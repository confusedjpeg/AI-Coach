import os
import logging
from dotenv import load_dotenv
from coach_tools import create_coach_graph
from agents.exceptions import CoachError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    # Try to load from .env file
    load_dotenv()
    
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.\n"
            "You can do this by:\n"
            "1. Creating a .env file with OPENAI_API_KEY=your-api-key-here\n"
            "2. Or setting it directly in your environment: export OPENAI_API_KEY=your-api-key-here"
        )

def print_coaching_results(results: dict):
    """Print the coaching session results in a readable format."""
    print("\n=== Coaching Session Results ===\n")
    
    # Learning Path
    if "learning_path" in results:
        print("Learning Path:")
        print(f"Current Stage: {results.get('current_stage', 'Unknown')}")
        print(f"Progress: {results.get('progress', 0.0):.1%}")
        print("\nTopics:")
        for topic in results["learning_path"].get("topics", []):
            print(f"- {topic['name']} (Deadline: {topic['deadline']})")
        print()
    
    # Schedule
    if "schedule" in results:
        print("Study Schedule:")
        for day, slots in results["schedule"].get("weekly_schedule", {}).items():
            print(f"\n{day}:")
            for slot in slots:
                print(f"- {slot['time']}: {slot['topic']} ({slot['duration']})")
        print()
    
    # Progress Summary
    if "progress_summary" in results:
        print("Progress Summary:")
        print(f"Average Score: {results.get('average_score', 0.0):.1%}")
        print("\nCompleted Topics:")
        for topic in results.get("completed_topics", []):
            print(f"- {topic}")
        print("\nAreas for Improvement:")
        for area in results.get("improvement_areas", []):
            print(f"- {area}")
        print()
    
    # Recommendations
    if "recommendations" in results:
        print("Adaptive Recommendations:")
        print(f"Learning Strategy: {results.get('learning_strategy', 'Continue current path')}")
        print("\nNext Topics:")
        for topic in results.get("next_topics", []):
            print(f"- {topic}")
        print()

def main():
    """Main function to run the coaching session."""
    try:
        check_environment()
        
        # Sample student data
        student_data = {
            "student_id": "student123",
            "current_topic": "Python",
            "experience_level": "beginner",
            "goals": ["Learn programming basics", "Build projects"],
            "available_time": "10 hours per week"
        }
        
        logger.info(f"Starting coaching session for student {student_data['student_id']}...")
        logger.info(f"Student data: {student_data}")
        
        # Create the coach graph
        coach_graph = create_coach_graph()
        
        # Run the coaching session
        try:
            # Make sure the initial state has the right structure
            initial_state = {
                "student_data": student_data,
                "messages": []
            }
            
            logger.info(f"Invoking coach graph with initial state: {initial_state}")
            result = coach_graph.invoke(initial_state)
            
            logger.info(f"Coach graph result: {result}")
            
            # Check if result is None
            if result is None:
                logger.error("Coach graph returned None")
                print("Failed to complete coaching session - no result returned.")
                return
            
            # Check if result has the expected structure
            if not isinstance(result, dict):
                logger.error(f"Coach graph returned unexpected type: {type(result)}")
                print("Failed to complete coaching session - invalid result type.")
                return
                
            print("\nCoaching Session Results:")
            print("------------------------")
            
            # Display results with better formatting
            learning_path = result.get("learning_path", {})
            progress_summary = result.get("progress_summary", {})
            schedule = result.get("schedule", {})
            adaptive_analysis = result.get("adaptive_analysis", {})
            
            # Display learning path
            print("📚 Learning Path:")
            topics = learning_path.get("topics", [])
            if topics:
                print(f"  Current Stage: {learning_path.get('current_stage', 'Unknown')}")
                print(f"  Progress: {learning_path.get('progress', 0)*100:.1f}%")
                print(f"  Topics ({len(topics)}):")
                for i, topic in enumerate(topics, 1):
                    if isinstance(topic, dict):
                        name = topic.get("name", "Unknown Topic")
                        time = topic.get("estimated_time", "Unknown time")
                        desc = topic.get("description", "No description")
                        print(f"    {i}. {name} ({time})")
                        print(f"       {desc}")
            else:
                print("  No topics available")
            
            # Display progress summary  
            print(f"\n📊 Progress Summary:")
            print(f"  Average Score: {progress_summary.get('average_score', 0)}%")
            completed = progress_summary.get("completed_topics", [])
            print(f"  Completed Topics: {len(completed)}")
            if completed:
                for topic in completed:
                    print(f"    ✓ {topic}")
            
            next_steps = progress_summary.get("next_steps", [])
            if next_steps:
                print("  Next Steps:")
                for step in next_steps:
                    print(f"    • {step}")
            
            # Display schedule
            print(f"\n📅 Schedule:")
            weekly = schedule.get("weekly_schedule", [])
            if weekly:
                for session in weekly:
                    day = session.get("day", "Unknown")
                    time = session.get("time", "Unknown")
                    activity = session.get("activity", "Study")
                    print(f"  {day} {time}: {activity}")
            else:
                print("  No schedule available")
            
            # Display adaptive analysis
            print(f"\n🎯 Adaptive Analysis:")
            recommendations = adaptive_analysis.get("recommendations", [])
            if recommendations:
                print("  Recommendations:")
                for rec in recommendations:
                    print(f"    • {rec}")
            else:
                print("  No specific recommendations")
                
            print("\n✅ Coaching session completed successfully!")
            
        except Exception as graph_error:
            logger.error(f"Error in coaching session: {str(graph_error)}")
            print("Failed to complete coaching session.")
            
    except EnvironmentError as env_error:
        logger.error(f"Environment error: {str(env_error)}")
        print(f"Environment setup failed: {str(env_error)}")
        
    except CoachError as coach_error:
        logger.error(f"Coach error: {str(coach_error)}")
        print(f"Coaching error: {str(coach_error)}")
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        print("An unexpected error occurred.")

if __name__ == "__main__":
    main()