# import plannerAgent
# from google import genai
# from google.genai import types
# from plannerAgent import Agentcall
# import re


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


# points,route = extractRoute(response)


# def writerAgent():
#     client = genai.Client()


#     system_prompt = """

#     """ 
#     model = 'gemini-2.5-flash'

#     response = Agentcall()


import os
import re
import logging
from typing import List, Dict, Tuple, Optional
from google import genai
from google.genai import types

# Setup logging for industry standard observability
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WriterAgent:
    """Handles the generation of detailed audio transcripts for specific points."""
    
    def __init__(self, model_name: str = 'gemini-2.0-flash'):
        self.client = genai.Client()
        self.model_name = model_name
        self.system_prompt = (
            "You are a professional Audio Tour Script Writer. "
            "Generate immersive, conversational, and historically accurate audio transcripts. "
            "Focus on storytelling and sensory details."
        )

    def generate_transcript(self, point: Dict[str, str], route_name: str) -> str:
        """Calls the LLM to generate a transcript for a single point of interest."""
        prompt = (
            f"Route: {route_name}\n"
            f"Location: {point['title']}\n"
            f"Summary: {point['summary']}\n"
            f"Directive: {point['directive']}\n\n"
            "Write a 3-minute engaging audio tour script for this location."
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(system_instruction=self.system_prompt),
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating transcript for {point['title']}: {e}")
            return f"Error: Could not generate transcript for {point['title']}."

class TourDirector:
    """Coordinates the planning, parsing, and writing phases of the tour."""
    
    def __init__(self, output_dir: str = "transcripts"):
        self.writer = WriterAgent()
        self.output_dir = output_dir
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def extract_route_data(self, raw_response: str) -> Tuple[List[Dict[str, str]], str]:
        """Parses the structured response from the Planner Agent."""
        if not raw_response:
            return [], "Unknown Route"

        # Extract Primary Route
        route_match = re.search(r"(?:Primary [Rr]oute):\s*(.*)", raw_response, re.IGNORECASE)
        primary_route = route_match.group(1).strip() if route_match else "Route not found"

        # Split into individual points
        points_raw = re.split(r'\n(?=\d+\.\s+\*\*)', raw_response)
        parsed_points = []

        for item in points_raw:
            if "Summary:" not in item:
                continue

            title = self._regex_get(r'\*\*(.*?)\*\*', item)
            summary = self._regex_get(r'Summary:\s*(.*)', item)
            directive = self._regex_get(r'Script Writer Directive:\s*(.*)', item)

            parsed_points.append({
                "title": title,
                "summary": summary,
                "directive": directive
            })
        
        return parsed_points, primary_route

    def _regex_get(self, pattern: str, text: str) -> str:
        """Helper to safely extract regex matches."""
        match = re.search(pattern, text)
        return match.group(1).replace('*', '').strip() if match else "Not Found"

    def run_sequential_writer(self, points: List[Dict[str, str]], route: str):
        """Iterates through points and saves each as a separate Markdown file."""
        logger.info(f"Starting transcript generation for route: {route}")
        
        for i, point in enumerate(points, 1):
            logger.info(f"Processing Point {i}/{len(points)}: {point['title']}")
            
            transcript = self.writer.generate_transcript(point, route)
            
            # Save to individual file (Writer Phase)
            file_name = f"point_{i:02d}_{point['title'].replace(' ', '_')}.md"
            file_path = os.path.join(self.output_dir, file_name)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {point['title']}\n\n")
                f.write(transcript)
        
        logger.info("All transcripts saved to temporary directory.")

# --- Usage Example ---

if __name__ == "__main__":
    from plannerAgent import Agentcall # Assuming this returns the raw planner string
    
    # 1. Initialize Director
    director = TourDirector(output_dir="tour_project_v1")
    
    # 2. Get data from Planner
    raw_planner_response = Agentcall()
    
    # 3. Parse data
    points, route = director.extract_route_data(raw_planner_response)
    
    # 4. Execute Writing Phase
    if points:
        director.run_sequential_writer(points, route)
    else:
        logger.warning("No points were found to write.")