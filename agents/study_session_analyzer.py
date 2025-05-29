from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StudySessionAnalyzer:
    """Analyzes study sessions against learning paths and schedules using LLM."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000
        )
    
    def analyze_study_session(
    self, 
    session_data: Dict[str, Any], 
    learning_paths: List[Dict[str, Any]], 
    current_progress: Dict[str, Any],
    schedule_preferences: Dict[str, Any]
) -> Dict[str, Any]:
        """
        Analyze a study session comprehensively.
        """
        try:
            # Convert datetime objects to strings for JSON serialization
            session_data_clean = self._clean_datetime_objects(session_data)
            learning_paths_clean = self._clean_datetime_objects(learning_paths)
            current_progress_clean = self._clean_datetime_objects(current_progress)
            
            # Prepare context for LLM
            context = self._prepare_analysis_context(
                session_data_clean, learning_paths_clean, current_progress_clean, schedule_preferences
            )
            
            # Create analysis prompt
            system_prompt = self._create_system_prompt()
            human_prompt = self._create_analysis_prompt(context)
            
            # Get LLM analysis
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse the response
            analysis_result = self._parse_llm_response(response.content)
            
            # Add metadata and PRESERVE THE ORIGINAL SESSION DATA
            analysis_result['analysis_timestamp'] = datetime.now().isoformat()
            analysis_result['session_data'] = session_data_clean  # This should have the topic
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing study session: {str(e)}")
            return self._create_fallback_analysis(session_data)
    
    def _prepare_analysis_context(
        self, 
        session_data: Dict[str, Any], 
        learning_paths: List[Dict[str, Any]], 
        current_progress: Dict[str, Any],
        schedule_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare context data for analysis."""
        
        # Find relevant learning path
        relevant_path = None
        session_topic = session_data.get('topic', '').lower()
        
        for path in learning_paths:
            path_topic = path.get('topic', '').lower()
            if session_topic in path_topic or path_topic in session_topic:
                relevant_path = path
                break
        
        if not relevant_path and learning_paths:
            relevant_path = learning_paths[0]  # Use most recent if no match
        
        # MAKE SURE THE SESSION DATE IS PROPERLY CONVERTED
        session_date = session_data.get('session_date')
        if hasattr(session_date, 'isoformat'):
            session_date_str = session_date.isoformat()
        else:
            session_date_str = str(session_date)
        
        return {
            'session': {
                'topic': session_data.get('topic', ''),  # Keep the original topic
                'duration_minutes': session_data.get('duration_minutes', 0),
                'mood_rating': session_data.get('mood_rating', 3),
                'productivity_rating': session_data.get('productivity_rating', 3),
                'notes': session_data.get('notes', ''),
                'session_date': session_date_str
            },
            'learning_path': relevant_path,
            'current_progress': current_progress,
            'schedule_preferences': schedule_preferences
        }

    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        return """You are an AI Learning Coach analyzing a student's study session. 

Your task is to evaluate the study session against:
1. The student's learning path and topics
2. Their current progress and performance
3. Their schedule preferences and study habits
4. The effectiveness and alignment of the session

Provide a comprehensive analysis in the following JSON format:

{
    "topic_alignment": {
        "matches_learning_path": true/false,
        "relevant_topics_covered": ["topic1", "topic2"],
        "progress_on_current_stage": "description",
        "alignment_score": 0-100
    },
    "schedule_analysis": {
        "follows_preferred_schedule": true/false,
        "optimal_time_slot": true/false,
        "duration_appropriateness": "too_short/optimal/too_long",
        "consistency_with_habits": "description"
    },
    "learning_effectiveness": {
        "productivity_assessment": "description based on ratings",
        "mood_impact": "description based on mood rating",
        "comprehension_indicators": ["indicator1", "indicator2"],
        "effectiveness_score": 0-100
    },
    "progress_update": {
        "topics_to_mark_completed": ["topic1", "topic2"],
        "new_concepts_learned": ["concept1", "concept2"],
        "skill_improvements": ["skill1", "skill2"],
        "areas_needing_review": ["area1", "area2"]
    },
    "recommendations": {
        "immediate_next_steps": ["step1", "step2"],
        "schedule_adjustments": ["adjustment1", "adjustment2"],
        "study_method_suggestions": ["suggestion1", "suggestion2"],
        "focus_areas_next_session": ["area1", "area2"]
    },
    "insights": {
        "patterns_observed": ["pattern1", "pattern2"],
        "strengths_demonstrated": ["strength1", "strength2"],
        "challenges_identified": ["challenge1", "challenge2"],
        "motivation_indicators": ["indicator1", "indicator2"]
    }
}

Be specific, actionable, and encouraging in your analysis."""

    def _create_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Create the analysis prompt with context."""
        return f"""
