from typing import Dict, Any, List
from ..core.base_agent import BaseAgent
from ..core.llm_service import LLMService

class FraudDetectionAgent(BaseAgent):
    """
    Agent that checks for potential fraud indicators in the insurance claim
    """
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for fraud based on:
        1. Are there inconsistencies between different parts of the claim?
        2. Are there suspicious patterns in treatment or billing?
        3. Is there evidence of service upcoding or unbundling?
        4. Are there indicators of identity fraud or impersonation?
        """
        # Extract relevant data
        patient_data = data.get("patient_data", {})
        insurance_policy_data = data.get("insurance_policy_data", {})
        visit_data = data.get("visit_data", {})
        medical_records = data.get("medical_records", [])
        diagnostic_verification = data.get("diagnostic_verification", {})
        treatment_verification = data.get("treatment_verification", {})
        billing_verification = data.get("billing_verification", {})
        
        # Create fraud detection prompt
        prompt = self._create_fraud_detection_prompt(
            patient_data, 
            insurance_policy_data,
            visit_data,
            medical_records,
            diagnostic_verification,
            treatment_verification,
            billing_verification
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
    
    def _create_fraud_detection_prompt(self, patient_data: Dict[str, Any],
                                       insurance_policy_data: Dict[str, Any],
                                       visit_data: Dict[str, Any],
                                       medical_records: List[Dict[str, Any]],
                                       diagnostic_verification: Dict[str, Any],
                                       treatment_verification: Dict[str, Any],
                                       billing_verification: Dict[str, Any]) -> str:
        """Create the prompt for fraud detection"""
        prompt_parts = [
            "FRAUD DETECTION TASK",
            "\nCheck for potential fraud indicators in the insurance claim:",
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
        
        # Add billing information
        prompt_parts.append("\nBILLING INFORMATION:")
        prompt_parts.append(f"- Total Amount: {visit_data.get('total_amount', 'Not provided')}")
        
        # Add charges if available
        charges = visit_data.get("charges", [])
        if charges:
            prompt_parts.append("\nITEMIZED CHARGES:")
            for i, charge in enumerate(charges):
                prompt_parts.append(f"Charge {i+1}:")
                for key, value in charge.items():
                    prompt_parts.append(f"  - {key}: {value}")
        
        # Add previous verification results
        prompt_parts.append("\nPREVIOUS VERIFICATION RESULTS:")
        
        prompt_parts.append("Diagnostic Verification:")
        prompt_parts.append(f"- Is Approved: {diagnostic_verification.get('is_approved', False)}")
        prompt_parts.append(f"- Confidence Score: {diagnostic_verification.get('confidence_score', 'Not provided')}")
        
        prompt_parts.append("Treatment Verification:")
        prompt_parts.append(f"- Is Approved: {treatment_verification.get('is_approved', False)}")
        prompt_parts.append(f"- Confidence Score: {treatment_verification.get('confidence_score', 'Not provided')}")
        
        prompt_parts.append("Billing Verification:")
        prompt_parts.append(f"- Is Approved: {billing_verification.get('is_approved', False)}")
        prompt_parts.append(f"- Confidence Score: {billing_verification.get('confidence_score', 'Not provided')}")
        
        prompt_parts.append("\nFRAUD DETECTION REQUIREMENTS:")
        prompt_parts.append("1. Check for inconsistencies between different parts of the claim")
        prompt_parts.append("2. Look for suspicious patterns in treatment or billing")
        prompt_parts.append("3. Check for evidence of service upcoding or unbundling")
        prompt_parts.append("4. Look for indicators of identity fraud or impersonation")
        prompt_parts.append("5. Check for irregular treatment patterns or excessive services")
        prompt_parts.append("6. Look for unusual timing patterns in the claim submission")
        prompt_parts.append("\nProvide a detailed fraud detection result with specific findings.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert medical insurance fraud detection specialist with deep knowledge of fraud schemes and patterns.
        Your task is to carefully analyze the insurance claim to detect potential fraud indicators.
        Be thorough, attentive to inconsistencies and patterns, and provide clear reasoning for your findings.
        Note that you should look for potential fraud but avoid making absolute accusations without strong evidence."""
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for the agent"""
        return {
            "type": "object",
            "properties": {
                "verification_result": {
                    "type": "object",
                    "properties": {
                        "no_inconsistencies_detected": {"type": "boolean"},
                        "no_suspicious_patterns": {"type": "boolean"},
                        "no_upcoding_or_unbundling": {"type": "boolean"},
                        "no_identity_fraud_indicators": {"type": "boolean"},
                        "no_irregular_treatment_patterns": {"type": "boolean"},
                        "no_unusual_timing_patterns": {"type": "boolean"},
                        "fraud_risk_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high"]
                        }
                    }
                },
                "confidence_score": {
                    "type": "number",
                    "description": "A score between 0.0 and 1.0 indicating confidence in the fraud assessment"
                },
                "is_approved": {
                    "type": "boolean",
                    "description": "Whether the claim passes fraud checks (true = no fraud detected)"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation of the fraud assessment with specific findings"
                }
            },
            "required": ["verification_result", "confidence_score", "is_approved", "notes"]
        }
