from typing import Dict, Any, List
from ..core.base_agent import BaseAgent
from ..core.llm_service import LLMService

class TreatmentVerificationAgent(BaseAgent):
    """
    Agent that verifies the treatment is appropriate for the diagnosis
    and covered by the insurance policy
    """
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify treatment based on:
        1. Is the treatment appropriate for the diagnosis?
        2. Is the treatment covered by the insurance policy?
        3. Is the treatment medically necessary?
        4. Does the treatment follow standard medical protocols?
        """
        # Extract relevant data
        patient_data = data.get("patient_data", {})
        insurance_policy_data = data.get("insurance_policy_data", {})
        visit_data = data.get("visit_data", {})
        medical_records = data.get("medical_records", [])
        diagnostic_verification = data.get("diagnostic_verification", {})
        
        # Create treatment verification prompt
        prompt = self._create_treatment_prompt(
            patient_data, 
            insurance_policy_data,
            visit_data,
            medical_records,
            diagnostic_verification
        )
        
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
    
    def _create_treatment_prompt(self, patient_data: Dict[str, Any],
                                 insurance_policy_data: Dict[str, Any],
                                 visit_data: Dict[str, Any],
                                 medical_records: List[Dict[str, Any]],
                                 diagnostic_verification: Dict[str, Any]) -> str:
        """Create the prompt for treatment verification"""
        prompt_parts = [
            "TREATMENT VERIFICATION TASK",
            "\nVerify if the treatment is appropriate for the diagnosis and covered by the insurance policy:",
            "\nPATIENT INFORMATION:",
        ]
        
        # Add patient information
        for key, value in patient_data.items():
            prompt_parts.append(f"- {key}: {value}")
        
        # Add diagnosis information
        prompt_parts.append("\nDIAGNOSIS INFORMATION:")
        diagnosis = visit_data.get("diagnosis", "Not provided")
        icd_code = visit_data.get("icd_code", "Not provided")
        prompt_parts.append(f"- Diagnosis: {diagnosis}")
        prompt_parts.append(f"- ICD Code: {icd_code}")
        
        # Add treatment information
        prompt_parts.append("\nTREATMENT INFORMATION:")
        treatment = visit_data.get("treatment_notes", "Not provided")
        prompt_parts.append(f"- Treatment: {treatment}")
        
        # Add diagnostic verification result
        prompt_parts.append("\nDIAGNOSTIC VERIFICATION RESULT:")
        prompt_parts.append(f"- Is Approved: {diagnostic_verification.get('is_approved', False)}")
        prompt_parts.append(f"- Notes: {diagnostic_verification.get('notes', 'Not provided')}")
        
        # Add insurance policy coverage information
        prompt_parts.append("\nINSURANCE POLICY COVERAGE INFORMATION:")
        for key, value in insurance_policy_data.items():
            if 'coverage' in key.lower() or 'exclusion' in key.lower():
                prompt_parts.append(f"- {key}: {value}")
        
        prompt_parts.append("\nVERIFICATION REQUIREMENTS:")
        prompt_parts.append("1. Verify if the treatment is appropriate for the diagnosed condition")
        prompt_parts.append("2. Check if the treatment is covered by the insurance policy")
        prompt_parts.append("3. Verify if the treatment is medically necessary")
        prompt_parts.append("4. Check if the treatment follows standard medical protocols")
        prompt_parts.append("5. Verify if there are any policy exclusions for this treatment")
        prompt_parts.append("6. Check if pre-authorization was required and obtained if necessary")
        prompt_parts.append("\nProvide a detailed verification result with specific reasons for approval or rejection.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert medical treatment verification agent with deep knowledge of medical treatments, protocols, and insurance coverage policies.
        Your task is to carefully analyze the patient's diagnosis and prescribed treatment to verify if the treatment is appropriate, medically necessary, and covered by the insurance policy.
        Be thorough, attentive to medical details, and provide clear medical reasoning for your decisions."""
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for the agent"""
        return {
            "type": "object",
            "properties": {
                "verification_result": {
                    "type": "object",
                    "properties": {
                        "treatment_appropriate_for_diagnosis": {"type": "boolean"},
                        "treatment_covered_by_policy": {"type": "boolean"},
                        "treatment_medically_necessary": {"type": "boolean"},
                        "treatment_follows_standard_protocols": {"type": "boolean"},
                        "no_policy_exclusions": {"type": "boolean"},
                        "pre_authorization_requirements_met": {"type": "boolean"}
                    }
                },
                "confidence_score": {
                    "type": "number",
                    "description": "A score between 0.0 and 1.0 indicating confidence in the verification"
                },
                "is_approved": {
                    "type": "boolean",
                    "description": "Whether the treatment verification is approved"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation of the verification result with medical reasoning"
                }
            },
            "required": ["verification_result", "confidence_score", "is_approved", "notes"]
        }
