from typing import Dict, Any
from ..core.base_agent import BaseAgent
from ..core.llm_service import LLMService

class EligibilityVerificationAgent(BaseAgent):
    """
    Agent that verifies patient eligibility for insurance claims
    """
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify patient eligibility based on:
        1. Is the patient's insurance policy active?
        2. Is the treatment covered under their policy?
        3. Are there any waiting periods or pre-existing condition exclusions?
        """
        # Extract relevant data
        patient_data = data.get("patient_data", {})
        insurance_policy_data = data.get("insurance_policy_data", {})
        visit_data = data.get("visit_data", {})
        
        # Create eligibility verification prompt
        prompt = self._create_eligibility_prompt(patient_data, insurance_policy_data, visit_data)
        
        # Get verification result from LLM
        result = self.llm_service.get_structured_output(
            system_prompt=self._get_system_prompt(),
            user_prompt=prompt,
            output_schema=self._get_output_schema(),
            use_flash=True
        )
        
        # Format and return the result
        verification_result = result.get("verification_result", {})
        confidence_score = result.get("confidence_score", 0.0)
        is_approved = result.get("is_approved", False)
        notes = result.get("notes", "")
        
        return self.format_output(
            verification_result=verification_result,
            confidence_score=confidence_score,
            is_approved=is_approved,
            notes=notes
        )
    
    def _create_eligibility_prompt(self, patient_data: Dict[str, Any],
                                  insurance_policy_data: Dict[str, Any],
                                  visit_data: Dict[str, Any]) -> str:
        """Create the prompt for eligibility verification"""
        prompt_parts = [
            "ELIGIBILITY VERIFICATION TASK",
            "\nVerify if the patient is eligible for insurance coverage based on the following information:",
            "\nPATIENT INFORMATION:",
        ]
        
        # Add patient information
        for key, value in patient_data.items():
            prompt_parts.append(f"- {key}: {value}")
        
        # Add insurance policy information
        prompt_parts.append("\nINSURANCE POLICY INFORMATION:")
        for key, value in insurance_policy_data.items():
            prompt_parts.append(f"- {key}: {value}")
        
        # Add visit information
        prompt_parts.append("\nVISIT INFORMATION:")
        for key, value in visit_data.items():
            prompt_parts.append(f"- {key}: {value}")
        
        prompt_parts.append("\nVERIFICATION REQUIREMENTS:")
        prompt_parts.append("1. Verify if the insurance policy is active at the time of the visit")
        prompt_parts.append("2. Check if the visit type/treatment is covered under the policy")
        prompt_parts.append("3. Check if any waiting periods or pre-existing condition exclusions apply")
        prompt_parts.append("4. Verify if the patient has met any required deductibles")
        prompt_parts.append("5. Check if pre-authorization was required and obtained if necessary")
        prompt_parts.append("\nProvide a detailed verification result with specific reasons for approval or rejection.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert medical insurance eligibility verification agent with deep knowledge of healthcare insurance policies.
        Your task is to carefully analyze patient and insurance policy information to determine if the patient is eligible for coverage.
        Be thorough, attentive to details, and provide clear reasoning for your decisions."""
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for the agent"""
        return {
            "type": "object",
            "properties": {
                "verification_result": {
                    "type": "object",
                    "properties": {
                        "policy_active": {"type": "boolean"},
                        "treatment_covered": {"type": "boolean"},
                        "waiting_period_satisfied": {"type": "boolean"},
                        "preexisting_conditions": {"type": "boolean"},
                        "deductibles_met": {"type": "boolean"},
                        "preauth_requirements_met": {"type": "boolean"},
                    }
                },
                "confidence_score": {
                    "type": "number",
                    "description": "A score between 0.0 and 1.0 indicating confidence in the verification"
                },
                "is_approved": {
                    "type": "boolean",
                    "description": "Whether the eligibility verification is approved"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation of the verification result"
                }
            },
            "required": ["verification_result", "confidence_score", "is_approved", "notes"]
        }
