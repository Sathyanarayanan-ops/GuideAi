# from dataclasses import dataclass
# from typing_extensions import TypedDict

# from langchain_core.runnables import RunnableConfig
# from langgraph.graph import StateGraph
# from langgraph.runtime import Runtime
# from langgraph.graph import StateGraph,END
# from langgraph.checkpoint.memory import MemorySaver
# from plannerAgent import Agentcall

# from google import genai
# from google.genai import types
# from plannerAgent import Agentcall
# import re



# class AgentState(TypedDict):
#     point_data: dict 
#     route: str
#     completed_sections: List[str]
#     transcript: str
#     feedback: str
#     revision_count: int
#     is_ready: bool


# builder = StateGraph(AgentState)

# def writer_node(state: AgentState) -> AgentState:
#     client = genai.Client()
#     tools = [types.Tool(google_search=types.GoogleSearchRetrieval())]
#     WRITER_SYSTEM_PROMPT = """
#         ROLE: You are an award-winning Audio Tour Script Writer and Local Historian. Your goal is to turn dry facts into "theatre for the ears."

#         TONE: 
#         - Engaging, warm, and slightly witty. 
#         - Think "National Geographic meets a friendly local pub guide."
#         - Use "Verbal Signposting" (e.g., "If you look to your left," "Now, notice the brickwork...").

#         CONTENT GUIDELINES:
#         1. SENSORY DETAILS: Don't just tell history; describe the smell of the coal smoke, the sound of the frontier wagons, or the vibe of a modern college game day.
#         2. THE "HUMOR QUOTA": Include 1-2 subtle, tasteful jokes or "fun facts" per segment. (e.g., "Blacksburg was so remote back then that even the squirrels needed a map.")
#         3. RESEARCH INTEGRITY: Use your search tool to find specific, non-obvious details (names of founding families, specific dates, or quirky local legends).
#         4. PACING: Write for the ear. Use shorter sentences. Avoid complex jargon unless you explain it immediately.
#         5. TRANSITIONS: Always end the segment by hinting at the next destination to keep the listener moving.

#         STRUCTURE:
#         - Intro: Hook the listener immediately.
#         - The "Meat": Deep dive into the history/directive.
#         - The "Easter Egg": One weird/funny fact nobody knows.
#         - Outro: A smooth transition statement.
#         """
#     config = types.GenerateContentConfig(
#     system_instruction=WRITER_SYSTEM_PROMPT,
#     tools=tools,
#     temperature=0.6 # Slight randomness helps with humor
# )

    

#     prompt = f"""
#     GENERATE TOUR SEGMENT:
#     Route: {state['route']}
#     Point Title: {state['point_data']['title']}
#     Summary: {state['point_data']['summary']}
#     Specific Directive: {state['point_data']['directive']}
#     """

#     if state.get('feedback'):
#         prompt += f"\n\nINCORPORATE FEEDBACK: {state['feedback']}"
#         prompt += f"\n\nPREVIOUS DRAFT:\n{state['transcript']}"

#     response = client.models.generate_content(
#         model='gemini-3.0-flash', 
#         contents=prompt,
#         config=config
#     )

#     return {
#         "transcript": response.text,
#         "revision_count": state['revision_count'] + 1
#     }




# def director_node(state: AgentState) -> AgentState:
#     client = genai.Client()
    
#     DIRECTOR_SYSTEM_PROMPT = """
#     ROLE: You are the Tour Director and Senior Editor. 
#     GOAL: Ensure the script is cohesive, accurate, and flows well.
    
#     CONTINUITY CHECK:
#     You have access to 'PREVIOUS_SECTIONS'. If the current script discusses a topic (e.g., earthquakes) that was introduced in a previous section, 
#     instruct the writer to refer back to it (e.g., "Remember the anti-seismic bracing we saw at the Golden Gate?").
    
#     OUTPUT FORMAT:
#     You must return a JSON object with two fields:
#     1. "is_ready": boolean (true if approved, false if needs changes)
#     2. "feedback": string (If false, specific instructions for the writer. If true, a brief commendation.)
#     """

#     # Format previous sections for context
#     prev_context = "\n---\n".join(state['completed_sections']) if state['completed_sections'] else "No previous sections."

