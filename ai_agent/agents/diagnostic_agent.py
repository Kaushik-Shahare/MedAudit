from typing import Dict, Any, List
from ..core.base_agent import BaseAgent
from ..core.llm_service import LLMService

class DiagnosticVerificationAgent(BaseAgent):
    """
    Agent that verifies the medical diagnosis is consistent with medical records
    and appropriate for the insurance claim
    """
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify diagnosis based on:
        1. Is the diagnosis consistent with medical records?
        2. Are the diagnostic codes correct and appropriate?
        3. Is there sufficient medical evidence to support the diagnosis?
        """
        # Extract relevant data
        patient_data = data.get("patient_data", {})
        insurance_policy_data = data.get("insurance_policy_data", {})
        visit_data = data.get("visit_data", {})
        medical_records = data.get("medical_records", [])
        
        # Create diagnostic verification prompt
        prompt = self._create_diagnostic_prompt(
            patient_data, 
            insurance_policy_data,
            visit_data,
            medical_records
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
    
    def _create_diagnostic_prompt(self, patient_data: Dict[str, Any],
                                  insurance_policy_data: Dict[str, Any],
                                  visit_data: Dict[str, Any],
                                  medical_records: List[Dict[str, Any]]) -> str:
        """Create the prompt for diagnostic verification"""
        prompt_parts = [
            "DIAGNOSTIC VERIFICATION TASK",
            "\nVerify if the diagnosis is consistent with the medical records and appropriate for the insurance claim:",
            "\nPATIENT INFORMATION:",
        ]
        
        # Add patient information
        for key, value in patient_data.items():
            prompt_parts.append(f"- {key}: {value}")
        
        # Add diagnosis from visit data
        prompt_parts.append("\nDIAGNOSIS INFORMATION:")
        diagnosis = visit_data.get("diagnosis", "Not provided")
        icd_code = visit_data.get("icd_code", "Not provided")
        prompt_parts.append(f"- Diagnosis: {diagnosis}")
        prompt_parts.append(f"- ICD Code: {icd_code}")
        
        # Add relevant information from visit data
        prompt_parts.append("\nVISIT INFORMATION:")
        prompt_parts.append(f"- Visit Type: {visit_data.get('visit_type', 'Not provided')}")
        prompt_parts.append(f"- Chief Complaint: {visit_data.get('chief_complaint', 'Not provided')}")
        prompt_parts.append(f"- Reason for Visit: {visit_data.get('reason_for_visit', 'Not provided')}")
        
        # Add medical records summary
        prompt_parts.append("\nMEDICAL RECORDS:")
        for i, record in enumerate(medical_records):
            prompt_parts.append(f"Record {i+1}:")
            for key, value in record.items():
                prompt_parts.append(f"  - {key}: {value}")
        
        prompt_parts.append("\nVERIFICATION REQUIREMENTS:")
        prompt_parts.append("1. Verify if the diagnosis is consistent with the symptoms and medical evidence")
        prompt_parts.append("2. Check if the ICD code is correct and matches the diagnosis")
        prompt_parts.append("3. Verify if the diagnosis is supported by the medical records and test results")
        prompt_parts.append("4. Check if the diagnosis is appropriate for the visit type and chief complaint")
        prompt_parts.append("5. Verify if there are any inconsistencies or contradictions in the medical records")
        prompt_parts.append("\nProvide a detailed verification result with specific reasons for approval or rejection.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert medical diagnostic verification agent with deep knowledge of medicine, clinical guidelines, and diagnostic codes.
        Your task is to carefully analyze the patient's diagnosis, medical records, and visit information to verify if the diagnosis is appropriate and supported by evidence.
        Be thorough, attentive to medical details, and provide clear medical reasoning for your decisions."""
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for the agent"""
        return {
            "type": "object",
            "properties": {
                "verification_result": {
                    "type": "object",
                    "properties": {
                        "diagnosis_consistent_with_symptoms": {"type": "boolean"},
                        "icd_code_appropriate": {"type": "boolean"},
                        "sufficient_medical_evidence": {"type": "boolean"},
                        "diagnosis_matches_visit_reason": {"type": "boolean"},
                        "no_contradictions_in_records": {"type": "boolean"}
                    }
                },
                "confidence_score": {
                    "type": "number",
                    "description": "A score between 0.0 and 1.0 indicating confidence in the verification"
                },
                "is_approved": {
                    "type": "boolean",
                    "description": "Whether the diagnostic verification is approved"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation of the verification result with medical reasoning"
                }
            },
            "required": ["verification_result", "confidence_score", "is_approved", "notes"]
        }
