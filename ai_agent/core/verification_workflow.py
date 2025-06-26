from typing import Dict, Any, List, Tuple, TypedDict, Annotated
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph, END
import json
import logging

logger = logging.getLogger(__name__)

class InsuranceVerificationInput(BaseModel):
    """Input for the insurance verification workflow"""
    insurance_form_id: int
    patient_data: Dict[str, Any]
    insurance_policy_data: Dict[str, Any]
    medical_records: List[Dict[str, Any]]
    visit_data: Dict[str, Any]

class InsuranceVerificationState(TypedDict):
    """State maintained throughout the verification workflow"""
    # Input data
    insurance_form_id: int
    patient_data: Dict[str, Any]
    insurance_policy_data: Dict[str, Any]
    medical_records: List[Dict[str, Any]]
    visit_data: Dict[str, Any]
    
    # Verification results from each sub-agent
    eligibility_verification: Dict[str, Any]
    diagnostic_verification: Dict[str, Any]
    treatment_verification: Dict[str, Any] 
    billing_verification: Dict[str, Any]
    fraud_detection: Dict[str, Any]
    
    # Final verification result
    final_verification: Dict[str, Any]
    
    # Reflections data
    reflections: List[Dict[str, Any]]
    
    # Workflow control
    current_step: str
    next_step: str
    error: str

