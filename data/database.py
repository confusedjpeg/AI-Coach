import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import json
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database operations for the learning coach."""
    
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'learning_coach'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password'),
            'port': os.getenv('DB_PORT', '5432')
        }
        
    def get_connection(self):
        """Get database connection."""
        try:
            conn = psycopg2.connect(**self.connection_params)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
    
    def create_tables(self):
        """Create all necessary tables."""
        
        create_tables_sql = """
        -- Students table
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(100) PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            experience_level VARCHAR(50),
            current_topic VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Student preferences table
        CREATE TABLE IF NOT EXISTS student_preferences (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            preference_type VARCHAR(50),
            preference_key VARCHAR(50),
            preference_value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Learning paths table
        CREATE TABLE IF NOT EXISTS learning_paths (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            topic VARCHAR(255) NOT NULL,
            current_stage VARCHAR(255),
            overall_progress DECIMAL(5,2) DEFAULT 0.00,
            topics JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
        
        -- Topics table
        CREATE TABLE IF NOT EXISTS topics (
            id SERIAL PRIMARY KEY,
            learning_path_id INTEGER REFERENCES learning_paths(id) ON DELETE CASCADE,
            topic_name VARCHAR(255) NOT NULL,
            description TEXT,
            estimated_time VARCHAR(50),
            difficulty_level VARCHAR(50),
            order_index INTEGER,
            status VARCHAR(50) DEFAULT 'not_started', -- not_started, in_progress, completed
            completion_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Study sessions table
        CREATE TABLE IF NOT EXISTS study_sessions (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            session_date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            duration_minutes INTEGER,
            activities JSONB,
            notes TEXT,
            mood_rating INTEGER CHECK (mood_rating >= 1 AND mood_rating <= 5),
            productivity_rating INTEGER CHECK (productivity_rating >= 1 AND productivity_rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Assessments table
        CREATE TABLE IF NOT EXISTS assessments (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            assessment_type VARCHAR(50), -- quiz, project, exercise, test
            assessment_name VARCHAR(255),
            max_score DECIMAL(5,2),
            achieved_score DECIMAL(5,2),
            percentage DECIMAL(5,2),
            time_taken_minutes INTEGER,
            attempts INTEGER DEFAULT 1,
            feedback TEXT,
            assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Progress tracking table
        CREATE TABLE IF NOT EXISTS progress_tracking (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
            progress_percentage DECIMAL(5,2),
            concepts_mastered JSONB,
            concepts_struggling JSONB,
            time_spent_minutes INTEGER,
            last_activity_date TIMESTAMP,
            streak_days INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Adaptive insights table
        CREATE TABLE IF NOT EXISTS adaptive_insights (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            insight_type VARCHAR(50), -- recommendation, difficulty_adjustment, focus_area
            insight_data JSONB,
            effectiveness_score DECIMAL(3,2), -- How effective was this insight (0-1)
            implemented BOOLEAN DEFAULT FALSE,
            implementation_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Learning analytics table
        CREATE TABLE IF NOT EXISTS learning_analytics (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            metric_name VARCHAR(100),
            metric_value DECIMAL(10,2),
            metric_data JSONB,
            calculation_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Schedules table
        CREATE TABLE IF NOT EXISTS schedules (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            schedule_data JSONB,
            week_start_date DATE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Study session analyses table
        CREATE TABLE IF NOT EXISTS study_session_analyses (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) REFERENCES students(student_id) ON DELETE CASCADE,
            analysis_data JSONB NOT NULL,
            topic_alignment_score INTEGER DEFAULT 0,
            effectiveness_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    
        -- Enhanced student progress table
        CREATE TABLE IF NOT EXISTS student_progress (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(100) UNIQUE REFERENCES students(student_id) ON DELETE CASCADE,
            completed_topics JSONB DEFAULT '[]',
            concepts_learned JSONB DEFAULT '[]',
            areas_needing_review JSONB DEFAULT '[]',
            last_effectiveness_score INTEGER DEFAULT 0,
            last_study_date DATE,
            total_study_sessions INTEGER DEFAULT 0,
            average_effectiveness DECIMAL(5,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
        CREATE INDEX IF NOT EXISTS idx_learning_paths_student ON learning_paths(student_id);
        CREATE INDEX IF NOT EXISTS idx_topics_learning_path ON topics(learning_path_id);
        CREATE INDEX IF NOT EXISTS idx_study_sessions_student ON study_sessions(student_id);
        CREATE INDEX IF NOT EXISTS idx_study_sessions_date ON study_sessions(session_date);
        CREATE INDEX IF NOT EXISTS idx_assessments_student ON assessments(student_id);
        CREATE INDEX IF NOT EXISTS idx_progress_student ON progress_tracking(student_id);
        CREATE INDEX IF NOT EXISTS idx_insights_student ON adaptive_insights(student_id);
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_tables_sql)
                    conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def save_student(self, student_data: Dict[str, Any]) -> bool:
        """Save student data to database with proper conflict handling."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First, check if student exists
                    cursor.execute(
                        "SELECT student_id FROM students WHERE student_id = %s",
                        (student_data['student_id'],)
                    )
                    existing_student = cursor.fetchone()
                    
                    if existing_student:
                        # Update existing student
                        cursor.execute("""
                            UPDATE students 
                            SET student_name = %s, 
                                email = %s, 
                                experience_level = %s, 
                                current_topic = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE student_id = %s
                        """, (
                            student_data['student_name'],
                            student_data.get('email', ''),
                            student_data['experience_level'],
                            student_data['current_topic'],
                            student_data['student_id']
                        ))
                        logger.info(f"Updated existing student: {student_data['student_id']}")
                    else:
                        # Insert new student
                        cursor.execute("""
                            INSERT INTO students (student_id, student_name, email, experience_level, current_topic)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            student_data['student_id'],
                            student_data['student_name'],
                            student_data.get('email', ''),
                            student_data['experience_level'],
                            student_data['current_topic']
                        ))
                        logger.info(f"Inserted new student: {student_data['student_id']}")
                    
                    # Save preferences (delete existing first, then insert new)
                    cursor.execute(
                        "DELETE FROM student_preferences WHERE student_id = %s",
                        (student_data['student_id'],)
                    )
                    
                    # Insert learning preferences
                    if 'learning_preferences' in student_data:
                        prefs = student_data['learning_preferences']
                        cursor.execute("""
                            INSERT INTO student_preferences (student_id, preference_type, preference_key, preference_value)
                            VALUES (%s, 'learning', 'learning_style', %s)
                        """, (student_data['student_id'], str(prefs.get('learning_style', []))))
                        
                        cursor.execute("""
                            INSERT INTO student_preferences (student_id, preference_type, preference_key, preference_value)
                            VALUES (%s, 'learning', 'difficulty_preference', %s)
                        """, (student_data['student_id'], prefs.get('difficulty_preference', '')))
                    
                    # Insert schedule preferences
                    if 'schedule_preferences' in student_data:
                        sched = student_data['schedule_preferences']
                        cursor.execute("""
                            INSERT INTO student_preferences (student_id, preference_type, preference_key, preference_value)
                            VALUES (%s, 'schedule', 'available_days', %s)
                        """, (student_data['student_id'], str(sched.get('available_days', []))))
                        
                        cursor.execute("""
                            INSERT INTO student_preferences (student_id, preference_type, preference_key, preference_value)
                            VALUES (%s, 'schedule', 'weekly_hours', %s)
                        """, (student_data['student_id'], str(sched.get('weekly_hours', 0))))
                    
                    # Insert success criteria
                    if 'success_criteria' in student_data:
                        criteria = student_data['success_criteria']
                        cursor.execute("""
                            INSERT INTO student_preferences (student_id, preference_type, preference_key, preference_value)
                            VALUES (%s, 'success', 'success_threshold', %s)
                        """, (student_data['student_id'], str(criteria.get('success_threshold', 75))))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Error saving student: {str(e)}")
            return False
    
    def save_learning_path(self, student_id: str, learning_path_data: Dict[str, Any]) -> int:
        """Save learning path and return the learning_path_id."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Deactivate previous learning paths
                    cursor.execute("""
                        UPDATE learning_paths SET is_active = FALSE 
                        WHERE student_id = %s AND is_active = TRUE
                    """, (student_id,))
                    
                    # Insert new learning path
                    cursor.execute("""
                        INSERT INTO learning_paths 
                        (student_id, topic, current_stage, overall_progress, topics)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                    """, (
                        student_id,
                        learning_path_data.get('topic', ''),
                        learning_path_data.get('current_stage', ''),
                        learning_path_data.get('progress', 0.0) * 100,  # Convert to percentage
                        json.dumps(learning_path_data.get('topics', []))
                    ))
                    
                    learning_path_id = cursor.fetchone()[0]
                    
                    # Insert individual topics
                    topics = learning_path_data.get('topics', [])
                    for i, topic in enumerate(topics):
                        cursor.execute("""
                            INSERT INTO topics 
                            (learning_path_id, topic_name, description, estimated_time, order_index)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            learning_path_id,
                            topic.get('name', ''),
                            topic.get('description', ''),
                            topic.get('estimated_time', ''),
                            i + 1
                        ))
                    
                    conn.commit()
                    return learning_path_id
        except Exception as e:
            logger.error(f"Error saving learning path: {str(e)}")
            return None
    
    def get_student_data(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive student data."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get student basic info
                    cursor.execute("""
                        SELECT s.*, sp.preference_type, sp.preference_key, sp.preference_value
                        FROM students s
                        LEFT JOIN student_preferences sp ON s.student_id = sp.student_id
                        WHERE s.student_id = %s
                    """, (student_id,))
                    
                    student = cursor.fetchone()
                    if not student:
                        return None
                    
                    return dict(student)
        except Exception as e:
            logger.error(f"Error getting student data: {str(e)}")
            return None
    
    def get_student_progress(self, student_id: str) -> Dict[str, Any]:
        """Get comprehensive student progress data with correct topic counts."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get progress from student_progress table
                    cursor.execute("""
                        SELECT completed_topics, concepts_learned, areas_needing_review,
                            last_effectiveness_score, last_study_date, total_study_sessions,
                            average_effectiveness
                        FROM student_progress 
                        WHERE student_id = %s
                    """, (student_id,))
                    
                    progress_result = cursor.fetchone()
                    
                    # Get TOTAL topics from learning paths (this is the real total)
                    cursor.execute("""
                        SELECT topics
                        FROM learning_paths 
                        WHERE student_id = %s AND is_active = true
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (student_id,))
                    
                    learning_path_result = cursor.fetchone()
                    
                    # Get study sessions count and stats
                    cursor.execute("""
                        SELECT COUNT(*) as session_count,
                            AVG(mood_rating) as avg_mood,
                            AVG(productivity_rating) as avg_productivity,
                            SUM(duration_minutes) as total_minutes
                        FROM study_sessions 
                        WHERE student_id = %s
                    """, (student_id,))
                    
                    session_stats = cursor.fetchone()
                    
                    # Get assessment averages
                    cursor.execute("""
                        SELECT AVG(percentage) as avg_score,
                            COUNT(*) as assessment_count
                        FROM assessments 
                        WHERE student_id = %s
                    """, (student_id,))
                    
                    assessment_stats = cursor.fetchone()
                    
                    # Parse completed topics from progress table
                    if progress_result:
                        completed_topics = progress_result[0] if progress_result[0] else []
                        concepts_learned = progress_result[1] if progress_result[1] else []
                        areas_needing_review = progress_result[2] if progress_result[2] else []
                        
                        # Parse JSON if they're strings
                        if isinstance(completed_topics, str):
                            import json
                            completed_topics = json.loads(completed_topics)
                        if isinstance(concepts_learned, str):
                            import json
                            concepts_learned = json.loads(concepts_learned)
                        if isinstance(areas_needing_review, str):
                            import json
                            areas_needing_review = json.loads(areas_needing_review)
                    else:
                        completed_topics = []
                        concepts_learned = []
                        areas_needing_review = []
                    
                    # Get REAL total topics from learning path
                    total_topics_from_path = 0
                    if learning_path_result and learning_path_result[0]:
                        import json
                        topics_data = learning_path_result[0]
                        if isinstance(topics_data, str):
                            topics_data = json.loads(topics_data)
                        
                        # Count topics from learning path
                        if isinstance(topics_data, list):
                            total_topics_from_path = len(topics_data)
                        elif isinstance(topics_data, dict) and 'topics' in topics_data:
                            total_topics_from_path = len(topics_data['topics'])
                    
                    # Use the learning path total as the real total
                    total_topics = max(total_topics_from_path, len(completed_topics))
                    completed_count = len(completed_topics)
                    
                    # Progress percentage based on learning path topics
                    progress_percentage = (completed_count / total_topics * 100) if total_topics > 0 else 0
                    
                    return {
                        'completed_topics': completed_topics,
                        'concepts_learned': concepts_learned,
                        'areas_needing_review': areas_needing_review,
                        'total_topics': total_topics,
                        'completed_count': completed_count,
                        'progress_percentage': progress_percentage,
                        'last_effectiveness_score': progress_result[3] if progress_result else 0,
                        'last_study_date': progress_result[4] if progress_result else None,
                        'total_study_sessions': progress_result[5] if progress_result else 0,
                        'average_effectiveness': float(progress_result[6]) if progress_result and progress_result[6] else 0,
                        'average_score': float(assessment_stats[0]) if assessment_stats and assessment_stats[0] else 0,
                        'assessment_count': assessment_stats[1] if assessment_stats else 0,
                        'session_count': session_stats[0] if session_stats else 0,
                        'average_mood': float(session_stats[1]) if session_stats and session_stats[1] else 0,
                        'average_productivity': float(session_stats[2]) if session_stats and session_stats[2] else 0,
                        'total_study_time_hours': float(session_stats[3] / 60) if session_stats and session_stats[3] else 0,
                        'learning_path_topics': total_topics_from_path
                    }
                    
        except Exception as e:
            logger.error(f"Error getting student progress: {str(e)}")
            return {
                'completed_topics': [],
                'concepts_learned': [],
                'areas_needing_review': [],
                'total_topics': 0,
                'completed_count': 0,
                'progress_percentage': 0,
                'last_effectiveness_score': 0,
                'last_study_date': None,
                'total_study_sessions': 0,
                'average_effectiveness': 0,
                'average_score': 0,
                'assessment_count': 0,
                'session_count': 0,
                'average_mood': 0,
                'average_productivity': 0,
                'total_study_time_hours': 0,
                'learning_path_topics': 0
            }
    
    def save_study_session(self, session_data: Dict[str, Any]) -> bool:
        """Save a study session."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO study_sessions 
                        (student_id, topic_id, session_date, start_time, end_time, 
                         duration_minutes, activities, notes, mood_rating, productivity_rating)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session_data['student_id'],
                        session_data.get('topic_id'),
                        session_data['session_date'],
                        session_data.get('start_time'),
                        session_data.get('end_time'),
                        session_data['duration_minutes'],
                        json.dumps(session_data.get('activities', [])),
                        session_data.get('notes', ''),
                        session_data.get('mood_rating'),
                        session_data.get('productivity_rating')
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving study session: {str(e)}")
            return False
    
    def save_assessment(self, assessment_data: Dict[str, Any]) -> bool:
        """Save assessment results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO assessments 
                        (student_id, topic_id, assessment_type, assessment_name, 
                         max_score, achieved_score, percentage, time_taken_minutes, attempts, feedback)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        assessment_data['student_id'],
                        assessment_data.get('topic_id'),
                        assessment_data['assessment_type'],
                        assessment_data['assessment_name'],
                        assessment_data['max_score'],
                        assessment_data['achieved_score'],
                        assessment_data['percentage'],
                        assessment_data.get('time_taken_minutes'),
                        assessment_data.get('attempts', 1),
                        assessment_data.get('feedback', '')
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving assessment: {str(e)}")
            return False
    
    def get_adaptive_insights(self, student_id: str) -> List[Dict[str, Any]]:
        """Get adaptive insights for the student."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT insight_type, insight_data, effectiveness_score, 
                               implemented, created_at
                        FROM adaptive_insights
                        WHERE student_id = %s
                        ORDER BY created_at DESC
                        LIMIT 20
                    """, (student_id,))
                    
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting adaptive insights: {str(e)}")
            return []
    
    def save_adaptive_insight(self, student_id: str, insight_data: Dict[str, Any]) -> bool:
        """Save adaptive insight."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO adaptive_insights 
                        (student_id, insight_type, insight_data)
                        VALUES (%s, %s, %s)
                    """, (
                        student_id,
                        insight_data['type'],
                        json.dumps(insight_data)
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving adaptive insight: {str(e)}")
            return False