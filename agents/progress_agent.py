import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from agents.exceptions import ProgressAgentError

logger = logging.getLogger(__name__)

class ProgressSummary(BaseModel):
    """Model for student progress summary."""
    average_score: float = Field(description="Average score across all topics (0-100)")
    completed_topics: List[str] = Field(description="List of completed topics")
    improvement_areas: List[str] = Field(description="Areas that need improvement")
    next_steps: List[str] = Field(description="Recommended next steps")

class ProgressAgent:
    """Agent responsible for analyzing student progress."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        try:
            # Use structured output with function calling
            self.llm = ChatOpenAI(
                model_name="gpt-3.5-turbo-1106",  # Supports function calling
                temperature=0.3
            )
            
            # Create structured output chain
            self.structured_llm = self.llm.with_structured_output(ProgressSummary)
            
            # Simple prompt without JSON formatting instructions
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert educational progress analyzer. Analyze student progress and provide insights.
                
Provide:
- A realistic average score (0-100) based on available data
- List of topics the student has completed
- Areas where the student needs improvement
- Concrete next steps for the student"""),
                ("human", """Student Data: {student_data}
Learning Path: {learning_path}

Analyze this student's progress and provide insights.""")
            ])
            
        except Exception as e:
            logger.error(f"Failed to initialize ProgressAgent: {str(e)}")
            raise ProgressAgentError(f"Agent initialization failed: {str(e)}")

    def analyze_progress(self, student_data: Dict[str, Any] = None, learning_path: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Analyze student progress and generate insights."""
        try:
            # Handle missing parameters
            if student_data is None:
                student_data = {}
            if learning_path is None:
                learning_path = {}
            
            # Format the prompt
            formatted_prompt = self.prompt.format_messages(
                student_data=str(student_data),
                learning_path=str(learning_path)
            )
            
            # Get structured response
            progress_summary = self.structured_llm.invoke(formatted_prompt)
            
            # Convert to dict and validate
            result = progress_summary.model_dump()
            
            # Ensure valid data types
            if not isinstance(result.get("average_score"), (int, float)):
                result["average_score"] = 0.0
            else:
                result["average_score"] = max(0.0, min(100.0, result["average_score"]))
            
            for field in ["completed_topics", "improvement_areas", "next_steps"]:
                if not isinstance(result.get(field), list):
                    result[field] = []
                else:
                    result[field] = [str(item) for item in result[field]]
            
            logger.info(f"Successfully analyzed progress: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing progress: {str(e)}")
            return self._create_fallback_progress()

    def _create_fallback_progress(self) -> Dict[str, Any]:
        """Create fallback progress summary."""
        return {
            "average_score": 0.0,
            "completed_topics": [],
            "improvement_areas": ["Data not available for analysis"],
            "next_steps": ["Continue with current learning plan", "Review progress regularly"]
        }

    def validate_student_data(self, student_data: Dict[str, Any]) -> None:
        """Validate that student data contains required fields."""
        if not isinstance(student_data, dict):
            raise ProgressAgentError("Student data must be a dictionary")
        
        logger.debug(f"Validating student data: {student_data}")