#     prompt = f"""
#     PREVIOUS SECTIONS (Context):
#     {prev_context}
    
#     CURRENT DRAFT TO REVIEW:
#     {state['transcript']}
    
#     Review this draft. 
#     1. Is the tone correct?
#     2. Does it ignore context from previous sections?
#     3. Is it accurate and not misleading?
    
#     Provide your decision in JSON.
#     """

#     config = types.GenerateContentConfig(
#         system_instruction=DIRECTOR_SYSTEM_PROMPT,
#         response_mime_type="application/json", 
#         temperature=0.2 
#     )

#     response = client.models.generate_content(
#         model='gemini-3.0-flash',
#         contents=prompt,
#         config=config
#     )
    
#     import json
#     result = json.loads(response.text)
    
#     return {
#         "is_ready": result['is_ready'],
#         "feedback": result['feedback']
#     }

# def should_continue(state: AgentState) -> bool:
#     if state['revision_count'] >= 3:
#         return "end"
    
#     if state['is_ready']:
#         return "end"
#     else:
#         return "loop"



# # initialize the graph
# worflow = StateGraph(AgentState)
# workflow.add_node("writer", writer_node)
# workflow.add_node("director", director_node)
# workflow.set_entry_point("writer")
# workflow.add_edge("writer", "director")
# workflow.add_conditional_edges(
#     "director",
#     should_continue,
#     {
#         "loop": "writer",
#         "end": END
#     }
# )

# checkpointer = MemorySaver()
# app = workflow.compile(checkpointer=checkpointer)

# #####################




# def extractRoute(response):
#     ''''
    
#         Extracts the primary route and detailed points from the response text.
#         Returns a tuple containing a list of points and the primary route string.
#         Args: 
#             response (str): The response text containing the LLM response.
#         Returns:
#             tuple: A tuple containing:
#                 - list of dict: Each dict contains 'title', 'summary', and 'directive' for each point.
#                 - str: The primary route extracted from the response.
        
#         Uses Regex to parse the structured format of the response.
        
#     '''
#     if response is None:
#         return None, None
#     route_match = re.search(r"(?:Primary [Rr]oute):\s*(.*)", response, re.IGNORECASE)
#     primary_route = route_match.group(1).strip() if route_match else "Route not found"

#     points_raw = re.split(r'\n(?=\d+\.\s+\*\*)', response)

#     parsed_points = []
#     for item in points_raw:
#         if "Summary:" not in item:
#             continue

#         def get_match(pattern, string):
#             match = re.search(pattern, string)
#             # .strip() cleans up any trailing markdown stars or spaces
#             return match.group(1).replace('*', '').strip() if match else "Not Found"

#         title = get_match(r'\*\*(.*?)\*\*', item)
#         summary = get_match(r'Summary:\s*(.*)', item)
#         directive = get_match(r'Script Writer Directive:\s*(.*)', item)
    
#         parsed_points.append({
#             "title": title,
#             "summary": summary,
#             "directive": directive
#         })
        
#     return parsed_points, primary_route





import re
import json
import os
from typing import List, Dict, TypedDict, Optional
from dataclasses import dataclass
from plannerAgent import Agentcall

# LangGraph & LangChain Imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Google GenAI Imports
from google import genai
from google.genai import types

# --- 1. DEFINE STATE ---
class AgentState(TypedDict):
    point_data: dict 
    route: str
    completed_sections: List[str] # Holds the history of previous points
    transcript: str
    feedback: str
    revision_count: int
    is_ready: bool

# --- 2. DEFINE NODES ---

