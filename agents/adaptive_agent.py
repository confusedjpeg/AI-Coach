from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from agents.exceptions import AdaptiveAgentError
import logging

logger = logging.getLogger(__name__)

class AdaptiveRecommendations(BaseModel):
    """Adaptive learning recommendations for a student."""
    adjustments: List[str] = Field(
        ...,
        description="Recommended adjustments to the learning path"
    )
    next_topics: List[str] = Field(
        ...,
        description="Suggested next topics to focus on"
    )
    strategy: str = Field(
        ...,
        description="Recommended learning strategy"
    )

class AdaptiveAgent:
    """Agent responsible for generating adaptive learning recommendations."""
    
    def __init__(self):
        """Initialize the AdaptiveAgent with a language model and output parser."""
        try:
            # Initialize the language model
            self.model = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0.7
            )
            
            # Initialize the output parser
            self.parser = PydanticOutputParser(pydantic_object=AdaptiveRecommendations)
            
            # Get format instructions
            format_instructions = self.parser.get_format_instructions()
            
            # Create the prompt template
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational coach. Your task is to generate adaptive learning recommendations for a student.
                {format_instructions}

                Additional Rules:
                1. Adjustments should be specific and actionable
                2. Next topics should be relevant to the student's current progress
                3. Strategy should be clear and concise
                4. All recommendations should be based on the student's progress data
                """),
                ("human", """Generate adaptive recommendations for this student:
                Progress Data: {progress_data}
                Current Settings: {current_settings}

                {format_instructions}""")
            ])
            
        except Exception as e:
            logger.error(f"Failed to initialize AdaptiveAgent: {str(e)}")
            raise

    def generate_recommendations(self, progress_data: Dict[str, Any], current_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Generate adaptive learning recommendations based on progress data."""
        try:
            # Format the prompt
            messages = self.prompt.format_messages(
                progress_data=progress_data,
                current_settings=current_settings,
                format_instructions=self.parser.get_format_instructions()
            )
            
            # Generate recommendations
            response = self.model.invoke(messages)
            
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response: {response.content}")
            
            # Parse the response into an AdaptiveRecommendations object
            recommendations = self.parser.parse(response.content)
            
            # Convert to dictionary
            return recommendations.model_dump()
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            raise AdaptiveAgentError(f"Failed to generate recommendations: {str(e)}") 