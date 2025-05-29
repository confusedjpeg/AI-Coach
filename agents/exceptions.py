class CoachError(Exception):
    """Base exception for all coach-related errors."""
    pass

class AgentError(CoachError):
    """Base exception for agent-related errors."""
    pass

class PathAgentError(AgentError):
    """Exception raised for errors in the Path Agent."""
    pass

class TimeAgentError(AgentError):
    """Exception raised for errors in the Time Agent."""
    pass

class ProgressAgentError(AgentError):
    """Exception raised for errors in the Progress Agent."""
    pass

class AdaptiveAgentError(AgentError):
    """Exception raised for errors in the Adaptive Agent."""
    pass

class ValidationError(CoachError):
    """Exception raised for data validation errors."""
    pass

class StateError(CoachError):
    """Exception raised for state-related errors."""
    pass 