def writer_node(state: AgentState) -> AgentState:
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY")) # Ensure API key is set
    
    # Enable Google Search for the writer
    tools = [types.Tool(google_search=types.GoogleSearch())]
    
    WRITER_SYSTEM_PROMPT = """
        ROLE: You are an award-winning Audio Tour Script Writer and Local Historian. Your goal is to turn dry facts into "theatre for the ears."

        TONE: 
        - Engaging, warm, and slightly witty. 
        - Think "National Geographic meets a friendly local pub guide."
        - Use "Verbal Signposting" (e.g., "If you look to your left," "Now, notice the brickwork...").

        CONTENT GUIDELINES:
        1. SENSORY DETAILS: Don't just tell history; describe the smell of the coal smoke, the sound of the frontier wagons, or the vibe of a modern college game day.
        2. THE "HUMOR QUOTA": Include 1-2 subtle, tasteful jokes or "fun facts" per segment. (e.g., "Blacksburg was so remote back then that even the squirrels needed a map.")
        3. RESEARCH INTEGRITY: Use your search tool to find specific, non-obvious details (names of founding families, specific dates, or quirky local legends).
        4. PACING: Write for the ear. Use shorter sentences. Avoid complex jargon unless you explain it immediately.
        5. TRANSITIONS: Always end the segment by hinting at the next destination to keep the listener moving.

        STRUCTURE:
        - Intro: Hook the listener immediately.
        - The "Meat": Deep dive into the history/directive.
        - The "Easter Egg": One weird/funny fact nobody knows.
        - Outro: A smooth transition statement.
    """
    
    config = types.GenerateContentConfig(
        system_instruction=WRITER_SYSTEM_PROMPT,
        tools=tools,
        temperature=0.7 # Slight randomness helps with humor
    )

    # Construct Prompt
    prompt = f"""
    GENERATE TOUR SEGMENT:
    Route Name: {state['route']}
    Point Title: {state['point_data']['title']}
    Summary: {state['point_data']['summary']}
    Specific Directive: {state['point_data']['directive']}
    """

    # Add feedback if this is a revision loop
    if state.get('feedback'):
        prompt += f"\n\n*** CRITICAL FEEDBACK FROM DIRECTOR ***\n{state['feedback']}"
        prompt += f"\n\nPREVIOUS DRAFT (For Reference):\n{state['transcript']}"
    
    # Add context of previous sections if available (so writer knows what was already said)
    if state.get('completed_sections'):
        history_text = "\n---\n".join(state['completed_sections'])
        prompt += f"\n\nCONTEXT (Previously written stops):\n{history_text}"

    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents=prompt,
        config=config
    )

    return {
        "transcript": response.text,
        "revision_count": state['revision_count'] + 1
    }

def director_node(state: AgentState) -> AgentState:
    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
    
    DIRECTOR_SYSTEM_PROMPT = """
    ROLE: You are the Tour Director and Senior Editor. 
    GOAL: Ensure the script is cohesive, accurate, and flows well.
    
    CONTINUITY CHECK:
    You have access to 'PREVIOUS_SECTIONS'. If the current script discusses a topic (e.g., earthquakes) that was introduced in a previous section, 
    instruct the writer to refer back to it (e.g., "Remember the anti-seismic bracing we saw at the Golden Gate?").
    
    OUTPUT FORMAT:
    You must return a JSON object with two fields:
    1. "is_ready": boolean (true if approved, false if needs changes)
    2. "feedback": string (If false, specific instructions for the writer. If true, a brief commendation.)
    """

    # Format previous sections for context
    prev_context = "\n---\n".join(state['completed_sections']) if state['completed_sections'] else "No previous sections."

    prompt = f"""
    PREVIOUS SECTIONS (Context):
    {prev_context}
    
    CURRENT DRAFT TO REVIEW:
    {state['transcript']}
    
    Review this draft. 
    1. Is the tone correct?
    2. Does it ignore context from previous sections?
    3. Is it accurate and not misleading?
    
    Provide your decision in JSON.
    """

    config = types.GenerateContentConfig(
        system_instruction=DIRECTOR_SYSTEM_PROMPT,
        response_mime_type="application/json", 
        temperature=0.2 
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=config
    )
    
    # Safe JSON parsing
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError:
        # Fallback if JSON fails
        result = {"is_ready": False, "feedback": "JSON Error. Please regenerate."}
    
    return {
        "is_ready": result['is_ready'],
        "feedback": result['feedback']
    }

def should_continue(state: AgentState):
    # Safety valve: Stop after 3 revisions to prevent infinite loops
    if state['revision_count'] >= 3:
        return "end"
    
    if state['is_ready']:
        return "end"
    else:
        return "loop"

# --- 3. BUILD GRAPH ---

