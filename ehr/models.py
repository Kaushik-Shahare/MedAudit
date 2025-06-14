from django.db import models
from django.conf import settings

# Create your models here.

class PatientProfile(models.Model):
    """Profile for patient-specific information."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    # Add patient-specific fields as needed

class DoctorProfile(models.Model):
    """Profile for doctor-specific information."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    # Add doctor-specific fields as needed

class Document(models.Model):
    """Medical document belonging to a patient, uploaded by a user (doctor/patient/admin)."""
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='documents/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)  # Admin approval

class AccessRequest(models.Model):
    """Doctor requests access to a patient's documents, admin can approve."""
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='access_requests')
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='access_requests')
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
