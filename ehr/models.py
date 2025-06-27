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
    content = models.TextField(blank=True)  # Parsed content of the document
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)  # Admin approval
    is_emergency_accessible = models.BooleanField(default=False)  # Can be accessed in emergency
    document_type = models.CharField(max_length=50, blank=True)  # Type of document (e.g., Lab Report, Prescription)
    visit = models.ForeignKey('PatientVisit', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    
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
    visit = models.ForeignKey('PatientVisit', on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Session valid for 4 hours by default
            self.expires_at = timezone.now() + timedelta(hours=4)
        super().save(*args, **kwargs)
    
    @property
    def is_valid(self):
        """Check if this session is valid and can be used."""
        return self.is_active and timezone.now() < self.expires_at
    
    def validate_session(self):
        """
        Validates the session and returns appropriate status information.
        Returns a tuple: (is_valid, error_code, error_message)
        """
        if not self.is_active:
            return (False, "inactive_session", "This session is no longer active")
        
        if timezone.now() >= self.expires_at:
            return (False, "expired_session", "This session has expired, please generate a new one by tapping the NFC card again")
        
        return (True, None, None)
    
    def invalidate(self):
        """Mark this session as inactive."""
        self.is_active = False
        self.save()
        
    def extend_session(self, hours=4):
        """Extend the session by the specified number of hours."""
        if self.is_valid:
            self.expires_at = timezone.now() + timedelta(hours=hours)
            self.save()
            return True
        return False
    
    def create_visit(self, visit_type, reason_for_visit=None, created_by=None):
        """
        Create a new patient visit from this session.
        Only call if the session is valid and accessed by a doctor or admin.
        Returns tuple (visit, success, error_message)
        """
        from .models import PatientVisit, SessionActivity
        
        # Validate session
        is_valid, error_code, error_message = self.validate_session()
        if not is_valid:
            return None, False, error_message
        
        if self.visit:
            return self.visit, True, None
        
        # Default to the accessed_by user as the creator if not specified
        if not created_by:
            created_by = self.accessed_by
        
        # Create the visit
        visit = PatientVisit.objects.create(
            patient=self.patient,
            visit_type=visit_type,
            reason_for_visit=reason_for_visit,
            attending_doctor=self.accessed_by if self.session_type == 'doctor' else None,
            created_by=created_by,
            creating_session=self  # Link the creating session
        )
        
        # Link this session to the visit
        self.visit = visit
        self.save()
        
        # Log this activity
        SessionActivity.log_activity(
            session=self,
            user=created_by,
            activity_type='create_visit',
            visit=visit,
            details=f"Created {visit_type} visit using NFC session"
        )
        
        return visit, True, None
    
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

class PatientVisit(models.Model):
    """
    Tracks a patient's complete hospital visit from check-in to checkout.
    This model aggregates all documents, sessions, and billing for a hospital visit.
    """
    VISIT_STATUS_CHOICES = [
        ('checked_in', 'Checked In'),
        ('in_progress', 'In Progress'),
        ('ready_for_checkout', 'Ready for Checkout'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    VISIT_TYPE_CHOICES = [
        ('emergency', 'Emergency'),
        ('outpatient', 'Outpatient'),
        ('inpatient', 'Inpatient'),
        ('followup', 'Follow-up'),
        ('routine_checkup', 'Routine Checkup'),
        ('specialist_consultation', 'Specialist Consultation'),
    ]
    
    # Base Visit Information
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visits')
    visit_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=VISIT_STATUS_CHOICES, default='checked_in')
    visit_type = models.CharField(max_length=30, choices=VISIT_TYPE_CHOICES)
    
    # From Visit Model
    chief_complaint = models.TextField(blank=True, null=True)  # Primary reason for the visit
    location = models.CharField(max_length=100, blank=True, null=True)  # Hospital department or room
    
    # Medical Details
    attending_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='attended_visits'
    )
    reason_for_visit = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    treatment_notes = models.TextField(blank=True, null=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    recommendation = models.TextField(blank=True, null=True)  # Doctor's recommendations
    
    # Basic medical information (keeping only essential fields in this model)
    diagnosis = models.TextField(blank=True, null=True)  # Brief diagnosis note
    treatment_notes = models.TextField(blank=True, null=True)  # General treatment notes
    
    # Track which session created this visit
    creating_session = models.OneToOneField(
        'NFCSession',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_visit'
    )
    
    # Tags for searching and categorization
    tags = models.CharField(max_length=255, blank=True, null=True)  # Comma-separated list of tags
    
    # Billing information
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    insurance_coverage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, 
                                     choices=[('pending', 'Pending'), 
                                             ('paid', 'Paid'), 
                                             ('insurance_processing', 'Insurance Processing'),
                                             ('waived', 'Waived')],
                                     default='pending')
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_visits'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-check_in_time']
    
    def checkout(self, checked_out_by=None):
        """
        Complete a visit and set checkout time.
        Also logs the activity and invalidates sessions.
        """
        from django.utils import timezone
        
        self.check_out_time = timezone.now()
        self.status = 'completed'
        self.save()
        
        # Also invalidate any active sessions for this visit
        for session in self.sessions.filter(is_active=True):
            session.invalidate()
            
            # Log this activity if we know who checked out
            if checked_out_by:
                SessionActivity.log_activity(
                    session=session,
                    user=checked_out_by,
                    activity_type='checkout_visit',
                    visit=self,
                    details=f"Checked out visit {self.visit_number}"
                )
                
        return True
    
    def can_be_edited_by(self, user):
        """Check if a user can edit this visit."""
        # Staff can edit any visit
        if user.is_staff:
            return True, None
            
        # Attending doctor can edit their assigned visits
        if user == self.attending_doctor:
            return True, None
            
        # Doctor with active session can edit
        if hasattr(user, 'user_type') and user.user_type.name == 'Doctor':
            session = self.get_active_session_for_user(user)
            if session:
                return True, None
            else:
                return False, "No active NFC session found. Please generate a new session by tapping the NFC card."
            
        # None of the conditions met
        return False, "You do not have permission to edit this visit"
    
    def get_active_session_for_user(self, user):
        """Get an active NFC session for this user and visit, or None if none exists."""
        try:
            return self.sessions.filter(
                accessed_by=user, 
                is_active=True, 
                expires_at__gt=timezone.now()
            ).latest('started_at')
        except NFCSession.DoesNotExist:
            return None
    
    def has_active_session_for_user(self, user):
        """Check if a user has an active NFC session for this visit."""
        return self.sessions.filter(
            accessed_by=user, 
            is_active=True, 
            expires_at__gt=timezone.now()
        ).exists()
        
    def add_session_activity(self, session, user, activity_type, document=None, details=''):
        """Convenience method to log an activity for this visit."""
        return SessionActivity.log_activity(
            session=session,
            user=user,
            activity_type=activity_type,
            visit=self,
            document=document,
            details=details
        )
    
    def get_latest_vital_signs(self):
        """Get the latest recorded vital signs for this visit."""
        try:
            return self.vital_signs.latest('recorded_at')
        except VitalSigns.DoesNotExist:
            return None
    
    def auto_create_charges(self):
        """
        Automatically create charges based on visit type.
        This is called when a visit is created.
        """
        # Base consultation charge for all visit types
        if not self.charges.filter(charge_type='consultation').exists():
            base_charge = 50.00  # Default consultation fee
            
            # Adjust based on visit type
            if self.visit_type == 'emergency':
                base_charge = 150.00
            elif self.visit_type == 'specialist_consultation':
                base_charge = 100.00
            elif self.visit_type == 'inpatient':
                base_charge = 200.00
                
                # Add room charge for inpatient visits
                VisitCharge.objects.create(
                    visit=self,
                    description="Inpatient Room Charge (daily)",
                    amount=150.00,
                    charge_type='room_charge',
                    added_by=self.created_by
                )
            
            # Create the consultation charge
            VisitCharge.objects.create(
                visit=self,
                description=f"{self.get_visit_type_display()} Consultation",
                amount=base_charge,
                charge_type='consultation',
                added_by=self.created_by
            )
        
        # Update total amount
        self.update_total_amount()
    
    def update_total_amount(self):
        """Update the total amount based on all charges."""
        total = sum(charge.amount for charge in self.charges.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
    
    def save(self, *args, **kwargs):
        """Override save to manage charges for new visits."""
        is_new = self.pk is None
        
        # Save the model
        super().save(*args, **kwargs)
        
        # Create charges for new visits
        if is_new:
            self.auto_create_charges()

    def __str__(self):
        return f"Visit {self.visit_number} - {self.patient.email}"


class VisitCharge(models.Model):
    """Individual charges associated with a patient visit."""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='charges')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge_type = models.CharField(
        max_length=30,
        choices=[
            ('consultation', 'Consultation Fee'),
            ('medication', 'Medication'),
            ('procedure', 'Medical Procedure'),
            ('lab_test', 'Laboratory Test'),
            ('room_charge', 'Room Charge'),
            ('equipment', 'Equipment Usage'),
            ('vital_signs', 'Vital Signs Recording'),
            ('diagnosis', 'Diagnosis & Assessment'),
            ('imaging', 'Medical Imaging'),
            ('admission', 'Hospital Admission'),
            ('therapy', 'Therapy Session'),
            ('surgery', 'Surgical Procedure'),
            ('other', 'Other')
        ]
    )
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    insurance_covered = models.BooleanField(default=False)
    insurance_code = models.CharField(max_length=50, blank=True, null=True)  # Insurance billing code
    notes = models.TextField(blank=True, null=True)  # Additional information about the charge
    
    def __str__(self):
        return f"{self.charge_type}: {self.description} (${self.amount})"

class SessionActivity(models.Model):
    """
    Logs all activities performed with NFC sessions.
    This helps track which sessions were used for what purpose and by whom.
    """
    ACTIVITY_TYPES = [
        ('create_visit', 'Create Visit'),
        ('update_visit', 'Update Visit'),
        ('checkout_visit', 'Checkout Visit'),
        ('view_document', 'View Document'),
        ('upload_document', 'Upload Document'),
        ('add_charge', 'Add Charge'),
        ('record_vitals', 'Record Vital Signs'),
        ('add_diagnosis', 'Add Diagnosis'),
        ('add_lab_result', 'Add Lab Result'),
        ('add_prescription', 'Add Prescription'),
        ('other', 'Other Activity'),
    ]
    
    session = models.ForeignKey(NFCSession, on_delete=models.CASCADE, related_name='activities')
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='session_activities', null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='session_activities', null=True, blank=True)
    details = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Session Activities'
    
    @classmethod
    def log_activity(cls, session, user, activity_type, visit=None, document=None, details=''):
        """
        Convenience method to log a session activity.
        """
        return cls.objects.create(
            session=session,
            performed_by=user,
            activity_type=activity_type,
            visit=visit,
            document=document,
            details=details
        )
    
    def __str__(self):
        return f"{self.activity_type} by {self.performed_by.email} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class LabResult(models.Model):
    """Laboratory test results associated with a patient visit."""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='lab_results')
    test_name = models.CharField(max_length=255)
    test_date = models.DateTimeField()
    result = models.CharField(max_length=255)
    normal_range = models.CharField(max_length=100, blank=True, null=True)
    units = models.CharField(max_length=50, blank=True, null=True)
    interpretation = models.TextField(blank=True, null=True)
    performed_by = models.CharField(max_length=255, blank=True, null=True)
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordered_labs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.test_name} for {self.visit.patient.email} on {self.test_date.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        """Override save to add a charge when a lab result is created."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Add a charge for this lab test if it's a new record
        if is_new:
            # Default lab test charge
            charge_amount = 45.00
            
            # Certain tests might have different costs
            if 'blood panel' in self.test_name.lower() or 'comprehensive' in self.test_name.lower():
                charge_amount = 95.00
            elif 'mri' in self.test_name.lower() or 'ct' in self.test_name.lower() or 'scan' in self.test_name.lower():
                charge_amount = 350.00
            elif 'xray' in self.test_name.lower() or 'x-ray' in self.test_name.lower():
                charge_amount = 150.00
                
            VisitCharge.objects.create(
                visit=self.visit,
                description=f"Laboratory Test: {self.test_name}",
                amount=charge_amount,
                charge_type='lab_test',
                added_by=self.ordered_by
            )
            
            # Update the visit's total amount
            self.visit.update_total_amount()
            
            # Log this activity if there's an active session
            session = self.visit.get_active_session_for_user(self.ordered_by)
            if session:
                SessionActivity.log_activity(
                    session=session,
                    user=self.ordered_by,
                    activity_type='add_lab_result',
                    visit=self.visit,
                    details=f"Added lab result '{self.test_name}' for visit {self.visit.visit_number}"
                )


class Prescription(models.Model):
    """Medication prescriptions associated with a patient visit."""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='prescriptions')
    medication_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prescribed_medications'
    )
    pharmacy = models.CharField(max_length=255, blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.medication_name} for {self.visit.patient.email}"
    
    def save(self, *args, **kwargs):
        """Override save to add a medication charge when a prescription is created."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Add a charge for this medication if it's a new prescription
        if is_new:
            # Default medication charge
            charge_amount = 25.00
            
            # Calculate days of treatment
            if self.end_date and self.start_date:
                days_diff = (self.end_date - self.start_date).days
                if days_diff > 0:
                    charge_amount = days_diff * 5.00  # $5 per day of medication
            
            VisitCharge.objects.create(
                visit=self.visit,
                description=f"Medication: {self.medication_name}",
                amount=charge_amount,
                charge_type='medication',
                added_by=self.prescribed_by
            )
            
            # Update the visit's total amount
            self.visit.update_total_amount()
            
            # Log this activity if there's an active session
            session = self.visit.get_active_session_for_user(self.prescribed_by)
            if session:
                SessionActivity.log_activity(
                    session=session,
                    user=self.prescribed_by,
                    activity_type='add_prescription',
                    visit=self.visit,
                    details=f"Added prescription for '{self.medication_name}' for visit {self.visit.visit_number}"
                )

class VitalSigns(models.Model):
    """Records a patient's vital signs during a visit"""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='vital_signs')
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperature_unit = models.CharField(
        max_length=10, 
        choices=[('celsius', 'Celsius'), ('fahrenheit', 'Fahrenheit')], 
        default='celsius'
    )
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_unit = models.CharField(
        max_length=10, 
        choices=[('cm', 'Centimeters'), ('in', 'Inches')], 
        default='cm'
    )
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    weight_unit = models.CharField(
        max_length=10, 
        choices=[('kg', 'Kilograms'), ('lbs', 'Pounds')], 
        default='kg'
    )
    bmi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_vitals'
    )
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name_plural = 'Vital Signs'
    
    def save(self, *args, **kwargs):
        """Override save to calculate BMI and create a charge if needed"""
        is_new = self.pk is None
        
        # Calculate BMI if height and weight are available
        if self.height and self.weight:
            # Convert height to meters if in cm
            height_in_meters = self.height / 100 if self.height_unit == 'cm' else self.height * 0.0254
            
            # Convert weight to kg if in lbs
            weight_in_kg = self.weight if self.weight_unit == 'kg' else self.weight * 0.453592
            
            if height_in_meters > 0:
                self.bmi = round(weight_in_kg / (height_in_meters * height_in_meters), 2)
        
        super().save(*args, **kwargs)
        
        # Create a charge for recording vitals if it's a new record
        if is_new:
            # Check if there's already a vitals charge for this visit
            if not self.visit.charges.filter(charge_type='vital_signs').exists():
                VisitCharge.objects.create(
                    visit=self.visit,
                    description="Vital Signs Recording",
                    amount=25.00,
                    charge_type='vital_signs',
                    added_by=self.recorded_by
                )
                
                # Update the visit's total amount
                self.visit.update_total_amount()
                
                # Log this activity if there's an active session
                session = self.visit.get_active_session_for_user(self.recorded_by)
                if session:
                    SessionActivity.log_activity(
                        session=session,
                        user=self.recorded_by,
                        activity_type='record_vitals',
                        visit=self.visit,
                        details=f"Recorded vital signs for visit {self.visit.visit_number}"
                    )
    
    def __str__(self):
        return f"Vitals for {self.visit.patient.email} on {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"

