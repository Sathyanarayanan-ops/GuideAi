"""
Master Agent Module - Route Narrative Architect

This module contains the MasterAgent class responsible for orchestrating
the generation of high-level audio tour agendas for driving routes using
the Google Gemini API.

Author: GuideAI Team
Version: 1.0.0
"""

import logging
from typing import Optional
from google import genai
from google.genai import types


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MasterAgent:
    """
    Route Narrative Architect Agent for generating audio tour agendas.
    
    This agent generates a high-level "Audio Tour Agenda" for a specific driving
    route by identifying narrative markers, historical facts, and points of interest.
    
    Attributes:
        client (genai.Client): Google Generative AI client
        model (str): The model to use for content generation
        system_prompt (str): System instruction for the AI model
    """
    
    DEFAULT_MODEL = 'gemini-2.0-flash-exp'
    MAX_OUTPUT_TOKENS = 8192
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        system_prompt: Optional[str] = None
    ) -> None:
        """
        Initialize the MasterAgent.
        
        Args:
            model (str): The model identifier to use. Defaults to gemini-2.0-flash-exp
            system_prompt (str, optional): Custom system prompt. Uses default if None.
        """
        self.client = genai.Client()
        self.model = model
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        logger.info(f"MasterAgent initialized with model: {self.model}")
    
    @staticmethod
    def _get_default_system_prompt() -> str:
        """
        Get the default system prompt for the Route Narrative Architect.
        
        Returns:
            str: The default system prompt
        """
        return """You are the "Route Narrative Architect." Your sole purpose is to generate a high-level "Audio Tour Agenda" for a specific driving route. 

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

Additionally if the user has any specific requests, incorporate them into the agenda."""
    
    def generate_agenda(self, user_prompt: str) -> Optional[str]:
        """
        Generate a route agenda based on user input.
        
        Args:
            user_prompt (str): The user's travel route description
            
        Returns:
            str: The generated agenda text, or None if generation failed
            
        Raises:
            Exception: If API call encounters an error
        """
        try:
            logger.info(f"Generating agenda for route: {user_prompt}")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    max_output_tokens=self.MAX_OUTPUT_TOKENS,
                    tools=[types.Tool(google_maps=types.GoogleMaps())],
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_ONLY_HIGH"
                        )
                    ]
                ),
            )
            
            if response.text:
                logger.info("Agenda generated successfully")
                return response.text
            else:
                logger.warning("No text content in response")
                self._log_response_details(response)
                return None
                
        except Exception as e:
            logger.error(f"Error generating agenda: {e}", exc_info=True)
            raise
    
    @staticmethod
    def _log_response_details(response) -> None:
        """
        Log detailed information about the API response.
        
        Args:
            response: The API response object
        """
        if response.candidates:
            logger.info(f"Finish Reason: {response.candidates[0].finish_reason}")
            if response.candidates[0].safety_ratings:
                logger.info(f"Safety Ratings: {response.candidates[0].safety_ratings}")


def main() -> None:
    """Main entry point for testing the MasterAgent."""
    agent = MasterAgent()
    user_route = "I am travelling from Blacksburg, Virginia to New River Gorge National Park, West Virginia."
    
    result = agent.generate_agenda(user_route)
    if result:
        print(result)
    else:
        logger.error("Failed to generate agenda")


if __name__ == "__main__":
    main()