Please analyze this study session:

**Study Session Details:**
- Topic studied: {context['session']['topic']}
- Duration: {context['session']['duration_minutes']} minutes
- Mood rating: {context['session']['mood_rating']}/5
- Productivity rating: {context['session']['productivity_rating']}/5
- Date: {context['session']['session_date']}
- Notes: {context['session']['notes']}

**Current Learning Path:**
{json.dumps(context['learning_path'], indent=2) if context['learning_path'] else 'No active learning path'}

**Current Progress:**
{json.dumps(context['current_progress'], indent=2)}

**Schedule Preferences:**
{json.dumps(context['schedule_preferences'], indent=2)}

Provide a comprehensive analysis following the JSON format specified in the system prompt.
"""

    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        try:
            # Try to extract JSON from the response
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._create_simple_analysis(response_content)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return self._create_simple_analysis(response_content)
    
    def _create_simple_analysis(self, response_content: str) -> Dict[str, Any]:
        """Create a simple analysis structure from free text."""
        return {
            "topic_alignment": {
                "matches_learning_path": True,
                "relevant_topics_covered": [],
                "progress_on_current_stage": "Session completed",
                "alignment_score": 75
            },
            "schedule_analysis": {
                "follows_preferred_schedule": True,
                "optimal_time_slot": True,
                "duration_appropriateness": "optimal",
                "consistency_with_habits": "Good consistency"
            },
            "learning_effectiveness": {
                "productivity_assessment": "Good session",
                "mood_impact": "Positive learning experience",
                "comprehension_indicators": ["Completed session"],
                "effectiveness_score": 75
            },
            "progress_update": {
                "topics_to_mark_completed": [],
                "new_concepts_learned": [],
                "skill_improvements": [],
                "areas_needing_review": []
            },
            "recommendations": {
                "immediate_next_steps": ["Continue with next topic"],
                "schedule_adjustments": [],
                "study_method_suggestions": [],
                "focus_areas_next_session": []
            },
            "insights": {
                "patterns_observed": [],
                "strengths_demonstrated": ["Consistent study habit"],
                "challenges_identified": [],
                "motivation_indicators": ["Completed study session"]
            },
            "raw_analysis": response_content
        }
    
    def _create_fallback_analysis(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback analysis when LLM fails."""
        return {
            "topic_alignment": {
                "matches_learning_path": True,
                "relevant_topics_covered": [session_data.get('topic', 'Unknown')],
                "progress_on_current_stage": "Session logged successfully",
                "alignment_score": 70
            },
            "schedule_analysis": {
                "follows_preferred_schedule": True,
                "optimal_time_slot": True,
                "duration_appropriateness": "optimal",
                "consistency_with_habits": "Session completed"
            },
            "learning_effectiveness": {
                "productivity_assessment": f"Productivity rated {session_data.get('productivity_rating', 3)}/5",
                "mood_impact": f"Mood rated {session_data.get('mood_rating', 3)}/5",
                "comprehension_indicators": ["Session completed"],
                "effectiveness_score": (session_data.get('productivity_rating', 3) * 20)
            },
            "progress_update": {
                "topics_to_mark_completed": [],
                "new_concepts_learned": [session_data.get('topic', 'Unknown')],
                "skill_improvements": [],
                "areas_needing_review": []
            },
            "recommendations": {
                "immediate_next_steps": ["Continue learning"],
                "schedule_adjustments": [],
                "study_method_suggestions": [],
                "focus_areas_next_session": [session_data.get('topic', 'Unknown')]
            },
            "insights": {
                "patterns_observed": ["Regular study session"],
                "strengths_demonstrated": ["Consistent learning"],
                "challenges_identified": [],
                "motivation_indicators": ["Active learning"]
            },
            "error": "Fallback analysis used due to LLM error"
        }
    def _clean_datetime_objects(self, data: Any) -> Any:
        """Convert datetime objects to strings for JSON serialization."""
        if isinstance(data, dict):
            return {key: self._clean_datetime_objects(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._clean_datetime_objects(item) for item in data]
        elif hasattr(data, 'isoformat'):  # datetime objects
            return data.isoformat()
        elif hasattr(data, '__dict__'):  # other objects
            return str(data)
        else:
            return data