workflow = StateGraph(AgentState) # Fixed typo 'worflow'

workflow.add_node("writer", writer_node)
workflow.add_node("director", director_node)

workflow.set_entry_point("writer")

workflow.add_edge("writer", "director")

workflow.add_conditional_edges(
    "director",
    should_continue,
    {
        "loop": "writer",
        "end": END
    }
)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)



    
def save_tour_to_markdown(route_name, scripts, filename="tour_script.md"):
    with open(filename, "w", encoding="utf-8") as f:
        # Title and Header
        f.write(f"# Audio Tour: {route_name}\n")
        f.write(f"*Generated by AI Narrative Architect & Script Writer*\n\n")
        f.write("---\n\n")
        
        # Table of Contents
        f.write("## Tour Stops\n")
        for i, script in enumerate(scripts):
            # Extract just the title for the TOC
            title = script.split('\n')[0].replace(f"STOP {i+1}: ", "")
            f.write(f"{i+1}. [{title}](#stop-{i+1})\n")
        
        f.write("\n---\n\n")
        
        # Content
        for i, script in enumerate(scripts):
            # Clean up the STOP header for markdown anchoring
            content = script.replace(f"STOP {i+1}: ", f"## <a name='stop-{i+1}'></a> Stop {i+1}: ")
            f.write(content)
            f.write("\n\n---\n\n")
            
    print(f"📂 Tour script successfully saved to {filename}")

# Call this after your loop finishes:


# --- 4. HELPER FUNCTION ---

def extractRoute(response):
    if response is None:
        return None, None
    
    # Extract Route Name
    route_match = re.search(r"(?:Primary [Rr]oute):\s*(.*)", response, re.IGNORECASE)
    primary_route = route_match.group(1).strip() if route_match else "Route not found"

    # Split by points (looking for numbers like "1. **Title**")
    points_raw = re.split(r'\n(?=\d+\.\s+\*\*)', response)

    parsed_points = []
    for item in points_raw:
        if "Summary:" not in item:
            continue

        def get_match(pattern, string):
            match = re.search(pattern, string)
            return match.group(1).replace('*', '').strip() if match else "Not Found"

        title = get_match(r'\*\*(.*?)\*\*', item)
        summary = get_match(r'Summary:\s*(.*)', item)
        directive = get_match(r'Script Writer Directive:\s*(.*)', item)
    
        parsed_points.append({
            "title": title,
            "summary": summary,
            "directive": directive
        })
        
    return parsed_points, primary_route



llm_response = Agentcall()


if llm_response:

    parsed_points, route_name = extractRoute(llm_response)



    if parsed_points:
        print(f"🌍 Starting Tour Generation for: {route_name}")
        
        # This list maintains the "Long Term Memory" of the tour
        final_tour_scripts = [] 

        # 2. Iterate through each point
        for i, point in enumerate(parsed_points):
            print(f"\n📍 Processing Point {i+1}: {point['title']}...")
            
            # Prepare the input state
            initial_input = {
                "point_data": point,
                "route": route_name,
                "completed_sections": final_tour_scripts, # Pass history so Director can check continuity!
                "transcript": "",
                "feedback": "",
                "revision_count": 0,
                "is_ready": False
            }
            
            # Run the Graph for this specific point
            # We use a unique thread_id for each point to keep checkpoints organized
            config = {"configurable": {"thread_id": f"point_{i}"}}
            
            # Invoke!
            result = app.invoke(initial_input, config=config)
            
            # Retrieve the final approved script
            approved_script = result['transcript']
            
            # Add to history
            final_tour_scripts.append(f"STOP {i+1}: {point['title']}\n{approved_script}")
            
            print(f"✅ Finished {point['title']}")
        
        save_tour_to_markdown(route_name, final_tour_scripts)

        # 3. Output the Final Result
        print("\n" + "="*40)
        print("       FINAL AUDIO TOUR SCRIPT       ")
        print("="*40 + "\n")
        
        for script in final_tour_scripts:
            print(script)
            print("\n" + "-"*20 + "\n")

    else:
        print("❌ No points extracted. Check your regex or input.")
        
else:
    print("❌ No response from Planner Agent.")
    
    
    
