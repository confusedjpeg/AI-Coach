from typing import Dict, Any, Optional, List
from data.database import DatabaseManager
import logging
import json

logger = logging.getLogger(__name__)

class StudentService:
    """Service layer for student data operations."""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def debug_database_contents(self):
        """Debug function to see what's in the database."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if students table exists
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'students'
                    """)
                    table_exists = cursor.fetchone()
                    logger.info(f"Students table exists: {bool(table_exists)}")
                    
                    if table_exists:
                        # Count students
                        cursor.execute("SELECT COUNT(*) FROM students")
                        count = cursor.fetchone()[0]
                        logger.info(f"Total students in database: {count}")
                        
                        # Show all students
                        cursor.execute("SELECT student_id, student_name, email FROM students LIMIT 10")
                        students = cursor.fetchall()
                        for student in students:
                            logger.info(f"Student: ID={student[0]}, Name={student[1]}, Email={student[2]}")
                        
                        # Also check learning_paths table
                        cursor.execute("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' AND table_name = 'learning_paths'
                        """)
                        learning_paths_exists = cursor.fetchone()
                        logger.info(f"Learning paths table exists: {bool(learning_paths_exists)}")
                        
                        if learning_paths_exists:
                            cursor.execute("SELECT COUNT(*) FROM learning_paths")
                            lp_count = cursor.fetchone()[0]
                            logger.info(f"Total learning paths in database: {lp_count}")
                            
                            # Show all learning paths
                            cursor.execute("SELECT id, student_id, topic, current_stage FROM learning_paths LIMIT 10")
                            paths = cursor.fetchall()
                            for path in paths:
                                logger.info(f"Learning Path: ID={path[0]}, Student={path[1]}, Topic={path[2]}, Stage={path[3]}")
                    
                    return table_exists is not None
        except Exception as e:
            logger.error(f"Error debugging database: {str(e)}")
            return False
    
    def create_test_student(self):
        """Create a test student for debugging."""
        try:
            test_student = {
                'student_id': 'test_student_123',
                'student_name': 'Test User',
                'email': 'test@example.com',
                'experience_level': 'Beginner',
                'current_topic': 'Python Programming',
                'goals': ['Learn fundamentals'],
                'learning_preferences': {
                    'learning_style': ['Hands-on practice'],
                    'difficulty_preference': 'Gradual'
                },
                'schedule_preferences': {
                    'available_days': ['Monday', 'Wednesday', 'Friday'],
                    'weekly_hours': 10
                },
                'success_criteria': {
                    'success_threshold': 75
                }
            }
            
            success = self.db.save_student(test_student)
            logger.info(f"Test student created: {success}")
            return success
        except Exception as e:
            logger.error(f"Error creating test student: {str(e)}")
            return False
    
    def get_student_learning_paths(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all learning paths for a student."""
        try:
            logger.info(f"Getting learning paths for student: {student_id}")
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, student_id, topic, current_stage, overall_progress, 
                               topics, created_at, is_active
                        FROM learning_paths 
                        WHERE student_id = %s 
                        ORDER BY created_at DESC
                    """, (student_id,))
                    
                    results = cursor.fetchall()
                    learning_paths = []
                    
                    for row in results:
                        path_data = {
                            'id': row[0],
                            'student_id': row[1],
                            'topic': row[2],
                            'current_stage': row[3],
                            'overall_progress': float(row[4]) if row[4] else 0.0,
                            'topics': row[5] if row[5] else [],
                            'created_at': row[6],
                            'is_active': row[7]
                        }
                        learning_paths.append(path_data)
                    
                    logger.info(f"Found {len(learning_paths)} learning paths for student {student_id}")
                    return learning_paths
                    
        except Exception as e:
            logger.error(f"Error getting learning paths: {str(e)}")
            return []
    
    def find_student_by_name_and_id(self, student_name: str, student_id: str) -> Optional[Dict[str, Any]]:
        """Find student by exact name and ID match."""
        try:
            # Debug: log the search
            logger.info(f"Searching for student: name='{student_name}', id='{student_id}'")
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT student_id, student_name, email, experience_level, created_at
                        FROM students 
                        WHERE LOWER(student_name) = LOWER(%s) AND student_id = %s
                    """, (student_name, student_id))
                    
                    result = cursor.fetchone()
                    logger.info(f"Search result: {result}")
                    
                    if result:
                        return {
                            'student_id': result[0],
                            'student_name': result[1],
                            'email': result[2],
                            'experience_level': result[3],
                            'created_at': result[4]
                        }
            return None
        except Exception as e:
            logger.error(f"Error finding student by name and ID: {str(e)}")
            return None
    
    def find_students_by_name(self, student_name: str) -> List[Dict[str, Any]]:
        """Find all students with the given name."""
        try:
            logger.info(f"Searching for students by name: '{student_name}'")
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT student_id, student_name, email, experience_level, created_at
                        FROM students 
                        WHERE LOWER(student_name) = LOWER(%s)
                        ORDER BY created_at DESC
                    """, (student_name,))
                    
                    results = cursor.fetchall()
                    logger.info(f"Found {len(results)} students with name '{student_name}'")
                    
                    return [
                        {
                            'student_id': row[0],
                            'student_name': row[1],
                            'email': row[2],
                            'experience_level': row[3],
                            'created_at': row[4]
                        }
                        for row in results
                    ]
        except Exception as e:
            logger.error(f"Error finding students by name: {str(e)}")
            return []
    
    def find_student_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Find student by ID only."""
        try:
            logger.info(f"Searching for student by ID: '{student_id}'")
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT student_id, student_name, email, experience_level, created_at
                        FROM students 
                        WHERE student_id = %s
                    """, (student_id,))
                    
                    result = cursor.fetchone()
                    logger.info(f"Search by ID result: {result}")
                    
                    if result:
                        return {
                            'student_id': result[0],
                            'student_name': result[1],
                            'email': result[2],
                            'experience_level': result[3],
                            'created_at': result[4]
                        }
            return None
        except Exception as e:
            logger.error(f"Error finding student by ID: {str(e)}")
            return None
    
    def create_or_update_student(self, student_data: Dict[str, Any]) -> bool:
        """Create or update student with all their data."""
        try:
            logger.info(f"Creating/updating student: {student_data.get('student_id', 'Unknown')}")
            
            # Save basic student info and preferences
            success = self.db.save_student(student_data)
            if success:
                logger.info(f"Student {student_data['student_id']} saved successfully")
            else:
                logger.error(f"Failed to save student {student_data['student_id']}")
            return success
        except Exception as e:
            logger.error(f"Error in create_or_update_student: {str(e)}")
            return False
    
    def save_generated_learning_path(self, student_id: str, learning_path: Dict[str, Any], topic: str) -> Optional[int]:
        """Save the generated learning path."""
        try:
            learning_path_data = {
                'topic': topic,
                'current_stage': learning_path.get('current_stage', ''),
                'progress': learning_path.get('progress', 0.0),
                'topics': learning_path.get('topics', [])
            }
            
            learning_path_id = self.db.save_learning_path(student_id, learning_path_data)
            if learning_path_id:
                logger.info(f"Learning path saved for student {student_id} with ID {learning_path_id}")
            return learning_path_id
        except Exception as e:
            logger.error(f"Error saving learning path: {str(e)}")
            return None
    

        
    def get_student_preferences(self, student_id: str) -> Dict[str, Any]:
        """Get student preferences organized by type."""
        try:
            logger.info(f"Getting preferences for student: {student_id}")
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT preference_type, preference_key, preference_value
                        FROM student_preferences 
                        WHERE student_id = %s
                        ORDER BY preference_type, preference_key
                    """, (student_id,))
                    
                    results = cursor.fetchall()
                    preferences = {}
                    
                    for row in results:
                        pref_type = row[0]
                        pref_key = row[1]
                        pref_value = row[2]
                        
                        if pref_type not in preferences:
                            preferences[pref_type] = {}
                        
                        preferences[pref_type][pref_key] = pref_value
                    
                    logger.info(f"Found {len(results)} preferences for student {student_id}")
                    return preferences
                    
        except Exception as e:
            logger.error(f"Error getting student preferences: {str(e)}")
            return {}
        
    def record_analyzed_study_session(self, student_id: str, session_data: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Record a study session with its analysis and update progress."""
        try:
            logger.info(f"=== RECORDING ANALYZED SESSION FOR {student_id} ===")
            logger.info(f"Session data: {session_data}")
            
            # Save the basic study session
            logger.info("Step 1: Saving basic study session...")
            session_success = self.record_study_session(student_id, session_data)
            logger.info(f"Basic session save result: {session_success}")
            
            # Save the analysis
            logger.info("Step 2: Saving analysis...")
            analysis_success = self.save_study_analysis(student_id, analysis)
            logger.info(f"Analysis save result: {analysis_success}")
            
            # Update progress based on analysis
            logger.info("Step 3: Updating progress from analysis...")
            progress_success = self.update_progress_from_analysis(student_id, analysis)
            logger.info(f"Progress update result: {progress_success}")
            
            overall_success = session_success and analysis_success and progress_success
            logger.info(f"=== OVERALL SUCCESS: {overall_success} ===")
            return overall_success
            
        except Exception as e:
            logger.error(f"Error recording analyzed study session: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def update_progress_from_analysis(self, student_id: str, analysis: Dict[str, Any]) -> bool:
        """Update student progress based on analysis insights."""
        try:
            progress_update = analysis.get('progress_update', {})
            
            # Get current progress
            current_progress = self.db.get_student_progress(student_id)
            logger.info(f"Current progress for {student_id}: {current_progress}")
            
            # Get topics from the session that was just completed
            session_data = analysis.get('session_data', {})
            studied_topic = session_data.get('topic', '').strip()
            logger.info(f"Studied topic: '{studied_topic}'")
            
            # Get learning path topics for comparison
            learning_paths = self.get_student_learning_paths(student_id)
            learning_path_topics = []
            
            if learning_paths:
                for path in learning_paths:
                    topics = path.get('topics', [])
                    if isinstance(topics, list):
                        for topic in topics:
                            if isinstance(topic, dict):
                                topic_name = topic.get('name', '')
                                if topic_name:
                                    learning_path_topics.append(topic_name)
                            elif isinstance(topic, str):
                                learning_path_topics.append(topic)
            
            logger.info(f"Learning path topics: {learning_path_topics}")
            
            # Update completed topics (avoid duplicates)
            completed_topics = set(current_progress.get('completed_topics', []))
            logger.info(f"Current completed topics: {completed_topics}")
            
            # Add explicitly marked completed topics
            new_completed = progress_update.get('topics_to_mark_completed', [])
            completed_topics.update(new_completed)
            logger.info(f"After adding explicitly marked: {completed_topics}")
            
            # Check if studied topic matches any learning path topics (fuzzy matching)
            matching_topic = None
            if studied_topic:
                # First, exact match
                for lp_topic in learning_path_topics:
                    if studied_topic.lower() == lp_topic.lower():
                        matching_topic = lp_topic
                        break
                
                # If no exact match, try partial matching
                if not matching_topic:
                    for lp_topic in learning_path_topics:
                        if (studied_topic.lower() in lp_topic.lower() or 
                            lp_topic.lower() in studied_topic.lower()):
                            matching_topic = lp_topic
                            break
                
                # If still no match, use the studied topic as-is
                if not matching_topic:
                    matching_topic = studied_topic
            
            logger.info(f"Matching topic found: '{matching_topic}'")
            
            # If effectiveness is good, mark the topic as completed
            effectiveness_score = analysis.get('learning_effectiveness', {}).get('effectiveness_score', 0)
            logger.info(f"Effectiveness score: {effectiveness_score}")
            
            if effectiveness_score >= 70 and matching_topic and matching_topic not in completed_topics:
                completed_topics.add(matching_topic)
                logger.info(f"Auto-marking topic '{matching_topic}' as completed due to good effectiveness ({effectiveness_score}%)")
            elif effectiveness_score < 70:
                logger.info(f"Not marking topic as completed - effectiveness too low: {effectiveness_score}%")
            elif not matching_topic:
                logger.info("No matching topic to mark as completed")
            elif matching_topic in completed_topics:
                logger.info(f"Topic '{matching_topic}' already marked as completed")
            
            # Add new concepts learned (avoid duplicates)
            concepts_learned = list(set(current_progress.get('concepts_learned', []) + progress_update.get('new_concepts_learned', [])))
            
            # Add the studied topic to concepts learned if not already there
            if studied_topic and studied_topic not in concepts_learned:
                concepts_learned.append(studied_topic)
            
            # Update areas needing review
            review_areas = progress_update.get('areas_needing_review', [])
            existing_review_areas = current_progress.get('areas_needing_review', [])
            all_review_areas = list(set(existing_review_areas + review_areas))
            
            logger.info(f"Final completed topics to save: {list(completed_topics)}")
            
            # Update in database
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Calculate average effectiveness
                    cursor.execute("""
                        SELECT AVG(effectiveness_score) 
                        FROM study_session_analyses 
                        WHERE student_id = %s
                    """, (student_id,))
                    avg_effectiveness_result = cursor.fetchone()
                    avg_effectiveness = float(avg_effectiveness_result[0]) if avg_effectiveness_result and avg_effectiveness_result[0] else effectiveness_score
                    
                    # Update or insert progress
                    cursor.execute("""
                        INSERT INTO student_progress 
                        (student_id, completed_topics, concepts_learned, areas_needing_review, 
                        last_effectiveness_score, last_study_date, total_study_sessions, average_effectiveness)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, 1, %s)
                        ON CONFLICT (student_id) 
                        DO UPDATE SET
                            completed_topics = %s,
                            concepts_learned = %s,
                            areas_needing_review = %s,
                            last_effectiveness_score = %s,
                            last_study_date = CURRENT_DATE,
                            total_study_sessions = student_progress.total_study_sessions + 1,
                            average_effectiveness = %s,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        student_id,
                        json.dumps(list(completed_topics)),
                        json.dumps(concepts_learned),
                        json.dumps(all_review_areas),
                        effectiveness_score,
                        avg_effectiveness,
                        json.dumps(list(completed_topics)),
                        json.dumps(concepts_learned),
                        json.dumps(all_review_areas),
                        effectiveness_score,
                        avg_effectiveness
                    ))
                    
                    conn.commit()
                    logger.info(f"Progress updated for student {student_id}: {len(completed_topics)} topics completed")
                    
                    # Verify the save worked
                    cursor.execute("""
                        SELECT completed_topics FROM student_progress WHERE student_id = %s
                    """, (student_id,))
                    verify_result = cursor.fetchone()
                    if verify_result:
                        saved_topics = json.loads(verify_result[0]) if verify_result[0] else []
                        logger.info(f"Verified saved completed topics: {saved_topics}")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error updating progress from analysis: {str(e)}")
            return False
    def get_student_historical_data(self, student_id: str) -> Dict[str, Any]:
        """Get comprehensive historical data for adaptive analysis - with fresh data."""
        try:
            logger.info(f"Getting fresh historical data for student: {student_id}")
            
            # Get basic student data
            student_data = self.db.get_student_data(student_id)
            if not student_data:
                logger.info(f"No student data found for {student_id}")
                return {}
            
            # Get FRESH progress data (this will use the updated get_student_progress method)
            progress_data = self.db.get_student_progress(student_id)
            
            # Get adaptive insights
            insights = self.db.get_adaptive_insights(student_id)
            
            # Get learning paths count for better context
            learning_paths = self.get_student_learning_paths(student_id)
            has_learning_paths = len(learning_paths) > 0
            
            return {
                'student_info': student_data,
                'progress': progress_data,
                'adaptive_insights': insights,
                'learning_paths_count': len(learning_paths),
                'has_history': bool(progress_data.get('total_topics', 0) > 0) or has_learning_paths
            }
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return {}

    def save_study_analysis(self, student_id: str, analysis: Dict[str, Any]) -> bool:
        """Save study session analysis to database."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO study_session_analyses 
                        (student_id, analysis_data, topic_alignment_score, effectiveness_score, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        student_id,
                        json.dumps(analysis),
                        analysis.get('topic_alignment', {}).get('alignment_score', 0),
                        analysis.get('learning_effectiveness', {}).get('effectiveness_score', 0)
                    ))
                    
                    conn.commit()
                    logger.info(f"Study analysis saved for student {student_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving study analysis: {str(e)}")
            return False

    def record_study_session(self, student_id: str, session_data: Dict[str, Any]) -> bool:
        """Record a study session."""
        try:
            session_data['student_id'] = student_id
            return self.db.save_study_session(session_data)
        except Exception as e:
            logger.error(f"Error recording study session: {str(e)}")
            return False
    
    def record_assessment(self, student_id: str, assessment_data: Dict[str, Any]) -> bool:
        """Record an assessment result."""
        try:
            assessment_data['student_id'] = student_id
            return self.db.save_assessment(assessment_data)
        except Exception as e:
            logger.error(f"Error recording assessment: {str(e)}")
            return False