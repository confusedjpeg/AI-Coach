import streamlit as st
import os
import logging
from datetime import datetime, time
from dotenv import load_dotenv
from coach_tools import create_coach_graph
from agents.exceptions import CoachError
from typing import Dict, Any
from agents.study_session_analyzer import StudySessionAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ OpenAI API key not found. Please set it in your .env file or environment variables.")
        return False
    return True

def check_database_status():
    """Check and display database status."""
    try:
        from data.student_service import StudentService
        service = StudentService()
        
        # Debug database contents
        table_exists = service.debug_database_contents()
        
        if table_exists:
            st.success("✅ Database connected successfully")
            
            # Add debug buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧪 Create Test Student", key="create_test_button"):
                    success = service.create_test_student()
                    if success:
                        st.success("Test student created!")
                    else:
                        st.error("Failed to create test student")
            
            with col2:
                if st.button("🔍 Debug DB", key="debug_db_button"):
                    service.debug_database_contents()
                    st.info("Check logs for database contents")
            
            # Debug session state
            if st.checkbox("Show Session State", key="show_session_state"):
                st.write("**Current Session State:**")
                st.json({
                    "learning_plan_result": bool(st.session_state.get('learning_plan_result')),
                    "existing_student_data": bool(st.session_state.get('existing_student_data')),
                    "student_search_performed": st.session_state.get('student_search_performed', False),
                    "last_searched_name": st.session_state.get('last_searched_name', ''),
                    "last_searched_id": st.session_state.get('last_searched_id', ''),
                    "potential_conflicts": st.session_state.get('potential_conflicts', [])
                })
        else:
            st.error("❌ Students table not found in database")
        
        return table_exists
    except Exception as e:
        st.warning(f"⚠️ Database connection issue: {str(e)}")
        return False

def find_existing_student(student_name, student_id=None):
    """
    Find existing student by both name and ID with proper matching logic.
    Returns: (student_data, exact_match, potential_matches)
    """
    try:
        from data.student_service import StudentService
        service = StudentService()
        
        # Clear any previous results when searching for a new student
        if 'last_searched_name' not in st.session_state:
            st.session_state.last_searched_name = ""
        if 'last_searched_id' not in st.session_state:
            st.session_state.last_searched_id = ""
        
        # If we're searching for a different student, clear previous data
        if (student_name != st.session_state.last_searched_name or 
            student_id != st.session_state.last_searched_id):
            st.session_state.learning_plan_result = None
            st.session_state.existing_student_data = None
            st.session_state.potential_conflicts = []
            st.session_state.last_searched_name = student_name or ""
            st.session_state.last_searched_id = student_id or ""
        
        # Generate ID if not provided
        generated_id = f"student_{student_name.lower().replace(' ', '_')}" if student_name else None
        search_id = student_id if student_id else generated_id
        
        logger.info(f"Searching for student: name='{student_name}', id='{search_id}'")
        
        # Case 1: Both name and ID provided - exact match required
        if student_name and student_id:
            exact_match = service.find_student_by_name_and_id(student_name, student_id)
            if exact_match:
                historical_data = service.get_student_historical_data(student_id)
                return historical_data, True, []
            
            # Check for potential conflicts
            name_matches = service.find_students_by_name(student_name)
            id_matches = service.find_student_by_id(student_id)
            
            potential_matches = []
            if name_matches:
                potential_matches.extend([f"Name '{student_name}' exists with different ID: {match['student_id']}" for match in name_matches])
            if id_matches:
                potential_matches.append(f"ID '{student_id}' exists with different name: {id_matches['student_name']}")
            
            return None, False, potential_matches
        
        # Case 2: Only name provided - check for existing students with same name
        elif student_name and not student_id:
            name_matches = service.find_students_by_name(student_name)
            
            if not name_matches:
                # No matches - new student
                return None, False, []
            elif len(name_matches) == 1:
                # Single match - likely the same student
                match = name_matches[0]
                historical_data = service.get_student_historical_data(match['student_id'])
                return historical_data, True, []
            else:
                # Multiple matches - ambiguous
                conflicts = [f"Student ID: {match['student_id']}" for match in name_matches]
                return None, False, conflicts
        
        # Case 3: Only ID provided
        elif student_id and not student_name:
            id_match = service.find_student_by_id(student_id)
            if id_match:
                historical_data = service.get_student_historical_data(student_id)
                return historical_data, True, []
            return None, False, []
        
        return None, False, []
        
    except Exception as e:
        logger.error(f"Error finding existing student: {str(e)}")
        return None, False, [f"Database error: {str(e)}"]