class Diagnosis(models.Model):
    """Records a patient's diagnosis during a visit"""
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE, related_name='diagnoses')
    condition_name = models.CharField(max_length=255)
    icd_code = models.CharField(max_length=20, blank=True, null=True)  # International Classification of Diseases code
    diagnosis_date = models.DateField(auto_now_add=True)
    severity = models.CharField(
        max_length=20, 
        choices=[
            ('mild', 'Mild'), 
            ('moderate', 'Moderate'), 
            ('severe', 'Severe')
        ],
        default='moderate'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('resolved', 'Resolved'),
            ('recurrent', 'Recurrent'),
            ('chronic', 'Chronic')
        ],
        default='active'
    )
    notes = models.TextField(blank=True, null=True)
    treatment_plan = models.TextField(blank=True, null=True)
    diagnosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='made_diagnoses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-diagnosis_date']
        verbose_name_plural = 'Diagnoses'
    
    def save(self, *args, **kwargs):
        """Override save to create a diagnosis charge if needed"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Create a charge for this diagnosis if it's a new record
        if is_new:
            # Default diagnosis charge
            charge_amount = 75.00
            
            # Adjust based on severity
            if self.severity == 'severe':
                charge_amount = 125.00
            elif self.severity == 'mild':
                charge_amount = 50.00
            
            VisitCharge.objects.create(
                visit=self.visit,
                description=f"Diagnosis: {self.condition_name}",
                amount=charge_amount,
                charge_type='diagnosis',
                added_by=self.diagnosed_by
            )
            
            # Update the visit's total amount
            self.visit.update_total_amount()
            
            # Also update the visit's diagnosis field with a summary
            if not self.visit.diagnosis:
                self.visit.diagnosis = self.condition_name
                self.visit.save(update_fields=['diagnosis'])
            
            # Log this activity if there's an active session
            session = self.visit.get_active_session_for_user(self.diagnosed_by)
            if session:
                SessionActivity.log_activity(
                    session=session,
                    user=self.diagnosed_by,
                    activity_type='add_diagnosis',
                    visit=self.visit,
                    details=f"Added diagnosis '{self.condition_name}' for visit {self.visit.visit_number}"
                )
    
    def __str__(self):
        return f"{self.condition_name} for {self.visit.patient.email}"
