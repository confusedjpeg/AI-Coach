import json
import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from agents.exceptions import PathAgentError
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Topic(BaseModel):
    """A topic in the learning path."""
    name: str = Field(description="Name of the topic")
    description: str = Field(description="Brief description of what will be learned")
    estimated_time: str = Field(description="Estimated time to complete the topic")

class LearningPath(BaseModel):
    """Model for learning path."""
    topics: List[Topic] = Field(description="List of topics to be covered")
    current_stage: str = Field(description="Current stage in the learning path")
    progress: float = Field(description="Overall progress (0-1)")

class PathAgent:
    """Agent responsible for generating learning paths."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        try:
            # Use structured output with function calling
            self.llm = ChatOpenAI(
                model_name="gpt-3.5-turbo-1106",  # Supports function calling
                temperature=0.3
            )
            
            # Create structured output chain
            self.structured_llm = self.llm.with_structured_output(LearningPath)
            
            # Simple prompt without JSON formatting instructions
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational path designer. Generate a personalized learning path for students.
                
Create a learning path with:
- 3-5 relevant topics based on the student's current topic
- Clear descriptions for each topic
- Realistic time estimates
- An appropriate current stage description
- Progress starting at 0.0"""),
                ("human", """Student Information:
Student ID: {student_id}
Current Topic: {current_topic}
Additional Data: {additional_data}

Generate a personalized learning path for this student.""")
            ])
            
        except Exception as e:
            logger.error(f"Failed to initialize PathAgent: {str(e)}")
            raise PathAgentError(f"Agent initialization failed: {str(e)}")

    def validate_student_state(self, student_data: Dict[str, Any]) -> None:
        """Validate the student data before generating a learning path."""
        if not isinstance(student_data, dict):
            raise PathAgentError("Student data must be a dictionary")
            
        required_fields = ["student_id", "current_topic"]
        missing_fields = [field for field in required_fields if field not in student_data]
        
        if missing_fields:
            raise PathAgentError(f"Missing required fields: {missing_fields}")

    def generate_learning_path(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a personalized learning path for the student."""
        try:
            self.validate_student_state(student_data)
            
            # Format the prompt
            formatted_prompt = self.prompt.format_messages(
                student_id=student_data.get("student_id", "unknown"),
                current_topic=student_data.get("current_topic", "Programming"),
                additional_data=str(student_data)
            )
            
            # Get structured response
            learning_path = self.structured_llm.invoke(formatted_prompt)
            
            # Convert to dict and validate
            result = learning_path.model_dump()
            
            # Ensure valid data types
            if not isinstance(result.get("progress"), (int, float)):
                result["progress"] = 0.0
            else:
                result["progress"] = max(0.0, min(1.0, result["progress"]))
                
            if not isinstance(result.get("topics"), list):
                result["topics"] = self._create_default_topics(student_data.get("current_topic", "Programming"))
                
            if not isinstance(result.get("current_stage"), str):
                result["current_stage"] = "Getting Started"
            
            logger.info(f"Successfully generated learning path: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating learning path: {str(e)}")
            return self._create_fallback_learning_path(student_data)

    def _create_default_topics(self, topic_name: str) -> List[Dict[str, str]]:
        """Create default topics for a subject."""
        return [
            {
                "name": f"Introduction to {topic_name}",
                "description": "Basic concepts and overview",
                "estimated_time": "2 hours"
            },
            {
                "name": f"{topic_name} Fundamentals",
                "description": "Core principles and foundations",
                "estimated_time": "3 hours"
            },
            {
                "name": f"Practical {topic_name}",
                "description": "Hands-on exercises and practice",
                "estimated_time": "4 hours"
            }
        ]

    def _create_fallback_learning_path(self, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback learning path when generation fails."""
        topic_name = student_data.get("current_topic", "Programming") if student_data else "Programming"
        
        return {
            "topics": self._create_default_topics(topic_name),
            "current_stage": "Getting Started",
            "progress": 0.0
        }