def display_conflict_resolution(student_name, student_id):
    """Display conflict resolution interface."""
    st.header("⚠️ Student Record Conflicts")
    
    st.markdown("""
    We found multiple students with similar information. To ensure we access the correct records, 
    please provide both your name and student ID.
    """)
    
    if st.session_state.potential_conflicts:
        st.subheader("Found Records:")
        for conflict in st.session_state.potential_conflicts:
            st.info(conflict)
    
    st.markdown("""
    ### Options:
    1. **Provide both name and student ID** in the sidebar for exact match
    2. **Contact support** if you're unsure about your student ID
    3. **Create a new profile** if none of these records belong to you
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 Create New Profile", key="create_new_profile_button"):
            st.session_state.existing_student_data = None
            st.session_state.potential_conflicts = []
            st.session_state.student_search_performed = True
            st.rerun()
    
    with col2:
        if st.button("🔄 Try Search Again", key="retry_search_button"):
            st.session_state.student_search_performed = False
            st.session_state.potential_conflicts = []
            st.rerun()

def display_existing_student_dashboard(student_name, existing_data):
    """Display dashboard for existing students with real-time progress."""
    
    st.header(f"📊 Welcome Back, {student_name}!")
    
    # Get student info
    student_info = existing_data.get('student_info', {})
    student_id = student_info.get('student_id')
    
    # Initialize session state if not exists
    if 'show_learning_path' not in st.session_state:
        st.session_state.show_learning_path = False
    if 'show_progress' not in st.session_state:
        st.session_state.show_progress = False
    if 'show_schedule' not in st.session_state:
        st.session_state.show_schedule = False
    if 'show_study_form' not in st.session_state:
        st.session_state.show_study_form = False
    if 'show_assessment_form' not in st.session_state:
        st.session_state.show_assessment_form = False
    if 'show_adaptive_recommendations' not in st.session_state:
        st.session_state.show_adaptive_recommendations = False
    
    # Add refresh button and debug info
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    with col4:
        if st.button("🔍 Debug Data", key="debug_button"):
            st.write("**Debug Info:**")
            progress_data = existing_data.get('progress', {})
            st.json({
                'completed_topics': progress_data.get('completed_topics', []),
                'total_topics': progress_data.get('total_topics', 0),
                'learning_path_topics': progress_data.get('learning_path_topics', 0),
                'completed_count': progress_data.get('completed_count', 0),
                'progress_percentage': progress_data.get('progress_percentage', 0)
            })
    with col5:
        if st.button("🔄 Refresh Data", key="top_refresh_button"):
            try:
                from data.student_service import StudentService
                service = StudentService()
                fresh_data = service.get_student_historical_data(student_id)
                if fresh_data:
                    st.session_state.existing_student_data = fresh_data
                    st.success("Data refreshed!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error refreshing data: {str(e)}")
    
    # Quick actions - now with 4 buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("📚 View Learning Path", key="view_path_button"):
            st.session_state.show_learning_path = True
            st.session_state.show_progress = False
            st.session_state.show_schedule = False
            st.session_state.show_study_form = False
            st.session_state.show_assessment_form = False
            st.session_state.show_adaptive_recommendations = False
            st.rerun()
    with col2:
        if st.button("📊 View Progress", key="view_progress_button"):
            st.session_state.show_progress = True
            st.session_state.show_learning_path = False
            st.session_state.show_schedule = False
            st.session_state.show_study_form = False
            st.session_state.show_assessment_form = False
            st.session_state.show_adaptive_recommendations = False
            st.rerun()
    with col3:
        if st.button("🤖 Adaptive Insights", key="view_adaptive_button"):
            st.session_state.show_adaptive_recommendations = True
            st.session_state.show_learning_path = False
            st.session_state.show_progress = False
            st.session_state.show_schedule = False
            st.session_state.show_study_form = False
            st.session_state.show_assessment_form = False
            st.rerun()
    with col4:
        if st.button("📅 View Schedule", key="view_schedule_button"):
            st.session_state.show_schedule = True
            st.session_state.show_learning_path = False
            st.session_state.show_progress = False
            st.session_state.show_study_form = False
            st.session_state.show_assessment_form = False
            st.session_state.show_adaptive_recommendations = False
            st.rerun()
    with col5:
        if st.button("🔄 Generate New Plan", key="new_plan_button"):
            st.session_state.existing_student_data = None
            st.session_state.student_search_performed = False
            st.rerun()
    
    
    # Show Learning Path section
    if st.session_state.show_learning_path and student_id:
        st.markdown("---")
        st.subheader("📚 Your Learning Paths")
        
        try:
            from data.student_service import StudentService
            service = StudentService()
            learning_paths = service.get_student_learning_paths(student_id)
            
            if learning_paths:
                for i, path in enumerate(learning_paths):
                    with st.expander(f"📖 {path.get('topic', 'Unknown Topic')} - {path.get('current_stage', 'In Progress')}", expanded=i==0):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Progress", f"{path.get('overall_progress', 0):.1f}%")
                        with col2:
                            topics = path.get('topics', [])
                            topics_count = len(topics) if isinstance(topics, list) else 0
                            st.metric("Total Topics", topics_count)
                        with col3:
                            status = "🟢 Active" if path.get('is_active') else "⚪ Inactive"
                            st.write(f"**Status:** {status}")
                        
                        st.write(f"**Created:** {path.get('created_at', 'Unknown')}")
                        
                        # Show topics if available
                        if topics and isinstance(topics, list) and len(topics) > 0:
                            st.write("**Learning Topics:**")
                            for j, topic in enumerate(topics[:5], 1):  # Show first 5 topics
                                if isinstance(topic, dict):
                                    topic_name = topic.get('name', f'Topic {j}')
                                    topic_desc = topic.get('description', 'No description')
                                    st.write(f"{j}. **{topic_name}**")
                                    st.write(f"   _{topic_desc}_")
                                else:
                                    st.write(f"{j}. {topic}")
                            
                            if len(topics) > 5:
                                st.write(f"... and {len(topics) - 5} more topics")
                        else:
                            st.info("No detailed topics available for this learning path.")
            else:
                st.info("No learning paths found. Generate your first learning plan!")
                
        except Exception as e:
            st.error(f"Error loading learning paths: {str(e)}")
    
    # Show Progress section
    if st.session_state.show_progress:
        st.markdown("---")
        st.subheader("📊 Your Progress Details")
        
        progress_data = existing_data.get('progress', {})
        
        # Detailed metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_topics = progress_data.get('total_topics', 0)
            st.metric("Total Topics", total_topics)
        with col2:
            completed_count = progress_data.get('completed_count', 0)
            st.metric("Completed Topics", completed_count)
        with col3:
            avg_score = progress_data.get('average_score', 0)
            st.metric("Average Score", f"{avg_score:.1f}%")
        with col4:
            study_hours = progress_data.get('total_study_time_hours', 0)
            st.metric("Study Hours", f"{study_hours:.1f}h")
        
        # Progress visualization
        if total_topics > 0:
            progress_percentage = (completed_count / total_topics) * 100
            st.write(f"**Overall Progress:** {progress_percentage:.1f}%")
            st.progress(progress_percentage / 100)
        
        # Completed topics list
        completed_list = progress_data.get('completed_topics', [])
        if completed_list:
            st.write("**✅ Completed Topics:**")
            for topic in completed_list:
                st.write(f"• {topic}")
        
        # Improvement areas
        improvement_areas = progress_data.get('areas_needing_review', [])
        if improvement_areas:
            st.write("**🎯 Areas for Improvement:**")
            for area in improvement_areas:
                st.write(f"• {area}")
        
        # Recent activity
        if progress_data.get('last_study_date'):
            st.write(f"**📅 Last Study Session:** {progress_data.get('last_study_date')}")
    
    # Show Schedule section
    if st.session_state.show_schedule and student_id:
        st.markdown("---")
        st.subheader("📅 Your Study Schedule")
        
        try:
            from data.student_service import StudentService
            service = StudentService()
            
            # Get student preferences for schedule information
            student_preferences = service.get_student_preferences(student_id)
            
            if student_preferences:
                # Display schedule preferences
                schedule_prefs = student_preferences.get('schedule', {})
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**📋 Your Study Preferences:**")
                    
                    available_days = schedule_prefs.get('available_days', [])
                    if available_days:
                        if isinstance(available_days, str):
                            # Handle string representation of list
                            import ast
                            try:
                                available_days = ast.literal_eval(available_days)
                            except:
                                available_days = [available_days]
                        
                        st.write(f"**Available Days:** {', '.join(available_days)}")
                    
                    weekly_hours = schedule_prefs.get('weekly_hours', 'Not set')
                    st.write(f"**Weekly Hours:** {weekly_hours}")
                    
                    time_prefs = schedule_prefs.get('time_preferences', {})
                    if time_prefs:
                        preferred_times = []
                        if time_prefs.get('morning'): preferred_times.append('Morning')
                        if time_prefs.get('afternoon'): preferred_times.append('Afternoon')
                        if time_prefs.get('evening'): preferred_times.append('Evening')
                        
                        if preferred_times:
                            st.write(f"**Preferred Times:** {', '.join(preferred_times)}")
                
                with col2:
                    st.write("**📊 Schedule Analytics:**")
                    
                    # Calculate some schedule metrics
                    if available_days and isinstance(available_days, list):
                        st.metric("Study Days per Week", len(available_days))
                    
                    if weekly_hours and str(weekly_hours).isdigit():
                        hours_per_day = int(weekly_hours) / len(available_days) if available_days else 0
                        st.metric("Average Hours per Day", f"{hours_per_day:.1f}h")
                
                # Weekly schedule visualization
                st.write("**📅 Weekly Schedule Overview:**")
                
                days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Create a simple schedule grid
                schedule_cols = st.columns(7)
                
                for i, day in enumerate(days_of_week):
                    with schedule_cols[i]:
                        st.write(f"**{day[:3]}**")
                        
                        if available_days and day in available_days:
                            st.success("📚 Study")
                            
                            # Show preferred time slots
                            if time_prefs:
                                if time_prefs.get('morning'):
                                    st.caption("🌅 Morning")
                                if time_prefs.get('afternoon'):
                                    st.caption("☀️ Afternoon")
                                if time_prefs.get('evening'):
                                    st.caption("🌆 Evening")
                        else:
                            st.info("💤 Free")
                
                # Study habits and recommendations
                learning_prefs = student_preferences.get('learning', {})
                if learning_prefs:
                    st.write("**🎯 Study Recommendations:**")
                    
                    difficulty = learning_prefs.get('difficulty_preference', '')
                    if difficulty:
                        st.write(f"• **Difficulty Level:** {difficulty}")
                    
                    learning_style = learning_prefs.get('learning_style', '')
                    if learning_style:
                        if isinstance(learning_style, str):
                            try:
                                import ast
                                learning_style = ast.literal_eval(learning_style)
                            except:
                                learning_style = [learning_style]
                        
                        if isinstance(learning_style, list):
                            st.write(f"• **Learning Style:** {', '.join(learning_style)}")
                
                # Success criteria
                success_prefs = student_preferences.get('success', {})
                if success_prefs:
                    threshold = success_prefs.get('success_threshold', '')
                    if threshold:
                        st.write(f"• **Success Threshold:** {threshold}%")
                
            else:
                st.info("No schedule preferences found. Generate a learning plan to set up your schedule!")
                
            # Option to modify schedule
            st.write("**⚙️ Schedule Actions:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📝 Update Schedule", key="update_schedule_button"):
                    st.info("Schedule update functionality - coming soon!")
            
            with col2:
                if st.button("📊 Schedule Analytics", key="schedule_analytics_button"):
                    st.info("Detailed schedule analytics - coming soon!")
            
            with col3:
                if st.button("📅 Export Schedule", key="export_schedule_button"):
                    st.info("Schedule export functionality - coming soon!")
                    
        except Exception as e:
            st.error(f"Error loading schedule: {str(e)}")

    # ADD THE NEW ADAPTIVE RECOMMENDATIONS SECTION
    if st.session_state.show_adaptive_recommendations and student_id:
        st.markdown("---")
        st.subheader("🤖 Adaptive Learning Insights")
        
        try:
            from agents.adaptive_agent import AdaptiveAgent
            from data.student_service import StudentService
            
            service = StudentService()
            
            with st.spinner("🧠 Generating adaptive recommendations..."):
                # Get comprehensive progress data
                progress_data = existing_data.get('progress', {})
                
                # Get current settings (learning preferences)
                current_settings = service.get_student_preferences(student_id)
                
                # Initialize the adaptive agent
                adaptive_agent = AdaptiveAgent()
                
                # Generate recommendations
                recommendations = adaptive_agent.generate_recommendations(
                    progress_data=progress_data,
                    current_settings=current_settings
                )
                
                # Display the recommendations
                st.success("✅ Adaptive insights generated!")
                
                # Create tabs for different types of insights
                tab1, tab2, tab3 = st.tabs(["📈 Adjustments", "📚 Next Topics", "🎯 Strategy"])
                
                with tab1:
                    st.subheader("📈 Recommended Adjustments")
                    adjustments = recommendations.get('adjustments', [])
                    if adjustments:
                        for i, adjustment in enumerate(adjustments, 1):
                            st.write(f"{i}. {adjustment}")
                    else:
                        st.info("No specific adjustments recommended at this time.")
                
                with tab2:
                    st.subheader("📚 Next Topics to Focus On")
                    next_topics = recommendations.get('next_topics', [])
                    if next_topics:
                        for i, topic in enumerate(next_topics, 1):
                            st.write(f"{i}. **{topic}**")
                    else:
                        st.info("Continue with your current learning path.")
                
                with tab3:
                    st.subheader("🎯 Recommended Learning Strategy")
                    strategy = recommendations.get('strategy', '')
                    if strategy:
                        st.write(strategy)
                    else:
                        st.info("Your current learning strategy is working well!")
                
                # Show detailed data used for recommendations
                with st.expander("🔍 Data Used for Recommendations"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Progress Data:**")
                        st.json(progress_data)
                    
                    with col2:
                        st.write("**Current Settings:**")
                        st.json(current_settings)
                
                # Action buttons based on recommendations
                st.markdown("---")
                st.subheader("🚀 Quick Actions")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📝 Log Study Session", key="adaptive_log_session"):
                        st.session_state.show_study_form = True
                        st.session_state.show_adaptive_recommendations = False
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Update Learning Path", key="adaptive_update_path"):
                        st.info("Learning path update feature - coming soon!")
                
                with col3:
                    if st.button("📊 Take Assessment", key="adaptive_assessment"):
                        st.session_state.show_assessment_form = True
                        st.session_state.show_adaptive_recommendations = False
                        st.rerun()
                
        except Exception as e:
            st.error(f"Error generating adaptive insights: {str(e)}")
            
            # Show debug info for troubleshooting
            with st.expander("🔍 Debug Information"):
                st.write("**Error Details:**")
                st.code(str(e))
                
                st.write("**Available Data:**")
                st.write(f"- Student ID: {student_id}")
                st.write(f"- Progress Data Keys: {list(progress_data.keys()) if 'progress_data' in locals() else 'Not available'}")
                st.write(f"- Current Settings: {'Available' if 'current_settings' in locals() else 'Not available'}")
    
    # Quick summary section with corrected data - FIX THE VARIABLES HERE
    st.markdown("---")
    st.subheader("📈 Live Progress Overview")
    
    progress_data = existing_data.get('progress', {})
    
    # Get all the progress variables in one place
    completed_count = progress_data.get('completed_count', 0)
    total_topics = progress_data.get('total_topics', 0)
    learning_path_topics = progress_data.get('learning_path_topics', 0)
    actual_total = max(total_topics, learning_path_topics)
    
    # Calculate correct progress percentage
    if actual_total > 0:
        correct_progress = (completed_count / actual_total) * 100
    else:
        correct_progress = 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Completed Topics", completed_count)
    with col2:
        st.metric("Total Topics", actual_total)
        
        # Show breakdown if different
        if learning_path_topics != total_topics:
            st.caption(f"Learning Path: {learning_path_topics}, Tracked: {total_topics}")
    with col3:
        st.metric("Progress", f"{correct_progress:.1f}%")
    with col4:
        learning_paths_count = existing_data.get('learning_paths_count', 0)
        st.metric("Learning Paths", learning_paths_count)
    
    # Corrected progress bar - use correct_progress instead of progress_percentage
    if correct_progress > 0:
        st.progress(correct_progress / 100)
        st.caption(f"You've completed {completed_count} out of {actual_total} topics!")
    
    # Show completed topics list
    completed_topics = progress_data.get('completed_topics', [])
    if completed_topics:
        st.write("**✅ Completed Topics:**")
        for i, topic in enumerate(completed_topics, 1):
            st.write(f"{i}. {topic}")
    
    # Recent activity (always visible)
    if progress_data.get('last_study_date'):
        st.info(f"📅 Last study session: {progress_data.get('last_study_date')}")
    
    # Quick actions section
    st.subheader("🚀 Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Log Study Session", key="log_session_button"):
            st.session_state.show_study_form = True
            st.session_state.show_assessment_form = False
            st.session_state.show_learning_path = False
            st.session_state.show_progress = False
            st.session_state.show_schedule = False
            st.session_state.show_adaptive_recommendations = False
            st.rerun()
    with col2:
        if st.button("🧪 Take Assessment", key="take_assessment_button"):
            st.session_state.show_assessment_form = True
            st.session_state.show_study_form = False
            st.session_state.show_learning_path = False
            st.session_state.show_progress = False
            st.session_state.show_schedule = False
            st.session_state.show_adaptive_recommendations = False
            st.rerun()

    # Show study session form
    if st.session_state.show_study_form:
        st.markdown("---")
        show_study_session_form(student_name)
    
    # Show assessment form
    if st.session_state.show_assessment_form:
        st.markdown("---")
        show_assessment_form(student_name)
    
    # Update the clear buttons section to include the new state
    if (st.session_state.show_learning_path or st.session_state.show_progress or 
        st.session_state.show_schedule or st.session_state.show_study_form or 
        st.session_state.show_assessment_form or st.session_state.show_adaptive_recommendations):
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", key="refresh_data_button"):
                st.rerun()
        with col2:
            if st.button("❌ Hide Details", key="hide_details_button"):
                st.session_state.show_learning_path = False
                st.session_state.show_progress = False
                st.session_state.show_schedule = False
                st.session_state.show_study_form = False
                st.session_state.show_assessment_form = False
                st.session_state.show_adaptive_recommendations = False
                st.rerun()
def load_existing_learning_data(existing_data):
    """Load and format existing learning data for display."""
    try:
        from data.student_service import StudentService
        service = StudentService()
        
        # Get student info
        student_info = existing_data.get('student_info', {})
        student_id = student_info.get('student_id')
        
        if not student_id:
            st.error("No student ID found")
            return
        
        # Get actual learning paths from database
        learning_paths = service.get_student_learning_paths(student_id)
        progress_data = existing_data.get('progress', {})
        
        # Format data to match expected structure
        formatted_result = {
            "learning_path": {},
            "progress_summary": {
                "average_score": progress_data.get('average_score', 0),
                "completed_topics": progress_data.get('completed_topics', []),
                "improvement_areas": progress_data.get('improvement_areas', []),
                "total_study_time_hours": progress_data.get('total_study_time_hours', 0),
                "success_threshold": {
                    "student_setting": 75.0,
                    "meeting_threshold": progress_data.get('average_score', 0) >= 75.0,
                    "threshold_analysis": "Based on historical data"
                },
                "ai_insights": [
                    f"You have completed {len(progress_data.get('completed_topics', []))} topics",
                    f"Your average score is {progress_data.get('average_score', 0):.1f}%",
                    f"Total study time: {progress_data.get('total_study_time_hours', 0):.1f} hours"
                ],
                "next_steps": [
                    "Continue with your current learning path",
                    "Focus on improvement areas",
                    "Consider taking assessments to track progress"
                ]
            },
            "schedule": {
                "weekly_schedule": [],
                "study_sessions": [],
                "custom_habits": []
            },
            "adaptive_analysis": {
                "personalized_suggestions": [
                    {
                        "category": "Progress",
                        "suggestion": "Continue consistent study schedule",
                        "reason": "Good progress maintained",
                        "priority": "Medium"
                    }
                ],
                "progress_against_goals": {
                    "weekly_goal": "Continue current progress",
                    "progress_percentage": min(progress_data.get('average_score', 0), 100),
                    "on_track": progress_data.get('average_score', 0) >= 70,
                    "adjustment_needed": "Maintain current pace" if progress_data.get('average_score', 0) >= 70 else "Increase study frequency"
                }
            }
        }
        
        # Add actual learning path data if available
        if learning_paths:
            # Get the most recent active learning path
            active_path = None
            for path in learning_paths:
                if path.get('is_active', True):
                    active_path = path
                    break
            
            if not active_path and learning_paths:
                # If no active path, use the most recent one
                active_path = learning_paths[0]
            
            if active_path:
                formatted_result["learning_path"] = {
                    "current_stage": active_path.get('current_stage', 'In Progress'),
                    "progress": active_path.get('overall_progress', 0) / 100.0,  # Convert to decimal
                    "topics": active_path.get('topics', []),
                    "topic": active_path.get('topic', ''),
                    "learning_path_id": active_path.get('id')
                }
                
                st.info(f"📚 Loaded learning path: {active_path.get('topic', 'Unknown Topic')}")
        
        st.session_state.learning_plan_result = formatted_result
        
    except Exception as e:
        logger.error(f"Error loading existing learning data: {str(e)}")
        st.error(f"Error loading your learning data: {str(e)}")

def show_study_session_form(student_name):
    """Show form to log a study session with comprehensive analysis."""
    st.subheader("📝 Log Study Session")
    
    with st.form("study_session_form"):
        session_date = st.date_input("Study Date", value=datetime.now().date())
        topic = st.text_input("What did you study?", placeholder="e.g., Python Functions, Data Structures")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=60)
        
        col1, col2 = st.columns(2)
        with col1:
            mood_rating = st.slider("How did you feel?", 1, 5, 3, help="1=Frustrated, 5=Great")
        with col2:
            productivity_rating = st.slider("How productive were you?", 1, 5, 3, help="1=Distracted, 5=Focused")
        
        # Enhanced note taking
        notes = st.text_area(
            "Session Notes", 
            placeholder="What did you learn? What concepts did you practice? Any challenges or breakthroughs?",
            help="Be specific about what you studied - this helps the AI analyze your progress better!"
        )
        
        # Analysis options
        st.write("**Analysis Options:**")
        analyze_session = st.checkbox(
            "🤖 Get AI Analysis", 
            value=True, 
            help="Analyze this session against your learning path and schedule"
        )
        
        # Add debug mode toggle
        debug_mode = st.checkbox("🔍 Enable Debug Mode", value=True, help="Show detailed debugging information")
        
        if st.form_submit_button("💾 Save & Analyze Session"):
            if not topic.strip():
                st.error("Please specify what you studied!")
                return
            
            # Prepare session data
            session_data = {
                'session_date': session_date,
                'topic': topic.strip(),
                'duration_minutes': duration,
                'mood_rating': mood_rating,
                'productivity_rating': productivity_rating,
                'notes': notes.strip()
            }
            
            # Get student ID
            student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
            student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
            
            with st.spinner("📊 Analyzing your study session..."):
                try:
                    from data.student_service import StudentService
                    service = StudentService()
                    
                    if analyze_session:
                        # Get comprehensive data for analysis
                        learning_paths = service.get_student_learning_paths(student_id)
                        current_progress = service.db.get_student_progress(student_id)
                        schedule_preferences = service.get_student_preferences(student_id)
                        
                        if debug_mode:
                            st.markdown("---")
                            st.subheader("🔍 DEBUG: Pre-Analysis Data")
                            
                            with st.expander("Current State"):
                                st.write("**Student ID:**", student_id)
                                st.write("**Topic Being Studied:**", topic.strip())
                                st.write("**Productivity Rating:**", productivity_rating)
                                st.write("**Current Completed Topics:**", current_progress.get('completed_topics', []))
                                st.write("**Current Progress Data:**")
                                st.json(current_progress)
                        
                        # Perform AI analysis
                        from agents.study_session_analyzer import StudySessionAnalyzer
                        analyzer = StudySessionAnalyzer()
                        
                        analysis = analyzer.analyze_study_session(
                            session_data, 
                            learning_paths, 
                            current_progress, 
                            schedule_preferences
                        )
                        
                        if debug_mode:
                            st.subheader("🔍 DEBUG: AI Analysis Results")
                            
                            with st.expander("Full Analysis", expanded=True):
                                st.json(analysis)
                            
                            progress_update = analysis.get('progress_update', {})
                            effectiveness = analysis.get('learning_effectiveness', {})
                            effectiveness_score = effectiveness.get('effectiveness_score', 0)
                            
                            st.write("**Key Analysis Results:**")
                            st.write(f"- **Effectiveness Score:** {effectiveness_score}%")
                            st.write(f"- **Topics to Mark Completed:** {progress_update.get('topics_to_mark_completed', [])}")
                            st.write(f"- **New Concepts Learned:** {progress_update.get('new_concepts_learned', [])}")
                            st.write(f"- **Areas Needing Review:** {progress_update.get('areas_needing_review', [])}")
                            
                            # Show completion logic
                            if effectiveness_score >= 70:
                                st.success(f"✅ Effectiveness score {effectiveness_score}% is ≥70% - topic should be marked as completed!")
                            else:
                                st.warning(f"⚠️ Effectiveness score {effectiveness_score}% is <70% - topic won't be auto-completed")
                        
                        # Save with analysis
                        success = service.record_analyzed_study_session(student_id, session_data, analysis)
                        
                        if debug_mode:
                            st.subheader("🔍 DEBUG: Database Update Results")
                        
                        if success:
                            st.success("✅ Study session analyzed and saved successfully!")
                            
                            # Show what was marked as completed
                            progress_update = analysis.get('progress_update', {})
                            completed_in_session = progress_update.get('topics_to_mark_completed', [])
                            session_topic = session_data.get('topic', '')
                            effectiveness_score = analysis.get('learning_effectiveness', {}).get('effectiveness_score', 0)
                            
                            if completed_in_session:
                                st.info(f"🎉 AI marked these topics as completed: {', '.join(completed_in_session)}")
                            elif effectiveness_score >= 70 and session_topic:
                                st.info(f"🎉 Auto-completing '{session_topic}' due to effectiveness score: {effectiveness_score}%")
                            else:
                                st.warning(f"⚠️ Topic not auto-completed. Effectiveness: {effectiveness_score}% (needs ≥70%)")
                            
                            # Check what was actually saved to database
                            if debug_mode:
                                # Get fresh data directly from database
                                fresh_progress = service.db.get_student_progress(student_id)
                                st.write("**Database Check After Save:**")
                                st.write(f"- **Completed Topics in DB:** {fresh_progress.get('completed_topics', [])}")
                                st.write(f"- **Completed Count:** {fresh_progress.get('completed_count', 0)}")
                                st.write(f"- **Total Topics:** {fresh_progress.get('total_topics', 0)}")
                                st.write(f"- **Progress Percentage:** {fresh_progress.get('progress_percentage', 0)}%")
                            
                            # REFRESH THE SESSION STATE WITH NEW DATA
                            fresh_data = service.get_student_historical_data(student_id)
                            if fresh_data:
                                st.session_state.existing_student_data = fresh_data
                                st.info("📊 Session state refreshed!")
                                
                                if debug_mode:
                                    fresh_progress_from_session = fresh_data.get('progress', {})
                                    st.write("**Session State After Refresh:**")
                                    st.write(f"- **Completed Topics:** {fresh_progress_from_session.get('completed_topics', [])}")
                                    st.write(f"- **Completed Count:** {fresh_progress_from_session.get('completed_count', 0)}")
                                    st.write(f"- **Total Topics:** {fresh_progress_from_session.get('total_topics', 0)}")
                                    st.write(f"- **Progress Percentage:** {fresh_progress_from_session.get('progress_percentage', 0)}%")
                            
                            # Display analysis results
                            display_study_analysis(analysis)
                            
                        else:
                            st.error("❌ Failed to save study session analysis!")
                            
                            if debug_mode:
                                st.write("**Debug: Attempting basic session save without analysis...**")
                                basic_success = service.record_study_session(student_id, session_data)
                                if basic_success:
                                    st.info("✅ Basic session saved successfully")
                                else:
                                    st.error("❌ Even basic session save failed")
                    else:
                        # Simple save without analysis
                        success = service.record_study_session(student_id, session_data)
                        if success:
                            st.success("✅ Study session logged successfully!")
                        else:
                            st.warning("⚠️ Could not save to database.")
                            
                except Exception as e:
                    st.error(f"Error processing study session: {str(e)}")
                    logger.error(f"Study session processing error: {str(e)}")
                    
                    if debug_mode:
                        st.write("**Full Error Details:**")
                        import traceback
                        st.code(traceback.format_exc())
    
    # Manual topic completion section
    st.markdown("---")
    st.subheader("🎯 Manual Topic Completion")
    st.info("If the AI analysis doesn't automatically mark your topic as completed, you can manually mark it here.")
    
    manual_topic = st.text_input("Topic to mark as completed:", value=topic if 'topic' in locals() else "")
    
    if st.button("✅ Mark Topic as Completed", key="manual_complete_button"):
        if manual_topic.strip():
            try:
                from data.student_service import StudentService
                service = StudentService()
                
                # Get student ID
                student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
                student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
                
                # Get current progress
                current_progress = service.db.get_student_progress(student_id)
                completed_topics = set(current_progress.get('completed_topics', []))
                
                # Add the topic
                if manual_topic.strip() not in completed_topics:
                    completed_topics.add(manual_topic.strip())
                    
                    # Save directly to database
                    import json
                    with service.db.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE student_progress 
                                SET completed_topics = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE student_id = %s
                            """, (json.dumps(list(completed_topics)), student_id))
                            
                            if cursor.rowcount == 0:
                                # Insert if not exists
                                cursor.execute("""
                                    INSERT INTO student_progress (student_id, completed_topics)
                                    VALUES (%s, %s)
                                """, (student_id, json.dumps(list(completed_topics))))
                            
                            conn.commit()
                    
                    st.success(f"✅ Manually marked '{manual_topic.strip()}' as completed!")
                    
                    # Refresh data
                    fresh_data = service.get_student_historical_data(student_id)
                    if fresh_data:
                        st.session_state.existing_student_data = fresh_data
                        st.rerun()
                else:
                    st.info(f"'{manual_topic.strip()}' is already marked as completed!")
                        
            except Exception as e:
                st.error(f"Error manually completing topic: {str(e)}")
                if debug_mode:
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.error("Please enter a topic name!")
def display_study_analysis(analysis: Dict[str, Any]):
    """Display the AI analysis of the study session."""
    st.markdown("---")
    st.subheader("🤖 AI Analysis of Your Study Session")
    
    # Topic Alignment
    topic_alignment = analysis.get('topic_alignment', {})
    col1, col2 = st.columns(2)
    
    with col1:
        alignment_score = topic_alignment.get('alignment_score', 0)
        st.metric(
            "Learning Path Alignment", 
            f"{alignment_score}%",
            help="How well this session aligns with your learning goals"
        )
    
    with col2:
        effectiveness = analysis.get('learning_effectiveness', {})
        effectiveness_score = effectiveness.get('effectiveness_score', 0)
        st.metric(
            "Session Effectiveness", 
            f"{effectiveness_score}%",
            help="Overall effectiveness of this study session"
        )
    
    # Progress Update
    progress_update = analysis.get('progress_update', {})
    if progress_update.get('topics_to_mark_completed'):
        st.success("🎉 **Topics Completed:** " + ", ".join(progress_update['topics_to_mark_completed']))
    
    if progress_update.get('new_concepts_learned'):
        st.info("📚 **New Concepts Learned:** " + ", ".join(progress_update['new_concepts_learned']))
    
    # Recommendations
    recommendations = analysis.get('recommendations', {})
    if recommendations.get('immediate_next_steps'):
        st.write("**🎯 Next Steps:**")
        for step in recommendations['immediate_next_steps']:
            st.write(f"• {step}")
    
    # Insights
    insights = analysis.get('insights', {})
    
    col1, col2 = st.columns(2)
    with col1:
        if insights.get('strengths_demonstrated'):
            st.write("**💪 Strengths Observed:**")
            for strength in insights['strengths_demonstrated']:
                st.write(f"• {strength}")
    
    with col2:
        if insights.get('challenges_identified'):
            st.write("**⚠️ Areas to Address:**")
            for challenge in insights['challenges_identified']:
                st.write(f"• {challenge}")
    
    # Schedule Analysis
    schedule_analysis = analysis.get('schedule_analysis', {})
    if schedule_analysis:
        st.write("**📅 Schedule Analysis:**")
        
        if schedule_analysis.get('follows_preferred_schedule'):
            st.success("✅ Session aligns with your preferred schedule")
        else:
            st.warning("⚠️ Consider adjusting timing to match your optimal schedule")
        
        duration_assessment = schedule_analysis.get('duration_appropriateness', 'optimal')
        if duration_assessment == 'optimal':
            st.info("⏱️ Session duration was optimal")
        elif duration_assessment == 'too_short':
            st.warning("⏱️ Consider longer study sessions for better retention")
        elif duration_assessment == 'too_long':
            st.warning("⏱️ Consider shorter, more focused sessions")
    
    # Show detailed analysis in expandable section
    with st.expander("🔍 Detailed Analysis"):
        st.json(analysis)

