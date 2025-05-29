from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from agents.exceptions import TimeAgentError
import logging

logger = logging.getLogger(__name__)

class TimeSlot(BaseModel):
    """A time slot in the study schedule."""
    time: str = Field(..., description="Time slot for the study session")
    topic: str = Field(..., description="Topic to be studied in this time slot")
    duration: str = Field(..., description="Duration of the study session")

class Schedule(BaseModel):
    """A weekly study schedule."""
    weekly_schedule: Dict[str, List[TimeSlot]] = Field(
        ...,
        description="Schedule organized by day of the week"
    )

class TimeAgent:
    """Agent responsible for generating study schedules."""
    
    def __init__(self):
        """Initialize the TimeAgent with a language model and output parser."""
        try:
            # Initialize the language model
            self.model = ChatOpenAI(
                model_name="gpt-3.5-turbo",
                temperature=0.7
            )
            
            # Initialize the output parser
            self.parser = PydanticOutputParser(pydantic_object=Schedule)
            
            # Get format instructions
            format_instructions = self.parser.get_format_instructions()
            
            # Create the prompt template
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational coach. Your task is to generate a study schedule for a student.
                {format_instructions}

                Additional Rules:
                1. Time slots must be in HH:MM format
                2. Duration must be in hours (e.g., "2 hours")
                3. Days should be: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
                4. Schedule must fit within the available time slots
                5. Topics should be distributed evenly across available days
                """),
                ("human", """Generate a study schedule for this student:
                Learning Path: {learning_path}
                Available Time: {available_time}

                {format_instructions}""")
            ])
            
        except Exception as e:
            logger.error(f"Failed to initialize TimeAgent: {str(e)}")
            raise

    def generate_schedule(self, learning_path: Dict[str, Any], available_time: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate a study schedule based on the learning path and available time."""
        try:
            # Format the prompt
            messages = self.prompt.format_messages(
                learning_path=learning_path,
                available_time=available_time,
                format_instructions=self.parser.get_format_instructions()
            )
            
            # Generate the schedule
            response = self.model.invoke(messages)
            
            # Log the raw response for debugging
            logger.debug(f"Raw LLM response: {response.content}")
            
            # Parse the response into a Schedule object
            schedule = self.parser.parse(response.content)
            
            # Convert to dictionary
            return schedule.model_dump()
            
        except Exception as e:
            logger.error(f"Error generating schedule: {str(e)}")
            raise TimeAgentError(f"Failed to generate schedule: {str(e)}")