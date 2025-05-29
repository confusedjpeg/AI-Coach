from typing import Dict, Any
import logging
from langgraph.graph import StateGraph, END
from agents.path_agent import PathAgent
from agents.progress_agent import ProgressAgent
from data.student_service import StudentService

logger = logging.getLogger(__name__)

class CoachState:
    """State for the coaching workflow."""
    def __init__(self):
        self.student_data = {}
        self.learning_path = None
        self.progress_summary = None
        self.schedule = None
        self.adaptive_analysis = None
        self.messages = []

def create_coach_graph():
    """Create the coach workflow graph with database integration."""
    
    student_service = StudentService()
    
    def get_learning_path(state: Dict[str, Any]) -> Dict[str, Any]:
        """Get learning path for the student."""
        try:
            path_agent = PathAgent()
            student_data = state.get("student_data", {})
            student_id = student_data.get("student_id")
            
            # Save student data to database
            if student_id:
                student_service.create_or_update_student(student_data)
            
            # Generate learning path
            learning_path = path_agent.generate_learning_path(student_data)
            
            # Save generated learning path to database
            if student_id and learning_path:
                student_service.save_generated_learning_path(
                    student_id, 
                    learning_path, 
                    student_data.get('current_topic', '')
                )
            
            state["learning_path"] = learning_path
            return state
            
        except Exception as e:
            logger.error(f"Error getting learning path: {str(e)}")
            state["learning_path"] = {"topics": [], "current_stage": "Error", "progress": 0.0}
            return state
    
    def get_progress_summary(state: Dict[str, Any]) -> Dict[str, Any]:
        """Get progress summary using historical data."""
        try:
            progress_agent = ProgressAgent()
            student_data = state.get("student_data", {})
            learning_path = state.get("learning_path", {})
            student_id = student_data.get("student_id")
            
            # Get historical data from database
            historical_data = {}
            if student_id:
                historical_data = student_service.get_student_historical_data(student_id)
            
            # Use historical data for more accurate progress analysis
            if historical_data.get('has_history'):
                progress_data = historical_data['progress']
                enhanced_progress = {
                    "average_score": progress_data.get('average_score', 0.0),
                    "completed_topics": progress_data.get('completed_topics', []),
                    "improvement_areas": progress_data.get('improvement_areas', []),
                    "total_study_time_hours": progress_data.get('total_study_time_hours', 0),
                    "last_study_date": str(progress_data.get('last_study_date', '')),
                    # Add success threshold analysis
                    "success_threshold": {
                        "current_threshold": 70.0,
                        "student_setting": student_data.get('success_criteria', {}).get('success_threshold', 75.0),
                        "meeting_threshold": progress_data.get('average_score', 0) >= student_data.get('success_criteria', {}).get('success_threshold', 75.0),
                        "threshold_analysis": "Based on historical performance data"
                    },
                    "ai_insights": [
                        f"Student has completed {len(progress_data.get('completed_topics', []))} topics",
                        f"Total study time: {progress_data.get('total_study_time_hours', 0):.1f} hours",
                        f"Average performance: {progress_data.get('average_score', 0):.1f}%",
                        "Progress tracking shows consistent engagement" if progress_data.get('total_study_time_hours', 0) > 5 else "Consider increasing study frequency"
                    ],
                    "next_steps": [
                        "Continue with current learning plan",
                        "Focus on improvement areas identified",
                        "Maintain regular study schedule"
                    ]
                }
            else:
                # Use basic analysis for new students
                enhanced_progress = progress_agent.analyze_progress(
                    student_data=student_data,
                    learning_path=learning_path
                )
            
            state["progress_summary"] = enhanced_progress
            return state
            
        except Exception as e:
            logger.error(f"Error getting progress summary: {str(e)}")
            state["progress_summary"] = {"error": "Failed to get progress summary"}
            return state
    
    def get_schedule(state: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive schedule based on student preferences."""
        try:
            student_data = state.get("student_data", {})
            schedule_prefs = student_data.get("schedule_preferences", {})
            
            # Extract student preferences
            available_days = schedule_prefs.get("available_days", ["Monday", "Wednesday", "Friday"])
            time_prefs = schedule_prefs.get("time_preferences", {})
            study_duration = schedule_prefs.get("study_duration", 2)
            weekly_hours = schedule_prefs.get("weekly_hours", 10)
            break_frequency = schedule_prefs.get("break_frequency", "Every hour")
            break_duration = schedule_prefs.get("break_duration", "10 minutes")
            unavailable_times = schedule_prefs.get("unavailable_times", "")
            custom_habits = schedule_prefs.get("custom_habits", "")
            
            # Generate dynamic schedule based on preferences
            weekly_schedule = []
            study_sessions = []
            
            # Create sessions based on available days and time preferences
            for day in available_days:
                if time_prefs.get("morning", False):
                    weekly_schedule.append({
                        "day": day,
                        "time": "9:00-11:00",
                        "activity": f"{student_data.get('current_topic', 'Study')} - Morning Session",
                        "type": "study_session"
                    })
                    # Add break
                    weekly_schedule.append({
                        "day": day,
                        "time": "11:00-11:15",
                        "activity": f"Break ({break_duration})",
                        "type": "break"
                    })
                
                if time_prefs.get("afternoon", False):
                    weekly_schedule.append({
                        "day": day,
                        "time": "14:00-16:00",
                        "activity": f"{student_data.get('current_topic', 'Study')} - Practice Session",
                        "type": "study_session"
                    })
            
            # Generate study session types based on preferences
            learning_prefs = student_data.get("learning_preferences", {})
            if "Hands-on practice" in learning_prefs.get("learning_style", []):
                study_sessions.append({
                    "session": "Practical Coding",
                    "duration": f"{study_duration} hours",
                    "focus": "Hands-on exercises and projects"
                })
            
            if "Video tutorials" in learning_prefs.get("learning_style", []):
                study_sessions.append({
                    "session": "Video Learning",
                    "duration": f"{study_duration-0.5} hours",
                    "focus": "Video tutorials and guided learning"
                })
            
            # Parse custom habits
            parsed_habits = []
            if custom_habits:
                habits_list = custom_habits.split('\n')
                for habit in habits_list:
                    if habit.strip():
                        parsed_habits.append({
                            "habit": habit.strip(),
                            "time": "As specified",
                            "frequency": "As needed"
                        })
            
            state["schedule"] = {
                "weekly_schedule": weekly_schedule,
                "study_sessions": study_sessions,
                "custom_habits": parsed_habits,
                "total_weekly_hours": weekly_hours,
                "break_preferences": {
                    "frequency": break_frequency,
                    "duration": break_duration
                },
                "unavailable_times": unavailable_times.split('\n') if unavailable_times else []
            }
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting schedule: {str(e)}")
            state["schedule"] = {"error": "Failed to get schedule"}
            return state
    
    def get_adaptive_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
        """Get adaptive analysis for the student."""
        try:
            student_data = state.get("student_data", {})
            learning_path = state.get("learning_path", {})
            progress_summary = state.get("progress_summary", {})
            
            logger.info(f"Getting adaptive analysis for student: {student_data}")
            
            # Placeholder for adaptive analysis logic - you can implement AdaptiveAgent here
            recommendations = []
            if progress_summary.get("average_score", 0) < 70:
                recommendations.append("Focus on fundamentals before advancing")
            if not progress_summary.get("completed_topics"):
                recommendations.append("Start with introductory topics")
            
            state["adaptive_analysis"] = {
                "recommendations": recommendations,
                "difficulty_adjustments": ["Keep current level", "Add more practice exercises"],
                "focus_areas": progress_summary.get("improvement_areas", [])
            }
            return state
        except Exception as e:
            logger.error(f"Error getting adaptive analysis: {str(e)}")
            state["adaptive_analysis"] = {"error": "Failed to get adaptive analysis"}
            return state
    
    # Create the graph
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("get_learning_path", get_learning_path)
    workflow.add_node("get_progress_summary", get_progress_summary)
    workflow.add_node("get_schedule", get_schedule)
    workflow.add_node("get_adaptive_analysis", get_adaptive_analysis)
    
    # Set entry point
    workflow.set_entry_point("get_learning_path")
    
    # Add edges
    workflow.add_edge("get_learning_path", "get_progress_summary")
    workflow.add_edge("get_progress_summary", "get_schedule")
    workflow.add_edge("get_schedule", "get_adaptive_analysis")
    workflow.add_edge("get_adaptive_analysis", END)
    
    # Compile the graph
    return workflow.compile()

# Example usage
if __name__ == "__main__":
    try:
        # Create and compile the graph
        graph = create_coach_graph()
        
        # Initial state
        initial_state = {
            "student_data": {
                "student_id": "student123",
                "current_topic": "Python Basics",
                "available_time": {
                    "weekdays": ["09:00-17:00"],
                    "weekends": ["10:00-16:00"]
                },
                "current_settings": {
                    "success_threshold": 0.8,
                    "learning_style": "visual",
                    "preferred_difficulty": "medium"
                }
            },
            "learning_path": None,
            "schedule": None,
            "progress_summary": None,
            "adaptive_analysis": None
        }
        
        # Run the graph
        result = graph.invoke(initial_state)
        
        # Check for errors
        if result.get("error"):
            logger.error(f"Error in workflow: {result['error']}")
        else:
            print("Final state:", result)
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")