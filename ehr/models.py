from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary_storage.storage import RawMediaCloudinaryStorage
import uuid
import secrets
from datetime import timedelta

# Create your models here.

class Document(models.Model):
    """Medical document belonging to a patient, uploaded by a user (doctor/patient/admin)."""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='documents/', storage=RawMediaCloudinaryStorage())
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)  # Admin approval
    is_emergency_accessible = models.BooleanField(default=False)  # Can be accessed in emergency
    document_type = models.CharField(max_length=50, blank=True)  # Type of document (e.g., Lab Report, Prescription)
    
    def __str__(self):
        return f"Document for {self.patient.email} - {self.description[:30]}"

class AccessRequest(models.Model):
    """Doctor requests access to a patient's documents, admin can approve."""
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_requests_as_doctor')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='access_requests_as_patient')
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Access request: {self.doctor.email} -> {self.patient.email}"

class NFCCard(models.Model):
    """NFC card linked to a patient's EHR."""
    patient = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nfc_card')
    card_id = models.UUIDField(default=uuid.uuid4, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"NFC Card for {self.patient.email}"

class NFCSession(models.Model):
    """Stores temporary session data when a patient taps their NFC card."""
    SESSION_TYPE_CHOICES = [
        ('doctor', 'Doctor Access'),
        ('emergency', 'Emergency Access'),
        ('anonymous', 'Anonymous Emergency Access'),
        ('patient', 'Patient Self Access'),
    ]
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nfc_sessions')
    accessed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='accessed_sessions')
    session_token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='patient')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Session valid for 4 hours by default
            self.expires_at = timezone.now() + timedelta(hours=4)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at
    
    def invalidate(self):
        self.is_active = False
        self.save()
    
    def __str__(self):
        return f"Session for {self.patient.email} - Expires: {self.expires_at}"

class EmergencyAccess(models.Model):
    """Emergency access tokens for a patient's essential medical information."""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_tokens')
    access_token = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Emergency token valid for 24 hours by default
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        return timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Emergency access for {self.patient.email}"
