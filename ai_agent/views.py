from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from insurance.models import InsuranceForm
from .models import AIVerificationResult
from .tasks.verification import trigger_insurance_verification

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def trigger_verification(request, insurance_form_id):
    """
    Trigger AI verification for an insurance form
    """
    insurance_form = get_object_or_404(InsuranceForm, id=insurance_form_id)
    
    # For GET requests, just return status
    if request.method == 'GET':
        try:
            verification = AIVerificationResult.objects.get(insurance_form_id=insurance_form_id)
            return Response({
                "insurance_form_id": insurance_form_id,
                "verification_status": verification.status,
                "is_approved": verification.is_approved,
                "created_at": verification.created_at,
                "completed_at": verification.completed_at,
                "message": f"Verification status for insurance form {insurance_form_id}"
            })
        except AIVerificationResult.DoesNotExist:
            return Response({
                "insurance_form_id": insurance_form_id,
                "verification_status": "not_started",
                "message": "No verification has been started for this form yet. Use POST to start verification."
            })
    
    # For POST requests, trigger verification
    # Check if user has permission to trigger verification
    if not request.user.is_staff and request.user != insurance_form.created_by:
        return Response(
            {"error": "You don't have permission to trigger verification for this form"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Trigger verification
    task = trigger_insurance_verification.delay(insurance_form_id)
    
    return Response({
        "message": "Verification triggered successfully",
        "task_id": task.id
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verification_result(request, insurance_form_id):
    """
    Get the result of an AI verification for an insurance form
    """
    insurance_form = get_object_or_404(InsuranceForm, id=insurance_form_id)
    
    # Check if user has permission to view verification
    if not request.user.is_staff and request.user != insurance_form.created_by:
        return Response(
            {"error": "You don't have permission to view verification for this form"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        verification = AIVerificationResult.objects.get(insurance_form=insurance_form)
        eligible_verification = verification.eligibility_verification or {}
        diagnostic_verification = verification.diagnostic_verification or {}
        treatment_verification = verification.treatment_verification or {}
        billing_verification = verification.billing_verification or {}
        fraud_detection = verification.fraud_detection or {}
        
        return Response({
            "status": verification.status,
            "is_approved": verification.is_approved,
            "confidence_score": verification.confidence_score,
            "summary": verification.verification_summary,
            # "verification_result": verification.verification_result,
            "eligibility_verification": eligible_verification,
            "diagnostic_verification": diagnostic_verification,
            "treatment_verification": treatment_verification,
            "billing_verification": billing_verification,
            "fraud_detection": fraud_detection,
            # "reflections": verification.reflections,
            "created_at": verification.created_at,
            "completed_at": verification.completed_at
        })
    except AIVerificationResult.DoesNotExist:
        return Response(
            {"error": "No verification found for this insurance form"},
            status=status.HTTP_404_NOT_FOUND
        )
