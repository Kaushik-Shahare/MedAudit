from celery import shared_task
import logging
from django.utils import timezone
import json
import traceback

from insurance.models import InsuranceForm
from ..models import AIVerificationResult
from ..core.verification_workflow import InsuranceVerificationWorkflow, InsuranceVerificationInput

logger = logging.getLogger(__name__)

@shared_task
def trigger_insurance_verification(insurance_form_id):
    """
    Celery task to trigger insurance verification
    """
    try:
        # Get the insurance form
        insurance_form = InsuranceForm.objects.get(id=insurance_form_id)
        
        # Create or get verification result object
        verification_result, created = AIVerificationResult.objects.get_or_create(
            insurance_form=insurance_form,
            defaults={'status': 'pending'}
        )
        
        # If verification is already completed or in progress, don't trigger again
        if verification_result.status in ['completed', 'in_progress']:
            logger.info(f"Verification already {verification_result.status} for insurance form {insurance_form_id}")
            return f"Verification already {verification_result.status}"
        
        # Mark as in progress
        verification_result.mark_as_in_progress()
        
        # Start verification process
        _process_insurance_verification.delay(verification_result.id)
        
        return f"Triggered verification for insurance form {insurance_form_id}"
    
    except InsuranceForm.DoesNotExist:
        logger.error(f"Insurance form {insurance_form_id} not found")
        return f"Insurance form {insurance_form_id} not found"
    
    except Exception as e:
        logger.exception(f"Error triggering verification for insurance form {insurance_form_id}: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def _process_insurance_verification(verification_result_id):
    """
    Process the insurance verification
    """
    try:
        # Get the verification result object
        verification_result = AIVerificationResult.objects.get(id=verification_result_id)
        insurance_form = verification_result.insurance_form
        
        # Prepare input data
        input_data = _prepare_verification_input(insurance_form)
        
        # Run the verification workflow
        workflow = InsuranceVerificationWorkflow()
        verification_output = workflow.run(input_data)
        
        # Process the verification output
        final_verification = verification_output.get('final_verification', {})
        is_approved = final_verification.get('is_approved', False)
        confidence_score = final_verification.get('confidence_score', 0.0)
        
        # Store the verification details
        verification_result.mark_as_completed(
            is_approved=is_approved,
            confidence_score=confidence_score,
            verification_result=verification_output,
            summary=final_verification.get('notes', 'No summary provided')
        )
        
        # Store individual agent results
        verification_result.eligibility_verification = verification_output.get('eligibility_verification', {})
        verification_result.diagnostic_verification = verification_output.get('diagnostic_verification', {})
        verification_result.treatment_verification = verification_output.get('treatment_verification', {})
        verification_result.billing_verification = verification_output.get('billing_verification', {})
        verification_result.fraud_detection = verification_output.get('fraud_detection', {})
        verification_result.reflections = verification_output.get('reflections', [])
        verification_result.save()
        
        # If approval meets confidence threshold, update insurance form
        if is_approved and confidence_score >= 0.7:
            insurance_form.is_ai_approved = True
            insurance_form.ai_confidence_score = confidence_score
            insurance_form.ai_analysis = verification_output
            insurance_form.ai_processing_date = timezone.now()
            insurance_form.save()
        
        return f"Completed verification for insurance form {insurance_form.id}"
    
    except AIVerificationResult.DoesNotExist:
        logger.error(f"Verification result {verification_result_id} not found")
        return f"Verification result {verification_result_id} not found"
    
    except Exception as e:
        logger.exception(f"Error processing verification: {str(e)}")
        
        # Mark verification as failed
        try:
            verification_result = AIVerificationResult.objects.get(id=verification_result_id)
            error_message = f"{str(e)}\n\n{traceback.format_exc()}"
            verification_result.mark_as_failed(error_message)
        except:
            pass  # If we can't update the verification result, just log the error
        
        return f"Error: {str(e)}"

def _prepare_verification_input(insurance_form):
    """
    Prepare input data for the verification workflow
    """
    try:
        # Get patient data
        patient = insurance_form.visit.patient
        patient_profile = patient.profile
        patient_data = {
            "id": patient.id,
            "email": patient.email,
            "name": patient_profile.name if hasattr(patient, 'profile') else "",
            "gender": patient_profile.gender if hasattr(patient, 'profile') else "",
            "date_of_birth": patient_profile.date_of_birth.isoformat() if hasattr(patient_profile, 'date_of_birth') and patient_profile.date_of_birth else "",
            "allergies": patient_profile.allergies if hasattr(patient_profile, 'allergies') else [],
            "chronic_conditions": patient_profile.chronic_conditions if hasattr(patient_profile, 'chronic_conditions') else []
        }
        
        # Get insurance policy data
        policy = insurance_form.policy
        insurance_type = policy.insurance_type
        insurance_policy_data = {
            "policy_number": policy.policy_number,
            "provider": policy.provider,
            "valid_from": policy.valid_from.isoformat(),
            "valid_till": policy.valid_till.isoformat(),
            "sum_insured": str(policy.sum_insured),
            "is_active": policy.is_active,
            "insurance_type": insurance_type.name,
            "is_cashless": insurance_type.is_cashless,
            "coverage_percentage": str(insurance_type.coverage_percentage),
            "max_coverage_amount": str(insurance_type.max_coverage_amount),
            "waiting_period_days": insurance_type.waiting_period_days,
            "requires_pre_authorization": insurance_type.requires_pre_authorization
        }
        
        # Get visit data
        visit = insurance_form.visit
        visit_data = {
            "visit_number": visit.visit_number,
            "visit_type": visit.visit_type,
            "check_in_time": visit.check_in_time.isoformat(),
            "status": visit.status,
            "chief_complaint": visit.chief_complaint,
            "diagnosis": insurance_form.diagnosis or visit.diagnosis,
            "icd_code": insurance_form.icd_code,
            "treatment_notes": visit.treatment_notes,
            "total_amount": str(visit.total_amount),
            "insurance_form": {
                "claim_amount": str(insurance_form.claim_amount),
                "is_cashless_claim": insurance_form.is_cashless_claim,
                "treatment_type": insurance_form.treatment_type,
                "admission_date": insurance_form.admission_date.isoformat() if insurance_form.admission_date else None,
                "expected_discharge_date": insurance_form.expected_discharge_date.isoformat() if insurance_form.expected_discharge_date else None,
                "treatment_description": insurance_form.treatment_description,
                "clinical_findings": insurance_form.clinical_findings,
                "investigation_details": insurance_form.investigation_details
            }
        }
        
        # Get charges if available
        try:
            charges = []
            for charge in visit.charges.all():
                charges.append({
                    "description": charge.description,
                    "amount": str(charge.amount),
                    "charge_type": charge.charge_type,
                    "insurance_covered": charge.insurance_covered,
                    "insurance_code": charge.insurance_code
                })
            visit_data["charges"] = charges
        except:
            visit_data["charges"] = []
        
        # Get medical records
        medical_records = []
        try:
            for document in visit.documents.all():
                medical_records.append({
                    "document_type": document.document_type,
                    "description": document.description,
                    "uploaded_at": document.uploaded_at.isoformat()
                })
        except:
            pass  # No documents available
            
        # Create input object
        input_data = InsuranceVerificationInput(
            insurance_form_id=insurance_form.id,
            patient_data=patient_data,
            insurance_policy_data=insurance_policy_data,
            medical_records=medical_records,
            visit_data=visit_data
        )
        
        return input_data
    
    except Exception as e:
        logger.exception(f"Error preparing verification input: {str(e)}")
        raise e