def show_study_session_form(student_name):
    """Show form to log a study session with comprehensive analysis."""
    st.subheader("📝 Log Study Session")
    
    with st.form("study_session_form"):
        session_date = st.date_input("Study Date", value=datetime.now().date())
        topic = st.text_input("What did you study?", placeholder="e.g., Python Functions, Data Structures")
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=480, value=60)
        
        col1, col2 = st.columns(2)
        with col1:
            mood_rating = st.slider("How did you feel?", 1, 5, 3, help="1=Frustrated, 5=Great")
        with col2:
            productivity_rating = st.slider("How productive were you?", 1, 5, 3, help="1=Distracted, 5=Focused")
        
        # Enhanced note taking
        notes = st.text_area(
            "Session Notes", 
            placeholder="What did you learn? What concepts did you practice? Any challenges or breakthroughs?",
            help="Be specific about what you studied - this helps the AI analyze your progress better!"
        )
        
        # Analysis options
        st.write("**Analysis Options:**")
        analyze_session = st.checkbox(
            "🤖 Get AI Analysis", 
            value=True, 
            help="Analyze this session against your learning path and schedule"
        )
        
        # Add debug mode toggle
        debug_mode = st.checkbox("🔍 Enable Debug Mode", value=True, help="Show detailed debugging information")
        
        if st.form_submit_button("💾 Save & Analyze Session"):
            if not topic.strip():
                st.error("Please specify what you studied!")
                return
            
            # Prepare session data
            session_data = {
                'session_date': session_date,
                'topic': topic.strip(),
                'duration_minutes': duration,
                'mood_rating': mood_rating,
                'productivity_rating': productivity_rating,
                'notes': notes.strip()
            }
            
            # Get student ID
            student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
            student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
            
            with st.spinner("📊 Analyzing your study session..."):
                try:
                    from data.student_service import StudentService
                    service = StudentService()
                    
                    if analyze_session:
                        # Get comprehensive data for analysis
                        learning_paths = service.get_student_learning_paths(student_id)
                        current_progress = service.db.get_student_progress(student_id)
                        schedule_preferences = service.get_student_preferences(student_id)
                        
                        if debug_mode:
                            st.markdown("---")
                            st.subheader("🔍 DEBUG: Pre-Analysis Data")
                            
                            with st.expander("Current State"):
                                st.write("**Student ID:**", student_id)
                                st.write("**Topic Being Studied:**", topic.strip())
                                st.write("**Productivity Rating:**", productivity_rating)
                                st.write("**Current Completed Topics:**", current_progress.get('completed_topics', []))
                                st.write("**Current Progress Data:**")
                                st.json(current_progress)
                        
                        # Perform AI analysis
                        from agents.study_session_analyzer import StudySessionAnalyzer
                        analyzer = StudySessionAnalyzer()
                        
                        analysis = analyzer.analyze_study_session(
                            session_data, 
                            learning_paths, 
                            current_progress, 
                            schedule_preferences
                        )
                        
                        if debug_mode:
                            st.subheader("🔍 DEBUG: AI Analysis Results")
                            
                            with st.expander("Full Analysis", expanded=True):
                                st.json(analysis)
                            
                            progress_update = analysis.get('progress_update', {})
                            effectiveness = analysis.get('learning_effectiveness', {})
                            effectiveness_score = effectiveness.get('effectiveness_score', 0)
                            
                            st.write("**Key Analysis Results:**")
                            st.write(f"- **Effectiveness Score:** {effectiveness_score}%")
                            st.write(f"- **Topics to Mark Completed:** {progress_update.get('topics_to_mark_completed', [])}")
                            st.write(f"- **New Concepts Learned:** {progress_update.get('new_concepts_learned', [])}")
                            st.write(f"- **Areas Needing Review:** {progress_update.get('areas_needing_review', [])}")
                            
                            # Show completion logic
                            if effectiveness_score >= 70:
                                st.success(f"✅ Effectiveness score {effectiveness_score}% is ≥70% - topic should be marked as completed!")
                            else:
                                st.warning(f"⚠️ Effectiveness score {effectiveness_score}% is <70% - topic won't be auto-completed")
                        
                        # Save with analysis
                        success = service.record_analyzed_study_session(student_id, session_data, analysis)
                        
                        if debug_mode:
                            st.subheader("🔍 DEBUG: Database Update Results")
                        
                        if success:
                            st.success("✅ Study session analyzed and saved successfully!")
                            
                            # Show what was marked as completed
                            progress_update = analysis.get('progress_update', {})
                            completed_in_session = progress_update.get('topics_to_mark_completed', [])
                            session_topic = session_data.get('topic', '')
                            effectiveness_score = analysis.get('learning_effectiveness', {}).get('effectiveness_score', 0)
                            
                            if completed_in_session:
                                st.info(f"🎉 AI marked these topics as completed: {', '.join(completed_in_session)}")
                            elif effectiveness_score >= 70 and session_topic:
                                st.info(f"🎉 Auto-completing '{session_topic}' due to effectiveness score: {effectiveness_score}%")
                            else:
                                st.warning(f"⚠️ Topic not auto-completed. Effectiveness: {effectiveness_score}% (needs ≥70%)")
                            
                            # Check what was actually saved to database
                            if debug_mode:
                                # Get fresh data directly from database
                                fresh_progress = service.db.get_student_progress(student_id)
                                st.write("**Database Check After Save:**")
                                st.write(f"- **Completed Topics in DB:** {fresh_progress.get('completed_topics', [])}")
                                st.write(f"- **Completed Count:** {fresh_progress.get('completed_count', 0)}")
                                st.write(f"- **Total Topics:** {fresh_progress.get('total_topics', 0)}")
                                st.write(f"- **Progress Percentage:** {fresh_progress.get('progress_percentage', 0)}%")
                            
                            # REFRESH THE SESSION STATE WITH NEW DATA
                            fresh_data = service.get_student_historical_data(student_id)
                            if fresh_data:
                                st.session_state.existing_student_data = fresh_data
                                st.info("📊 Session state refreshed!")
                                
                                if debug_mode:
                                    fresh_progress_from_session = fresh_data.get('progress', {})
                                    st.write("**Session State After Refresh:**")
                                    st.write(f"- **Completed Topics:** {fresh_progress_from_session.get('completed_topics', [])}")
                                    st.write(f"- **Completed Count:** {fresh_progress_from_session.get('completed_count', 0)}")
                                    st.write(f"- **Total Topics:** {fresh_progress_from_session.get('total_topics', 0)}")
                                    st.write(f"- **Progress Percentage:** {fresh_progress_from_session.get('progress_percentage', 0)}%")
                            
                            # Display analysis results
                            display_study_analysis(analysis)
                            
                        else:
                            st.error("❌ Failed to save study session analysis!")
                            
                            if debug_mode:
                                st.write("**Debug: Attempting basic session save without analysis...**")
                                basic_success = service.record_study_session(student_id, session_data)
                                if basic_success:
                                    st.info("✅ Basic session saved successfully")
                                else:
                                    st.error("❌ Even basic session save failed")
                    else:
                        # Simple save without analysis
                        success = service.record_study_session(student_id, session_data)
                        if success:
                            st.success("✅ Study session logged successfully!")
                        else:
                            st.warning("⚠️ Could not save to database.")
                            
                except Exception as e:
                    st.error(f"Error processing study session: {str(e)}")
                    logger.error(f"Study session processing error: {str(e)}")
                    
                    if debug_mode:
                        st.write("**Full Error Details:**")
                        import traceback
                        st.code(traceback.format_exc())
    
    # Manual topic completion section
    st.markdown("---")
    st.subheader("🎯 Manual Topic Completion")
    st.info("If the AI analysis doesn't automatically mark your topic as completed, you can manually mark it here.")
    
    manual_topic = st.text_input("Topic to mark as completed:", value=topic if 'topic' in locals() else "")
    
    if st.button("✅ Mark Topic as Completed", key="manual_complete_button"):
        if manual_topic.strip():
            try:
                from data.student_service import StudentService
                service = StudentService()
                
                # Get student ID
                student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
                student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
                
                # Get current progress
                current_progress = service.db.get_student_progress(student_id)
                completed_topics = set(current_progress.get('completed_topics', []))
                
                # Add the topic
                if manual_topic.strip() not in completed_topics:
                    completed_topics.add(manual_topic.strip())
                    
                    # Save directly to database
                    import json
                    with service.db.get_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE student_progress 
                                SET completed_topics = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE student_id = %s
                            """, (json.dumps(list(completed_topics)), student_id))
                            
                            if cursor.rowcount == 0:
                                # Insert if not exists
                                cursor.execute("""
                                    INSERT INTO student_progress (student_id, completed_topics)
                                    VALUES (%s, %s)
                                """, (student_id, json.dumps(list(completed_topics))))
                            
                            conn.commit()
                    
                    st.success(f"✅ Manually marked '{manual_topic.strip()}' as completed!")
                    
                    # Refresh data
                    fresh_data = service.get_student_historical_data(student_id)
                    if fresh_data:
                        st.session_state.existing_student_data = fresh_data
                        st.rerun()
                else:
                    st.info(f"'{manual_topic.strip()}' is already marked as completed!")
                        
            except Exception as e:
                st.error(f"Error manually completing topic: {str(e)}")
                if debug_mode:
                    import traceback
                    st.code(traceback.format_exc())
        else:
            st.error("Please enter a topic name!")

    st.markdown("---")
    st.subheader("🔍 Debug: Learning Path Topics")
    
    if st.button("Show Learning Path Topics", key="show_lp_topics"):
        try:
            from data.student_service import StudentService
            service = StudentService()
            
            student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
            student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
            
            learning_paths = service.get_student_learning_paths(student_id)
            
            st.write("**Learning Paths Found:**")
            for i, path in enumerate(learning_paths):
                st.write(f"**Path {i+1}:** {path.get('topic', 'Unknown')}")
                topics = path.get('topics', [])
                
                if isinstance(topics, list):
                    st.write("**Topics in this path:**")
                    for j, topic in enumerate(topics):
                        if isinstance(topic, dict):
                            topic_name = topic.get('name', f'Topic {j+1}')
                            st.write(f"  {j+1}. {topic_name}")
                        else:
                            st.write(f"  {j+1}. {topic}")
                else:
                    st.write(f"Topics data: {topics}")
        except Exception as e:
            st.error(f"Error getting learning path topics: {str(e)}")

def show_assessment_form(student_name):
    """Show form to record an assessment."""
    st.subheader("🧪 Record Assessment")
    
    with st.form("assessment_form"):
        assessment_name = st.text_input("Assessment Name", placeholder="e.g., Python Quiz 1")
        assessment_type = st.selectbox("Type", ["Quiz", "Project", "Exercise", "Test"])
        
        col1, col2 = st.columns(2)
        with col1:
            max_score = st.number_input("Maximum Score", min_value=1, value=100)
        with col2:
            achieved_score = st.number_input("Your Score", min_value=0, value=0)
        
        time_taken = st.number_input("Time Taken (minutes)", min_value=1, value=30)
        feedback = st.text_area("Feedback/Notes", placeholder="What went well? What needs improvement?")
        
        # Remove the key parameter from form_submit_button
        if st.form_submit_button("💾 Save Assessment"):
            percentage = (achieved_score / max_score) * 100
            
            assessment_data = {
                'assessment_name': assessment_name,
                'assessment_type': assessment_type,
                'max_score': max_score,
                'achieved_score': achieved_score,
                'percentage': percentage,
                'time_taken_minutes': time_taken,
                'feedback': feedback
            }
            
            # Try to save to database
            try:
                from data.student_service import StudentService
                service = StudentService()
                # Get student ID from session state if available
                student_info = st.session_state.get('existing_student_data', {}).get('student_info', {})
                student_id = student_info.get('student_id', f"student_{student_name.lower().replace(' ', '_')}")
                
                success = service.record_assessment(student_id, assessment_data)
                if success:
                    st.success(f"✅ Assessment recorded! Score: {percentage:.1f}%")
                else:
                    st.warning("⚠️ Could not save to database, but assessment recorded.")
                    st.success(f"✅ Assessment recorded locally! Score: {percentage:.1f}%")
            except Exception as e:
                st.warning(f"⚠️ Database error: {str(e)}")
                st.success(f"✅ Assessment recorded locally! Score: {percentage:.1f}%")

def display_new_student_form(student_name, student_id):
    """Display the form for new students to create their learning plan."""
    
    st.header(f"🆕 Welcome {student_name}! Let's create your learning plan.")
    
    # Main content area with tabs for new student
    tab1, tab2, tab3 = st.tabs(["⏰ Schedule Preferences", "📊 Learning Preferences", "🎯 Success Criteria"])
    
    with tab1:
        st.header("⏰ Schedule Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Available Study Times")
            
            # Weekly availability
            st.write("**Select your available days:**")
            available_days = []
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            for day in days:
                if st.checkbox(day, value=day in ["Monday", "Wednesday", "Friday"], key=f"day_{day}"):
                    available_days.append(day)
            
            # Time preferences
            st.write("**Preferred study times:**")
            morning = st.checkbox("Morning (9:00-12:00)", value=True, key="time_morning")
            afternoon = st.checkbox("Afternoon (13:00-17:00)", value=True, key="time_afternoon")
            evening = st.checkbox("Evening (18:00-21:00)", key="time_evening")
            
            # Study duration
            study_duration = st.slider("Preferred session duration (hours)", 1, 4, 2)
            weekly_hours = st.slider("Total weekly study hours", 5, 40, 10)
        
        with col2:
            st.subheader("Break Preferences")
            
            break_frequency = st.selectbox(
                "Break frequency",
                ["Every 30 minutes", "Every hour", "Every 1.5 hours", "Every 2 hours"],
                index=1
            )
            
            break_duration = st.selectbox(
                "Break duration",
                ["5 minutes", "10 minutes", "15 minutes", "20 minutes"],
                index=1
            )
            
            st.subheader("Unavailable Times")
            unavailable_times = st.text_area(
                "When are you unavailable?",
                placeholder="e.g., Weekends, Tuesday evenings, 12:00-13:00 daily"
            )
            
            # Custom habits
            st.subheader("Study Habits")
            custom_habits = st.text_area(
                "Any specific study habits or routines?",
                placeholder="e.g., Review notes before sleep, Morning warm-up exercises"
            )
    
    with tab2:
        st.header("📊 Learning Preferences")
        
        # Learning Topic
        st.subheader("🎯 What do you want to learn?")
        learning_topics = [
            "Python Programming", "JavaScript", "Data Science", "Machine Learning", 
            "Web Development", "Mobile Development", "Database Management", 
            "Cybersecurity", "Cloud Computing", "Other"
        ]
        selected_topic = st.selectbox("Primary Topic", learning_topics)
        
        if selected_topic == "Other":
            custom_topic = st.text_input("Specify your topic")
            current_topic = custom_topic if custom_topic else "Programming"
        else:
            current_topic = selected_topic
        
        # Experience Level
        experience_level = st.select_slider(
            "Experience Level",
            options=["Complete Beginner", "Beginner", "Intermediate", "Advanced", "Expert"],
            value="Beginner"
        )
        
        # Learning Goals
        st.subheader("🎯 Learning Goals")
        goals = st.multiselect(
            "What are your learning objectives?",
            [
                "Learn fundamentals", "Build projects", "Get certified", 
                "Career change", "Skill improvement", "Academic requirement",
                "Personal interest", "Prepare for interviews"
            ],
            default=["Learn fundamentals"]
        )
        
        custom_goal = st.text_input("Any specific goal?", placeholder="e.g., Build a web app")
        if custom_goal:
            goals.append(custom_goal)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Learning Style")
            learning_style = st.multiselect(
                "How do you learn best?",
                [
                    "Visual (diagrams, charts)", "Auditory (lectures, discussions)",
                    "Hands-on practice", "Reading documentation", "Video tutorials",
                    "Interactive exercises", "Group study", "Self-paced learning"
                ],
                default=["Hands-on practice", "Video tutorials"]
            )
            
            difficulty_preference = st.select_slider(
                "Preferred difficulty progression",
                options=["Very gradual", "Gradual", "Moderate", "Challenging", "Intensive"],
                value="Gradual"
            )
            
            project_preference = st.checkbox("Include practical projects", value=True)
        
        with col2:
            st.subheader("Focus Areas")
            focus_areas = st.multiselect(
                "What aspects to emphasize?",
                [
                    "Theory and concepts", "Practical application", "Problem solving",
                    "Best practices", "Industry standards", "Certification prep",
                    "Portfolio building", "Interview preparation"
                ],
                default=["Practical application", "Problem solving"]
            )
            
            # Assessment preferences
            assessment_type = st.multiselect(
                "Preferred assessment methods",
                ["Quizzes", "Coding exercises", "Projects", "Peer review", "Self-assessment"],
                default=["Coding exercises", "Projects"]
            )
    
    with tab3:
        st.header("🎯 Success Criteria")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Performance Targets")
            success_threshold = st.slider("Target success rate (%)", 50, 100, 75)
            
            completion_timeline = st.selectbox(
                "Desired completion timeline",
                ["1 month", "2 months", "3 months", "6 months", "1 year", "Flexible"],
                index=2
            )
            
            priority_metrics = st.multiselect(
                "What metrics matter most to you?",
                [
                    "Completion rate", "Understanding depth", "Practical skills",
                    "Speed of learning", "Retention", "Application ability"
                ],
                default=["Understanding depth", "Practical skills"]
            )
        
        with col2:
            st.subheader("Motivation & Accountability")
            motivation_factors = st.multiselect(
                "What motivates you?",
                [
                    "Progress tracking", "Achievements/badges", "Regular feedback",
                    "Peer comparison", "Real-world applications", "Career advancement",
                    "Personal satisfaction", "External deadlines"
                ],
                default=["Progress tracking", "Regular feedback"]
            )
            
            feedback_frequency = st.selectbox(
                "How often do you want progress feedback?",
                ["Daily", "Every few days", "Weekly", "Bi-weekly", "Monthly"],
                index=2
            )
    
    # Generate coaching plan button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Generate My Learning Plan", type="primary", use_container_width=True, key="generate_plan_button"):
            if not current_topic:
                st.error("Please specify what you want to learn.")
            else:
                # Generate the learning plan
                result = generate_learning_plan(
                    student_name, student_id, current_topic, experience_level, goals,
                    available_days, morning, afternoon, evening, study_duration, weekly_hours,
                    break_frequency, break_duration, unavailable_times, custom_habits,
                    learning_style, difficulty_preference, project_preference, focus_areas,
                    assessment_type, success_threshold, completion_timeline, priority_metrics,
                    motivation_factors, feedback_frequency
                )
                
                # Store result in session state
                st.session_state.learning_plan_result = result
    
    # Display results if available
    if st.session_state.learning_plan_result:
        st.markdown("---")
        display_results(student_name, st.session_state.learning_plan_result)

def generate_learning_plan(
    student_name, student_id, current_topic, experience_level, goals,
    available_days, morning, afternoon, evening, study_duration, weekly_hours,
    break_frequency, break_duration, unavailable_times, custom_habits,
    learning_style, difficulty_preference, project_preference, focus_areas,
    assessment_type, success_threshold, completion_timeline, priority_metrics,
    motivation_factors, feedback_frequency
):
    """Generate the learning plan based on student input."""
    
    with st.spinner("🤖 AI Coach is analyzing your preferences and creating your personalized learning plan..."):
        try:
            # Build comprehensive student data from form inputs
            student_data = {
                "student_id": student_id or f"student_{student_name.lower().replace(' ', '_')}",
                "student_name": student_name,
                "current_topic": current_topic,
                "experience_level": experience_level,
                "goals": goals,
                "learning_preferences": {
                    "learning_style": learning_style,
                    "difficulty_preference": difficulty_preference,
                    "project_preference": project_preference,
                    "focus_areas": focus_areas,
                    "assessment_type": assessment_type
                },
                "schedule_preferences": {
                    "available_days": available_days,
                    "time_preferences": {
                        "morning": morning,
                        "afternoon": afternoon,
                        "evening": evening
                    },
                    "study_duration": study_duration,
                    "weekly_hours": weekly_hours,
                    "break_frequency": break_frequency,
                    "break_duration": break_duration,
                    "unavailable_times": unavailable_times,
                    "custom_habits": custom_habits
                },
                "success_criteria": {
                    "success_threshold": success_threshold,
                    "completion_timeline": completion_timeline,
                    "priority_metrics": priority_metrics,
                    "motivation_factors": motivation_factors,
                    "feedback_frequency": feedback_frequency
                }
            }
            
            logger.info(f"Generating learning plan for new student: {student_name}")
            
            # Create coach graph and generate plan
            coach_graph = create_coach_graph()
            result = coach_graph.invoke({
                "student_data": student_data,
                "messages": []
            })
            
            logger.info(f"Learning plan generated successfully for {student_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating learning plan: {str(e)}")
            st.error(f"Sorry, there was an error generating your learning plan: {str(e)}")
            return None

def display_results(student_name, result):
    """Display the coaching results in a nice format."""
    
    if not result:
        st.error("❌ No results to display. Please try generating a new learning plan.")
        return
    
    st.success(f"🎉 Learning plan for **{student_name}**!")
    
    # Create tabs for different sections
    result_tab1, result_tab2, result_tab3, result_tab4 = st.tabs([
        "📚 Learning Path", 
        "📊 Progress Summary", 
        "📅 Schedule", 
        "🎯 Adaptive Analysis"
    ])
    
    with result_tab1:
        st.header("📚 Your Personalized Learning Path")
        
        learning_path = result.get("learning_path", {})
        
        if learning_path and learning_path.get("topics"):
            # Progress overview
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Stage", learning_path.get("current_stage", "Unknown"))
            with col2:
                progress = learning_path.get("progress", 0)
                st.metric("Progress", f"{progress*100:.1f}%")
            with col3:
                topics = learning_path.get("topics", [])
                st.metric("Total Topics", len(topics))
            
            # Topics breakdown
            st.subheader("📋 Learning Topics")
            
            for i, topic in enumerate(topics, 1):
                with st.expander(f"**{i}. {topic.get('name', 'Unknown Topic')}**", expanded=i==1):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write("**Description:**")
                        st.write(topic.get('description', 'No description available'))
                    with col2:
                        st.metric("Estimated Time", topic.get('estimated_time', 'Unknown'))
        else:
            st.warning("❌ No learning path data available. Please try generating a new plan.")
    
    with result_tab2:
        st.header("📊 Progress Summary")
        
        progress_summary = result.get("progress_summary", {})
        
        if progress_summary:
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                avg_score = progress_summary.get("average_score", 0)
                st.metric("Average Score", f"{avg_score:.1f}%")
            with col2:
                completed = len(progress_summary.get("completed_topics", []))
                st.metric("Completed Topics", completed)
            with col3:
                threshold_info = progress_summary.get("success_threshold", {})
                threshold = threshold_info.get("student_setting", "Not set")
                st.metric("Success Threshold", f"{threshold}%")
            with col4:
                meeting_threshold = threshold_info.get("meeting_threshold", False)
                status = "✅ Yes" if meeting_threshold else "❌ No"
                st.metric("Meeting Threshold", status)
            
            # AI Insights
            insights = progress_summary.get("ai_insights", [])
            if insights:
                st.subheader("🤖 AI Insights")
                for insight in insights:
                    st.info(f"💡 {insight}")
            
            # Next steps
            next_steps = progress_summary.get("next_steps", [])
            if next_steps:
                st.subheader("🎯 Next Steps")
                for i, step in enumerate(next_steps, 1):
                    st.write(f"{i}. {step}")
        else:
            st.warning("❌ No progress summary data available.")
    
    with result_tab3:
        st.header("📅 Your Study Schedule")
        
        schedule = result.get("schedule", {})
        
        if schedule:
            # Weekly schedule display
            weekly_schedule = schedule.get("weekly_schedule", [])
            if weekly_schedule:
                st.subheader("📅 Weekly Schedule")
                
                # Create a better schedule display
                schedule_data = {}
                for session in weekly_schedule:
                    day = session.get("day", "Unknown")
                    if day not in schedule_data:
                        schedule_data[day] = []
                    schedule_data[day].append(session)
                
                # Display in columns
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                cols = st.columns(7)
                
                for i, day in enumerate(days):
                    with cols[i]:
                        st.markdown(f"**{day}**")
                        if day in schedule_data:
                            for session in schedule_data[day]:
                                time_slot = session.get("time", "")
                                activity = session.get("activity", "")
                                session_type = session.get("type", "")
                                
                                if session_type == "break":
                                    st.markdown(f"☕ `{time_slot}`")
                                    st.caption(activity)
                                else:
                                    st.markdown(f"📚 `{time_slot}`")
                                    st.caption(activity)
                        else:
                            st.markdown("*Free day*")
            
            # Study sessions
            study_sessions = schedule.get("study_sessions", [])
            if study_sessions:
                st.subheader("📖 Study Session Types")
                cols = st.columns(min(len(study_sessions), 3))
                for i, session in enumerate(study_sessions):
                    with cols[i % 3]:
                        st.markdown(f"**{session.get('session', 'Unknown')}**")
                        st.write(f"⏱️ Duration: {session.get('duration', 'Unknown')}")
                        st.write(f"🎯 Focus: {session.get('focus', 'Unknown')}")
            
            # Custom habits
            custom_habits = schedule.get("custom_habits", [])
            if custom_habits:
                st.subheader("🔄 Custom Study Habits")
                for habit in custom_habits:
                    st.write(f"• **{habit.get('habit', 'Unknown')}** - {habit.get('time', 'Unknown')} ({habit.get('frequency', 'Unknown')})")
        else:
            st.warning("❌ No schedule data available.")
    
    with result_tab4:
        st.header("🎯 Adaptive Analysis & Recommendations")
        
        adaptive_analysis = result.get("adaptive_analysis", {})
        
        if adaptive_analysis:
            # Personalized suggestions
            suggestions = adaptive_analysis.get("personalized_suggestions", [])
            if suggestions:
                st.subheader("💡 Personalized Suggestions")
                for suggestion in suggestions:
                    priority = suggestion.get("priority", "Medium")
                    category = suggestion.get("category", "General")
                    text = suggestion.get("suggestion", "No suggestion")
                    reason = suggestion.get("reason", "No reason provided")
                    
                    priority_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
                    
                    with st.expander(f"{priority_icon} [{priority}] {category}: {text}"):
                        st.write(f"**Reason:** {reason}")
            
            # Progress against goals
            progress_goals = adaptive_analysis.get("progress_against_goals", {})
            if progress_goals:
                st.subheader("🎯 Progress Against Goals")
                col1, col2 = st.columns(2)
                with col1:
                    weekly_goal = progress_goals.get("weekly_goal", "No goal set")
                    st.write(f"**Weekly Goal:** {weekly_goal}")
                    
                    progress_pct = progress_goals.get("progress_percentage", 0)
                    st.progress(progress_pct / 100)
                    st.write(f"Progress: {progress_pct}%")
                
                with col2:
                    on_track = progress_goals.get("on_track", False)
                    track_status = "✅ On Track" if on_track else "⚠️ Needs Attention"
                    st.write(f"**Status:** {track_status}")
                    
                    adjustment = progress_goals.get("adjustment_needed", "Continue current plan")
                    st.write(f"**Recommendation:** {adjustment}")
        else:
            st.warning("❌ No adaptive analysis data available.")
    
    # Export functionality with unique keys
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export Learning Plan", key="export_plan_button"):
            import json
            json_str = json.dumps(result, indent=2, default=str)
            st.download_button(
                label="Download as JSON",
                data=json_str,
                file_name=f"learning_plan_{student_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="download_plan_button"
            )
    
    with col2:
        if st.button("🔄 Clear Results", key="clear_results_button"):
            st.session_state.learning_plan_result = None
            st.rerun()

def main():
    st.set_page_config(
        page_title="AI Learning Coach",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎓 AI Learning Coach")
    st.markdown("*Your personalized learning companion*")
    
    # Check environment
    if not check_environment():
        st.stop()
    
    # Initialize session state
    if 'learning_plan_result' not in st.session_state:
        st.session_state.learning_plan_result = None
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""
    if 'existing_student_data' not in st.session_state:
        st.session_state.existing_student_data = None
    if 'student_id' not in st.session_state:
        st.session_state.student_id = ""
    if 'student_search_performed' not in st.session_state:
        st.session_state.student_search_performed = False
    if 'potential_conflicts' not in st.session_state:
        st.session_state.potential_conflicts = []
    if 'last_searched_name' not in st.session_state:
        st.session_state.last_searched_name = ""
    if 'last_searched_id' not in st.session_state:
        st.session_state.last_searched_id = ""
    
    # Sidebar for student input
    with st.sidebar:
        st.header("📝 Student Profile")
        
        # Database status
        st.subheader("System Status")
        db_connected = check_database_status()
        
        if not db_connected:
            st.error("❌ Database not connected. Running in demo mode.")
        
        # Basic Information
        st.subheader("Basic Information")
        student_name = st.text_input("Your Name", placeholder="Enter your name", key="student_name_input")
        student_id = st.text_input("Student ID (optional)", placeholder="e.g., student123", key="student_id_input")
        
        # Add a clear button
        if st.button("🗑️ Clear Session", key="clear_session_button"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        # Search button to explicitly trigger student lookup
        if st.button("🔍 Search Student Records", key="search_student_button"):
            if student_name or student_id:
                st.session_state.student_search_performed = True
                with st.spinner("Searching for existing student records..."):
                    existing_data, exact_match, conflicts = find_existing_student(student_name, student_id)
                    
                    st.session_state.existing_student_data = existing_data
                    st.session_state.potential_conflicts = conflicts
                    
                    if exact_match and existing_data:
                        student_info = existing_data.get('student_info', {})
                        st.success(f"✅ Welcome back, {student_info.get('student_name', student_name)}!")
                        st.info(f"Student ID: {student_info.get('student_id', 'Unknown')}")
                        
                        # Show quick stats
                        progress_data = existing_data.get('progress', {})
                        if progress_data:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Completed Topics", len(progress_data.get('completed_topics', [])))
                            with col2:
                                st.metric("Average Score", f"{progress_data.get('average_score', 0):.1f}%")
                            
                            last_study = progress_data.get('last_study_date')
                            if last_study:
                                st.caption(f"Last study: {last_study}")
                    
                    elif conflicts:
                        st.warning("⚠️ Multiple records found!")
                        st.write("**Please clarify:**")
                        for conflict in conflicts:
                            st.write(f"• {conflict}")
                        st.info("💡 Please provide both name and ID for exact match")
                    
                    else:
                        st.info("🆕 New student detected!")
                        suggested_id = student_id or f"student_{student_name.lower().replace(' ', '_')}"
                        st.write(f"**Suggested ID:** {suggested_id}")
            else:
                st.error("Please enter at least your name or student ID")
        
        # Show conflicts if any
        if st.session_state.potential_conflicts:
            st.subheader("⚠️ Student Record Conflicts")
            for conflict in st.session_state.potential_conflicts:
                st.warning(conflict)
            st.info("💡 Please provide both name and ID to resolve conflicts")
    
    # Main content logic
    if st.session_state.existing_student_data and st.session_state.student_search_performed:
        # Display existing student dashboard
        student_info = st.session_state.existing_student_data.get('student_info', {})
        display_existing_student_dashboard(
            student_info.get('student_name', student_name), 
            st.session_state.existing_student_data
        )
    
    elif st.session_state.student_search_performed and not st.session_state.existing_student_data and not st.session_state.potential_conflicts:
        # Show form for new student
        if student_name:
            display_new_student_form(student_name, student_id)
        else:
            st.error("Please enter your name to continue.")
    
    elif st.session_state.potential_conflicts:
        # Show conflict resolution
        display_conflict_resolution(student_name, student_id)
    
    else:
        # Welcome screen
        st.markdown("""
        ## Welcome to AI Learning Coach! 🎓
        
        Get started by entering your name in the sidebar and clicking "Search Student Records". 
        If you're a returning student, we'll show your existing learning progress. 
        If you're new, we'll help you create a personalized learning plan.
        
        ### Features:
        - 📚 **Personalized Learning Paths** - Tailored to your goals and experience
        - 📊 **Progress Tracking** - See your learning journey over time  
        - 📅 **Smart Scheduling** - Optimized study schedules based on your availability
        - 🎯 **Adaptive Analysis** - AI-powered insights to improve your learning
        
        ### Getting Started:
        1. Enter your name (and student ID if you have one) in the sidebar
        2. Click "Search Student Records"
        3. If you're new, fill out your preferences
        4. Get your personalized learning plan!
        
        ### Note:
        - If you have the same name as another student, please provide your student ID
        - Your student ID will be automatically generated if not provided
        """)

if __name__ == "__main__":
    main()