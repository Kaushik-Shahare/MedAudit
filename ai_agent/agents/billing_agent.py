from typing import Dict, Any, List
from ..core.base_agent import BaseAgent
from ..core.llm_service import LLMService

class BillingVerificationAgent(BaseAgent):
    """
    Agent that verifies the billing information is accurate and matches the treatment
    """
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify billing based on:
        1. Do the billed services match the documented treatment?
        2. Are the charges reasonable and customary for the services provided?
        3. Is there any duplicate billing?
        4. Are all services medically necessary?
        """
        # Extract relevant data
        patient_data = data.get("patient_data", {})
        insurance_policy_data = data.get("insurance_policy_data", {})
        visit_data = data.get("visit_data", {})
        diagnostic_verification = data.get("diagnostic_verification", {})
        treatment_verification = data.get("treatment_verification", {})
        
        # Create billing verification prompt
        prompt = self._create_billing_prompt(
            patient_data, 
            insurance_policy_data,
            visit_data,
            diagnostic_verification,
            treatment_verification
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
    
    def _create_billing_prompt(self, patient_data: Dict[str, Any],
                               insurance_policy_data: Dict[str, Any],
                               visit_data: Dict[str, Any],
                               diagnostic_verification: Dict[str, Any],
                               treatment_verification: Dict[str, Any]) -> str:
        """Create the prompt for billing verification"""
        prompt_parts = [
            "BILLING VERIFICATION TASK",
            "\nVerify if the billing information is accurate and matches the treatment provided:",
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
        
        # Add treatment verification result
        prompt_parts.append("\nTREATMENT VERIFICATION RESULT:")
        prompt_parts.append(f"- Is Approved: {treatment_verification.get('is_approved', False)}")
        prompt_parts.append(f"- Notes: {treatment_verification.get('notes', 'Not provided')}")
        
        # Add insurance policy coverage information
        prompt_parts.append("\nINSURANCE POLICY COVERAGE INFORMATION:")
        for key, value in insurance_policy_data.items():
            if 'coverage' in key.lower() or 'limit' in key.lower() or 'deductible' in key.lower():
                prompt_parts.append(f"- {key}: {value}")
        
        prompt_parts.append("\nVERIFICATION REQUIREMENTS:")
        prompt_parts.append("1. Verify if all billed services were documented as provided")
        prompt_parts.append("2. Check if the charges are reasonable and customary for the services")
        prompt_parts.append("3. Verify there is no duplicate billing or unbundled services")
        prompt_parts.append("4. Check if all billed services are medically necessary")
        prompt_parts.append("5. Verify if the total amount matches the sum of itemized charges")
        prompt_parts.append("6. Check if the charges are within the insurance coverage limits")
        prompt_parts.append("\nProvide a detailed verification result with specific reasons for approval or rejection.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert medical billing verification agent with deep knowledge of medical billing practices, coding, and insurance reimbursement policies.
        Your task is to carefully analyze the billing information to verify if it is accurate, appropriate, and matches the treatment provided.
        Be thorough, attentive to billing details, and provide clear reasoning for your decisions."""
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Define the output schema for the agent"""
        return {
            "type": "object",
            "properties": {
                "verification_result": {
                    "type": "object",
                    "properties": {
                        "services_match_documentation": {"type": "boolean"},
                        "charges_reasonable": {"type": "boolean"},
                        "no_duplicate_billing": {"type": "boolean"},
                        "services_medically_necessary": {"type": "boolean"},
                        "total_matches_itemized": {"type": "boolean"},
                        "within_coverage_limits": {"type": "boolean"}
                    }
                },
                "confidence_score": {
                    "type": "number",
                    "description": "A score between 0.0 and 1.0 indicating confidence in the verification"
                },
                "is_approved": {
                    "type": "boolean",
                    "description": "Whether the billing verification is approved"
                },
                "notes": {
                    "type": "string",
                    "description": "Explanation of the verification result with specific details"
                }
            },
            "required": ["verification_result", "confidence_score", "is_approved", "notes"]
        }