class InsuranceVerificationWorkflow:
    """
    LangGraph workflow for insurance verification using multiple agents
    """
    def __init__(self):
        self.workflow = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(InsuranceVerificationState)
        
        # Define nodes with different names than state keys
        workflow.add_node("check_eligibility", self.check_eligibility)
        workflow.add_node("check_diagnosis", self.check_diagnosis)
        workflow.add_node("check_treatment", self.check_treatment)
        workflow.add_node("check_billing", self.check_billing)
        workflow.add_node("check_fraud", self.check_fraud)
        workflow.add_node("finalize", self.finalize)
        
        # Define edges
        workflow.add_edge("check_eligibility", "check_diagnosis")
        workflow.add_edge("check_diagnosis", "check_treatment")
        workflow.add_edge("check_treatment", "check_billing")
        workflow.add_edge("check_billing", "check_fraud")
        workflow.add_edge("check_fraud", "finalize")
        workflow.add_edge("finalize", END)
        
        # Error handling - any step can go to final with error
        workflow.add_conditional_edges(
            "check_eligibility",
            lambda state: "finalize" if state.get("error") else "check_diagnosis"
        )
        workflow.add_conditional_edges(
            "check_diagnosis",
            lambda state: "finalize" if state.get("error") else "check_treatment"
        )
        workflow.add_conditional_edges(
            "check_treatment",
            lambda state: "finalize" if state.get("error") else "check_billing"
        )
        workflow.add_conditional_edges(
            "check_billing",
            lambda state: "finalize" if state.get("error") else "check_fraud"
        )
        
        # Set entry point
        workflow.set_entry_point("check_eligibility")
        
        return workflow
    
    def run(self, input_data: InsuranceVerificationInput) -> Dict[str, Any]:
        """
        Run the verification workflow
        
        Args:
            input_data: The input data for verification
            
        Returns:
            Dict: The final verification result
        """
        # Use the manual execution path by default to avoid LangGraph issues
        logger.info("Using manual verification workflow execution instead of LangGraph")
        
        initial_state = {
            "insurance_form_id": input_data.insurance_form_id,
            "patient_data": input_data.patient_data,
            "insurance_policy_data": input_data.insurance_policy_data,
            "medical_records": input_data.medical_records,
            "visit_data": input_data.visit_data,
            "eligibility_verification": {},
            "diagnostic_verification": {},
            "treatment_verification": {},
            "billing_verification": {},
            "fraud_detection": {},
            "final_verification": {},
            "reflections": [],
            "current_step": "eligibility_verification",
            "next_step": "",
            "error": ""
        }
        
        try:
            # Skip LangGraph due to version compatibility issues and use our manual execution
            # Direct execution of the node functions in sequence
            result = {}
            current_node = "check_eligibility"
            current_state = initial_state.copy()
            
            # Simple manual execution of the graph
            while current_node != END and current_node is not None:
                logger.info(f"Executing node: {current_node}")
                
                if current_node == "check_eligibility":
                    current_state = self.check_eligibility(current_state)
                    current_node = "check_diagnosis" if not current_state.get("error") else "finalize"
                elif current_node == "check_diagnosis":
                    current_state = self.check_diagnosis(current_state)
                    current_node = "check_treatment" if not current_state.get("error") else "finalize"
                elif current_node == "check_treatment":
                    current_state = self.check_treatment(current_state)
                    current_node = "check_billing" if not current_state.get("error") else "finalize"
                elif current_node == "check_billing":
                    current_state = self.check_billing(current_state)
                    current_node = "check_fraud" if not current_state.get("error") else "finalize"
                elif current_node == "check_fraud":
                    current_state = self.check_fraud(current_state)
                    current_node = "finalize"
                elif current_node == "finalize":
                    current_state = self.finalize(current_state)
                    current_node = END
            
            return current_state
        except Exception as e:
            logger.exception(f"Error in verification workflow: {str(e)}")
            error_type = type(e).__name__
            if "No module named" in str(e):
                error_notes = f"Missing dependency: {str(e)}. Please install the required package."
            elif "LangGraph" in str(e) or "graph" in str(e).lower():
                error_notes = f"LangGraph error: {str(e)}. The workflow engine encountered an issue."
            else:
                error_notes = f"Verification failed due to an error: {str(e)}"
            
            return {
                "error": str(e),
                "error_type": error_type,
                "final_verification": {
                    "is_approved": False,
                    "confidence_score": 0.0,
                    "notes": error_notes
                }
            }
    
    # Implementation of each node in the workflow
    def check_eligibility(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Verify patient eligibility for insurance claim"""
        try:
            from ..agents.eligibility_agent import EligibilityVerificationAgent
            
            state["current_step"] = "eligibility_verification"
            
            agent = EligibilityVerificationAgent()
            result = agent.run({
                "patient_data": state["patient_data"],
                "insurance_policy_data": state["insurance_policy_data"],
                "visit_data": state["visit_data"]
            })
            
            state["eligibility_verification"] = result
            state["next_step"] = "diagnostic_verification"
            
            # If eligibility verification fails, stop the workflow
            if not result.get("is_approved", False):
                state["final_verification"] = {
                    "is_approved": False,
                    "confidence_score": result.get("confidence_score", 0.0),
                    "notes": f"Eligibility verification failed: {result.get('notes', 'No notes provided')}"
                }
                state["next_step"] = "final_verification"
                
            return state
        except Exception as e:
            logger.exception(f"Error in eligibility verification: {str(e)}")
            state["error"] = str(e)
            return state
    
    def check_diagnosis(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Verify that diagnosis is accurate and covered by the insurance policy"""
        try:
            from ..agents.diagnostic_agent import DiagnosticVerificationAgent
            
            state["current_step"] = "diagnostic_verification"
            
            agent = DiagnosticVerificationAgent()
            result = agent.run({
                "patient_data": state["patient_data"],
                "insurance_policy_data": state["insurance_policy_data"],
                "visit_data": state["visit_data"],
                "medical_records": state["medical_records"]
            })
            
            state["diagnostic_verification"] = result
            state["next_step"] = "treatment_verification"
            
            return state
        except Exception as e:
            logger.exception(f"Error in diagnostic verification: {str(e)}")
            state["error"] = str(e)
            return state
    
    def check_treatment(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Verify that the treatment is appropriate for the diagnosis and covered by insurance"""
        try:
            from ..agents.treatment_agent import TreatmentVerificationAgent
            
            state["current_step"] = "treatment_verification"
            
            agent = TreatmentVerificationAgent()
            result = agent.run({
                "patient_data": state["patient_data"],
                "insurance_policy_data": state["insurance_policy_data"],
                "visit_data": state["visit_data"],
                "medical_records": state["medical_records"],
                "diagnostic_verification": state["diagnostic_verification"]
            })
            
            state["treatment_verification"] = result
            state["next_step"] = "billing_verification"
            
            return state
        except Exception as e:
            logger.exception(f"Error in treatment verification: {str(e)}")
            state["error"] = str(e)
            return state
    
    def check_billing(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Verify that the billing is accurate and matches the treatment provided"""
        try:
            from ..agents.billing_agent import BillingVerificationAgent
            
            state["current_step"] = "billing_verification"
            
            agent = BillingVerificationAgent()
            result = agent.run({
                "patient_data": state["patient_data"],
                "insurance_policy_data": state["insurance_policy_data"],
                "visit_data": state["visit_data"],
                "medical_records": state["medical_records"],
                "treatment_verification": state["treatment_verification"],
                "diagnostic_verification": state["diagnostic_verification"]
            })
            
            state["billing_verification"] = result
            state["next_step"] = "fraud_detection"
            
            return state
        except Exception as e:
            logger.exception(f"Error in billing verification: {str(e)}")
            state["error"] = str(e)
            return state
    
    def check_fraud(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Check for potential fraud indicators in the claim"""
        try:
            from ..agents.fraud_agent import FraudDetectionAgent
            
            state["current_step"] = "fraud_detection"
            
            agent = FraudDetectionAgent()
            result = agent.run({
                "patient_data": state["patient_data"],
                "insurance_policy_data": state["insurance_policy_data"],
                "visit_data": state["visit_data"],
                "medical_records": state["medical_records"],
                "treatment_verification": state["treatment_verification"],
                "diagnostic_verification": state["diagnostic_verification"],
                "billing_verification": state["billing_verification"]
            })
            
            state["fraud_detection"] = result
            state["next_step"] = "final_verification"
            
            return state
        except Exception as e:
            logger.exception(f"Error in fraud detection: {str(e)}")
            state["error"] = str(e)
            return state
    
    def finalize(self, state: InsuranceVerificationState) -> InsuranceVerificationState:
        """Combine all verification results and make a final decision"""
        try:
            from ..core.reflexion_agent import ReflexionAgent
            
            state["current_step"] = "final_verification"
            
            # Combine all verification results
            verification_results = {
                "eligibility": state["eligibility_verification"],
                "diagnostic": state["diagnostic_verification"],
                "treatment": state["treatment_verification"],
                "billing": state["billing_verification"],
                "fraud_detection": state["fraud_detection"]
            }
            
            # Calculate average confidence score
            confidence_scores = [
                result.get("confidence_score", 0.0) 
                for result in verification_results.values() 
                if "confidence_score" in result
            ]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Check if all verifications are approved
            all_approved = all(
                result.get("is_approved", False) 
                for result in verification_results.values() 
                if "is_approved" in result
            )
            
            # Generate initial final verification result
            initial_result = {
                "is_approved": all_approved,
                "confidence_score": avg_confidence,
                "verification_results": verification_results,
                "notes": self._generate_final_notes(verification_results, all_approved, avg_confidence)
            }
            
            # Apply reflexion to improve the final result
            reflexion_agent = ReflexionAgent(max_iterations=3)
            reflexion_result = reflexion_agent.reflect(
                initial_prompt=f"Verify insurance claim {state['insurance_form_id']}",
                initial_response=initial_result,
                context={
                    "patient_data": state["patient_data"],
                    "insurance_policy_data": state["insurance_policy_data"],
                    "visit_data": state["visit_data"],
                    "verification_results": verification_results
                }
            )
            
            # Save reflections for later analysis
            state["reflections"] = reflexion_result.get("reflections", [])
            
            # Use the final response after reflection
            final_result = reflexion_result.get("final_response", initial_result)
            
            # Set final verification result
            state["final_verification"] = final_result
            
            return state
        except Exception as e:
            logger.exception(f"Error in final verification: {str(e)}")
            state["error"] = str(e)
            state["final_verification"] = {
                "is_approved": False,
                "confidence_score": 0.0,
                "notes": f"Final verification failed due to an error: {str(e)}"
            }
            return state
    
    def _generate_final_notes(self, verification_results: Dict[str, Any], 
                             all_approved: bool, confidence_score: float) -> str:
        """Generate final notes summarizing the verification results"""
        notes = []
        
        if all_approved:
            notes.append(f"All verification checks passed with an average confidence score of {confidence_score:.2f}.")
        else:
            notes.append(f"Verification failed with an average confidence score of {confidence_score:.2f}.")
            
            # Add specific failure reasons
            failure_reasons = []
            for verification_type, result in verification_results.items():
                if not result.get("is_approved", True):
                    failure_reasons.append(
                        f"- {verification_type.capitalize()} verification: {result.get('notes', 'No notes provided')}"
                    )
            
            if failure_reasons:
                notes.append("Failure reasons:")
                notes.extend(failure_reasons)
        
        return "\n".join(notes)
