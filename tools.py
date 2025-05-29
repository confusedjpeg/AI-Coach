from typing import Dict, Any, List
from langgraph.graph import StateGraph
from agents import (
    PathAgent, TimeAgent, ProgressAgent, AdaptiveAgent,
    PathAgentError, TimeAgentError, ProgressAgentError, AdaptiveAgentError
)
import logging

logger = logging.getLogger(__name__)

class LearningPathTool:
    """Tool for generating learning paths."""
    
    def __init__(self):
        self.agent = PathAgent()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a learning path for the student."""
        try:
            # Extract student data
            student_data = {
                "student_id": state.get("student_id"),
                "current_topic": state.get("current_topic"),
                "available_time": state.get("available_time", {}),
                "current_settings": state.get("current_settings", {})
            }
            
            # Generate learning path
            learning_path = self.agent.generate_learning_path(student_data)
            
            # Update state
            state["learning_path"] = learning_path
            return state
            
        except PathAgentError as e:
            logger.error(f"Error in LearningPathTool: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LearningPathTool: {str(e)}")
            raise

class ScheduleTool:
    """Tool for generating study schedules."""
    
    def __init__(self):
        self.agent = TimeAgent()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a study schedule for the student."""
        try:
            # Check if learning path exists
            if "learning_path" not in state:
                raise TimeAgentError("Learning path not found in state")
            
            # Generate schedule
            schedule = self.agent.generate_schedule(
                learning_path=state["learning_path"],
                available_time=state.get("available_time", {})
            )
            
            # Update state
            state["schedule"] = schedule
            return state
            
        except TimeAgentError as e:
            logger.error(f"Error in ScheduleTool: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ScheduleTool: {str(e)}")
            raise

class ProgressSummaryTool:
    """Tool for analyzing student progress."""
    
    def __init__(self):
        self.agent = ProgressAgent()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze student progress."""
        try:
            # Check if learning path exists
            if "learning_path" not in state:
                raise ProgressAgentError("Learning path not found in state")
            
            # Extract student data
            student_data = {
                "student_id": state.get("student_id"),
                "current_topic": state.get("current_topic"),
                "available_time": state.get("available_time", {}),
                "current_settings": state.get("current_settings", {})
            }
            
            # Analyze progress
            progress_summary = self.agent.analyze_progress(
                student_data=student_data,
                learning_path=state["learning_path"]
            )
            
            # Update state
            state["progress_summary"] = progress_summary
            return state
            
        except ProgressAgentError as e:
            logger.error(f"Error in ProgressSummaryTool: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ProgressSummaryTool: {str(e)}")
            raise

class AdaptiveAnalysisTool:
    """Tool for generating adaptive recommendations."""
    
    def __init__(self):
        self.agent = AdaptiveAgent()
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate adaptive recommendations."""
        try:
            # Check if progress summary exists
            if "progress_summary" not in state:
                raise AdaptiveAgentError("Progress summary not found in state")
            
            # Generate recommendations
            recommendations = self.agent.generate_recommendations(
                progress_data=state["progress_summary"],
                current_settings=state.get("current_settings", {})
            )
            
            # Update state
            state["recommendations"] = recommendations
            return state
            
        except AdaptiveAgentError as e:
            logger.error(f"Error in AdaptiveAnalysisTool: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in AdaptiveAnalysisTool: {str(e)}")
            raise 