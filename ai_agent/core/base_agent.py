from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseAgent(ABC):
    """
    Base class for all verification agents
    """
    def __init__(self):
        self.agent_name = self.__class__.__name__
    
    @abstractmethod
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent's verification logic
        
        Args:
            data: The input data for verification
            
        Returns:
            Dict: The verification results
        """
        pass
    
    def format_output(self, verification_result: Dict[str, Any], confidence_score: float, 
                     is_approved: bool, notes: str) -> Dict[str, Any]:
        """
        Format the agent's output in a standardized way
        
        Args:
            verification_result: The detailed verification results
            confidence_score: The confidence score for this verification
            is_approved: Whether this part of the verification is approved
            notes: Additional notes or explanations
            
        Returns:
            Dict: Formatted output
        """
        return {
            "agent": self.agent_name,
            "verification_result": verification_result,
            "confidence_score": confidence_score,
            "is_approved": is_approved,
            "notes": notes
        }
