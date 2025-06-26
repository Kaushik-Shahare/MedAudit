from django.db import models
from django.utils import timezone
from insurance.models import InsuranceForm

class AIVerificationResult(models.Model):
    """
    Model to store AI verification results for insurance claims
    """
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    insurance_form = models.ForeignKey(InsuranceForm, on_delete=models.CASCADE, related_name='ai_verification_results')
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    verification_result = models.JSONField(null=True, blank=True)
    verification_summary = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Store verification results from different sub-agents
    eligibility_verification = models.JSONField(null=True, blank=True)
    diagnostic_verification = models.JSONField(null=True, blank=True)
    treatment_verification = models.JSONField(null=True, blank=True)
    billing_verification = models.JSONField(null=True, blank=True)
    fraud_detection = models.JSONField(null=True, blank=True)
    
    # Track iterations of reflective thinking
    iteration_count = models.PositiveIntegerField(default=0)
    reflections = models.JSONField(null=True, blank=True)
    
    def mark_as_completed(self, is_approved, confidence_score, verification_result, summary):
        self.status = 'completed'
        self.is_approved = is_approved
        self.confidence_score = confidence_score
        self.verification_result = verification_result
        self.verification_summary = summary
        self.completed_at = timezone.now()
        self.save()
    
    def mark_as_failed(self, error_message):
        self.status = 'failed'
        if not self.verification_result:
            self.verification_result = {}
        self.verification_result['error'] = error_message
        self.save()
    
    def mark_as_in_progress(self):
        self.status = 'in_progress'
        self.save()
    
    def __str__(self):
        return f"Verification for {self.insurance_form} - {self.status}"
