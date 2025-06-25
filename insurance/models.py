from django.db import models
from django.conf import settings

# Create your models here.

class InsuranceDocument(models.Model):
    """
    Model for digital insurance documents.
    """
    document_id = models.AutoField(primary_key=True)
    patient_id = models.CharField(max_length=100, unique=True)
    document_type = models.CharField(max_length=50)  # e.g., 'policy', 'claim'
    document_content = models.TextField()  # Store the content of the document
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_type} for {self.patient_id}"

class InsuranceType(models.Model):
    """
    Model for different types of insurance policies available.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_cashless = models.BooleanField(default=False)
    coverage_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    max_coverage_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    waiting_period_days = models.PositiveIntegerField(default=0)
    requires_pre_authorization = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name}" + (" (Cashless)" if self.is_cashless else "")

class InsurancePolicy(models.Model):
    """
    Model for insurance policies linked to patients.
    """
    policy_number = models.CharField(max_length=100, unique=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='insurance_policies_extended')
    insurance_type = models.ForeignKey(InsuranceType, on_delete=models.CASCADE, related_name='policies')
    provider = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255)
    valid_from = models.DateField()
    valid_till = models.DateField()
    sum_insured = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Insurance Policies"
    
    def __str__(self):
        return f"{self.policy_number} - {self.provider} ({self.patient.email})"
    
    @property
    def is_valid(self):
        """Check if the policy is currently valid"""
        from django.utils import timezone
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_till

class InsuranceForm(models.Model):
    """
    Model for insurance claim forms linked to patient visits.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('payment_pending', 'Payment Pending'),
        ('payment_completed', 'Payment Completed')
    ]
    
    visit = models.ForeignKey('ehr.PatientVisit', on_delete=models.CASCADE, related_name='insurance_forms')
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claim_forms')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_insurance_forms'
    )
    diagnosis = models.TextField(blank=True, null=True)
    treatment_description = models.TextField()
    claim_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    is_ai_approved = models.BooleanField(default=False)
    ai_confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    ai_processing_date = models.DateTimeField(null=True, blank=True)
    
    # Additional fields for cashless processing
    is_cashless_claim = models.BooleanField(default=False)
    pre_authorization_reference = models.CharField(max_length=100, blank=True, null=True)
    pre_authorization_date = models.DateTimeField(null=True, blank=True)
    pre_authorized_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Insurance Form for Visit {self.visit.visit_number} ({self.status})"
    
    def submit(self):
        """Mark the form as submitted"""
        from django.utils import timezone
        self.status = 'submitted'
        self.submission_date = timezone.now()
        self.save()
    
    def approve(self, approved_amount=None, ai_approved=False):
        """Mark the form as approved"""
        from django.utils import timezone
        self.status = 'approved'
        self.approval_date = timezone.now()
        if approved_amount is not None:
            self.approved_amount = approved_amount
        if ai_approved:
            self.is_ai_approved = True
            self.ai_processing_date = timezone.now()
        self.save()
    
    def reject(self, reason=None):
        """Mark the form as rejected"""
        from django.utils import timezone
        self.status = 'rejected'
        if reason:
            self.rejection_reason = reason
        self.save()
