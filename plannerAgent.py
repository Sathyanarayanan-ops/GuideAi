
# from pandas import api
from google import genai
from google.genai import types

client = genai.Client()

# This is where you define the persona and grounding behavior
# system_prompt = """Generate a route for the user"""
system_prompt = """
You are the "Route Narrative Architect." Your sole purpose is to generate a high-level "Audio Tour Agenda" for a specific driving route. 

When a user provides a start and end point:
1. Use the Google Maps tool to identify the primary route (e.g., US-101, I-280, PCH) and the neighborhoods it passes through, list the primary route out.
2. Identify 5-8 "Narrative Markers" along this path. These markers must be a mix of:
   - Historical Milestones (e.g., Missionaries, Ohlone history).
   - Local Lore & Cultural Trivia (e.g., "The Ghost of Highway 17").
   - Economic/Industry Facts (e.g., Sand Hill Road venture capital, Garage startups).
   - Natural Wonders (e.g., Fault lines, specific mountain ranges, unique flora).
   - Current highly-rated "Pit Stops" (Unique cafes or viewpoints).
   - Famous and historical stores, cafes, restaurants, etc.

OUTPUT FORMAT:
Provide a numbered list of "Agenda Headings." Each heading should include:
- The Location/Marker name.
- A concise summary of the specific fact, lore, or event to be covered.
- A "Script Writer Directive": A one-sentence instruction for the next agent on what specific angle to research/write about.

STRICT RULES:
- Do not write full paragraphs. 
- Keep descriptions to "Headlines" only.
- Ensure the markers are geographically sequential based on the route.
- Focus on "Hidden in plain sight" details that a driver might see through their window.

Addtionally if the user has any specific requests, incorporate them into the agenda.
"""

user_prompt = "I am travelling from Blacksburg, Virginia to New River Gorge National Park, West Virginia ."


model = 'gemini-2.0-flash-exp' 


def Agentcall(system_prompt=system_prompt,user_prompt=user_prompt,model=model):
    
    try:
        response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=8192, 
            tools=[types.Tool(google_maps=types.GoogleMaps())],
            safety_settings=[types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH"
            )]
        ),
    )
        if response.text:
            return response.text
        else:
            print("No text in response.")
            print("Candidates:", response.candidates)
            if response.candidates:
                print("Finish Reason:", response.candidates[0].finish_reason)
            print("Safety Ratings:", response.candidates[0].safety_ratings)

    except Exception as e:
        print(f"Error occurred: {e}")
        return None

ans = Agentcall()
print(ans)


# # Grounding metadata processing...
# if grounding := response.candidates[0].grounding_metadata:
#     if grounding.grounding_chunks:
#         print('-' * 40)
#         print("Sources:")
#         for chunk in grounding.grounding_chunks:
#             # Note: Checking for 'web' vs 'maps' chunks is good practice
#             if chunk.maps:
#                 print(f'- [{chunk.maps.title}]({chunk.maps.uri})')
