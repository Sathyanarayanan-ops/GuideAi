import plannerAgent
from google import genai
from google.genai import types
from plannerAgent import Agentcall
import re

client = genai.Client()


system_prompt = """

"""


model = 'gemini-2.5-flash'

response = Agentcall()


import re

def extractRoute(response):
    if response is None:
        return None, None
    
    # 1. Flexible Route Extraction
    # Handles: **Primary Route**: I-64, Primary route: I-64, etc.
    route_match = re.search(r"(?:Primary [Rr]oute):\s*(.*)", response, re.IGNORECASE)
    primary_route = route_match.group(1).strip() if route_match else "Route not found"

    # 2. Splitting by numbered points
    points_raw = re.split(r'\n(?=\d+\.\s+\*\*)', response)

    parsed_points = []
    for item in points_raw:
        if "Summary:" not in item:
            continue

        def get_match(pattern, string):
            match = re.search(pattern, string)
            # .strip() cleans up any trailing markdown stars or spaces
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


points,route = extractRoute(response)


# def writerCall()