import re
import json
import os
from typing import List, Dict, TypedDict, Optional
from dataclasses import dataclass
from plannerAgent import Agentcall
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from google import genai
from google.genai import types

class AgentState(TypedDict):
    point_data: dict 
    route: str
    completed_sections: List[str] 
    transcript: str
    feedback: str
    revision_count: int
    is_ready: bool
    
@dataclass
class TourConfig:
    '''
    Configuration for the tour generator agent.
    '''
    model_name: str = "gemini-2.5-flash"
    max_revisions: int = 3
    writer_temperature: float = 0.7
    director_temperature: float = 0.2
    
# --- Core Logic Classes ---

class TourContentGenerator:
    '''
    Handles the Langgraph workflow and agent nodes
    '''
    def __init__(self, config: TourConfig):
        self.config = config if config else TourConfig()
        self.client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.workflow = self._build_graph()
        
    def _should_continue(self, state: AgentState) -> str:
        '''
        Routing logic for the conditional edge 
        Returns 'loop' to go back to writer or 'end' to finish
        '''
        if state.get('revision_count',0) >= self.config.max_revisions:
            print("Max revisions ({self.config.max_revisions} reached. Ending process.")      
            return "end"
        
        if state.get('is_ready'):
            print("Director approved the script. Ending process.")
            return "end"
        
        return "loop"
            
                 
    def _build_graph(self) -> StateGraph:
        '''
        Constructs the state machine for the writing process
        '''
        workflow = StateGraph(AgentState)
        workflow.add_node("writer", self.writer_node)
        workflow.add_node("director", self.director_node)
        workflow.set_entry_point("writer")
        workflow.add_edge("writer", "director")
        workflow.add_conditional_edges(
            "director",
            self._should_continue,
            {
                "loop": "writer",
                "end": END
            }
        )

        return workflow.compile(checkpointer=MemorySaver())
    
    def writer_node(self,state: AgentState) -> Dict:
        '''
        Creative writer Agent Logic
        '''
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
        prompt = f"""
            GENERATE TOUR SEGMENT:
            Route Name: {state['route']}
            Point Title: {state['point_data']['title']}
            Summary: {state['point_data']['summary']}
            Specific Directive: {state['point_data']['directive']}
            """
        
        if state.get('feedback'):
            prompt += f"\n\n*** CRITICAL FEEDBACK FROM DIRECTOR ***\n{state['feedback']}"
            prompt += f"\n\nPREVIOUS DRAFT (For Reference):\n{state['transcript']}"
    
    # Add context of previous sections if available (so writer knows what was already said)
        if state.get('completed_sections'):
            history_text = "\n---\n".join(state['completed_sections'])
            prompt += f"\n\nCONTEXT (Previously written stops):\n{history_text}"
            
        
        response = self.client.models.generate_content(
            model=self.config.model_name, 
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=WRITER_SYSTEM_PROMPT,
                tools=tools,
                temperature=self.config.writer_temperature
            )
        )
        
        return {
            "transcript": response.text,
            "revision_count": state['revision_count'] + 1
        }
        
    def director_node(self,state: AgentState) -> Dict:
        '''
        Critical director Agent Logic
        '''
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
        
        response = self.client.models.generate_content(
            model=self.config.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=DIRECTOR_SYSTEM_PROMPT,
                response_mime_type="application/json", 
                temperature=self.config.director_temperature
            )
        )
        
        try:
            result = json.loads(response.text)
            return {
            "is_ready": result['is_ready'],
            "feedback": result['feedback']
        }
        
        except Exception as e:
            result = {"is_ready": False, "feedback": f"Parsing Error: {str(e)}. Please ensure your response is valid JSON."}
        

    
class TourArchitect:  
    '''
    Orchestrates the overall tour generation process and parses the llm output from the architect agent.
    '''
    
    def __init__(self,config: Optional[TourConfig] = None):
        self.config = config
        self.generator = TourContentGenerator(config)
    
    def parse_route_data(self,raw_response: str) -> tuple[List[Dict], str]:
        '''
        Parses the raw response from the architect agent to extract route and points data.
        '''
        if raw_response is None:
            return None, None
        
        route_match = re.search(r"(?:Primary [Rr]oute):\s*(.*)", raw_response, re.IGNORECASE)
        primary_route = route_match.group(1).strip() if route_match else "Route not found"

        points_raw = re.split(r'\n(?=\d+\.\s+\*\*)', raw_response)

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
    
    def save_to_markdown(self,route_name: str, scripts: List[str], filename: str = "tour_script.md"):
        '''
        Saves the final tour script to a markdown file.
        '''
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Audio Tour: {route_name}\n")
            f.write(f"*Generated by AI Narrative Architect & Script Writer*\n\n")
            f.write("---\n\n")
            
            f.write("## Tour Stops\n")
            for i, script in enumerate(scripts):
                title = script.split('\n')[0].replace(f"STOP {i+1}: ", "")
                f.write(f"{i+1}. [{title}](#stop-{i+1})\n")
            
            f.write("\n---\n\n")
            
            for i, script in enumerate(scripts):
                content = script.replace(f"STOP {i+1}: ", f"## <a name='stop-{i+1}'></a> Stop {i+1}: ")
                f.write(content)
                f.write("\n\n---\n\n")
                
        print(f"Tour script successfully saved to {filename}")
        
    
    def run(self,raw_input_data : str ):
        '''
        Main method to run the tour generation process.
        '''
        parsed_points, route_name = self.parse_route_data(raw_input_data)

        if not parsed_points:
            print("No points extracted. Check your regex or input.")
            return
        
        print(f"Starting Tour Generation for: {route_name}")
        
        final_tour_scripts = [] 

        for i, point in enumerate(parsed_points):
            print(f"\nProcessing Point {i+1}: {point['title']}...")
            
            initial_input = {
                "point_data": point,
                "route": route_name,
                "completed_sections": final_tour_scripts,
                "transcript": "",
                "feedback": "",
                "revision_count": 0,
                "is_ready": False
            }
            thread_config = {"configurable": {"thread_id": f"point_{i}"}}
            result = self.generator.workflow.invoke(initial_input, config=thread_config)
            
            final_tour_scripts.append(f"STOP {i+1}: {point['title']}\n{result['transcript']}")
            
        self.save_to_markdown(route_name, final_tour_scripts)
        
        
# --- Execution ---

if __name__ == "__main__":
    from plannerAgent import Agentcall
    
    planner_response = Agentcall() 
    
    if planner_response:
        architect = TourArchitect()
        architect.run(planner_response)
    else:
        print("No response from Planner Agent.")

        
