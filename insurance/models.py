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
    Includes pre-authorization request details for cashless claims.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('payment_pending', 'Payment Pending'),
        ('payment_completed', 'Payment Completed'),
        ('pre_auth_pending', 'Pre-Authorization Pending'),
        ('pre_auth_approved', 'Pre-Authorization Approved'),
        ('pre_auth_rejected', 'Pre-Authorization Rejected'),
        ('enhancement_requested', 'Enhancement Requested')
    ]
    
    TREATMENT_TYPE_CHOICES = [
        ('emergency', 'Emergency'),
        ('planned', 'Planned Procedure'),
        ('maternity', 'Maternity'),
        ('day_care', 'Day Care'),
        ('outpatient', 'Outpatient'),
        ('post_hosp', 'Post-Hospitalization'),
        ('domiciliary', 'Domiciliary')
    ]
    
    HOSPITALIZATION_TYPE_CHOICES = [
        ('single_room', 'Single Room'),
        ('shared_room', 'Shared Room'),
        ('icu', 'ICU'),
        ('iccu', 'ICCU'),
        ('day_care', 'Day Care'),
        ('outpatient', 'Outpatient'),
        ('na', 'Not Applicable')
    ]
    
    PROVIDER_TYPE_CHOICES = [
        ('network', 'Network Hospital'),
        ('non_network', 'Non-Network Hospital')
    ]
    
    visit = models.ForeignKey('ehr.PatientVisit', on_delete=models.CASCADE, related_name='insurance_forms')
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claim_forms')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_insurance_forms'
    )
    
    # Basic Insurance Details
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft')
    is_cashless_claim = models.BooleanField(default=False)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPE_CHOICES, default='network', blank=True, null=True)
    
    # Patient Condition and Medical Details
    diagnosis = models.TextField(blank=True, null=True)
    icd_code = models.CharField(max_length=20, blank=True, null=True, help_text="ICD-10 diagnosis code")
    presenting_complaints = models.TextField(blank=True, null=True, help_text="Patient's presenting complaints with duration")
    past_history = models.TextField(blank=True, null=True, help_text="Relevant past medical/surgical history")
    treatment_description = models.TextField()
    clinical_findings = models.TextField(blank=True, null=True)
    proposed_line_of_treatment = models.TextField(blank=True, null=True)
    investigation_details = models.TextField(blank=True, null=True, help_text="Investigation reports supporting diagnosis")
    route_of_drug_administration = models.CharField(max_length=255, blank=True, null=True)
    
    # Hospital and Treatment Details
    treatment_type = models.CharField(max_length=20, choices=TREATMENT_TYPE_CHOICES, default='planned', blank=True, null=True)
    hospitalization_type = models.CharField(max_length=20, choices=HOSPITALIZATION_TYPE_CHOICES, default='shared_room', blank=True, null=True)
    expected_days_of_stay = models.PositiveIntegerField(null=True, blank=True)
    admission_date = models.DateField(null=True, blank=True)
    expected_discharge_date = models.DateField(null=True, blank=True)
    treating_doctor = models.CharField(max_length=255, blank=True, null=True)
    doctor_registration_number = models.CharField(max_length=50, blank=True, null=True)
    is_injury_related = models.BooleanField(default=False, help_text="Whether condition is related to an injury")
    injury_details = models.TextField(blank=True, null=True)
    is_maternity_related = models.BooleanField(default=False)
    date_of_delivery = models.DateField(null=True, blank=True)
    
    # Financial Details
    claim_amount = models.DecimalField(max_digits=10, decimal_places=2)
    room_rent_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    icu_charges_per_day = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ot_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Operation Theatre charges")
    professional_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    medicine_consumables = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    investigation_charges = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Pre-authorization Details
    pre_authorization_reference = models.CharField(max_length=100, blank=True, null=True)
    pre_authorization_date = models.DateTimeField(null=True, blank=True)
    pre_authorized_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pre_auth_remarks = models.TextField(blank=True, null=True, help_text="Insurer's remarks on pre-authorization")
    
    # AI Approval
    is_ai_approved = models.BooleanField(default=False)
    ai_confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    ai_processing_date = models.DateTimeField(null=True, blank=True)
    
    # Enhancement Details
    enhancement_requested = models.BooleanField(default=False)
    enhancement_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    enhancement_reason = models.TextField(blank=True, null=True)
    
    # Process Dates
    submission_date = models.DateTimeField(null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Insurance Form for Visit {self.visit.visit_number} ({self.status})"
    
    def submit(self):
        """Mark the form as submitted"""
        from django.utils import timezone
        if self.is_cashless_claim:
            self.status = 'pre_auth_pending'
        else:
            self.status = 'submitted'
        self.submission_date = timezone.now()
        self.save()
    
    def approve(self, approved_amount=None, ai_approved=False):
        """Mark the form as approved"""
        from django.utils import timezone
        if self.is_cashless_claim and self.status == 'pre_auth_pending':
            self.status = 'pre_auth_approved'
        else:
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
        if self.is_cashless_claim and self.status == 'pre_auth_pending':
            self.status = 'pre_auth_rejected'
        else:
            self.status = 'rejected'
            
        if reason:
            self.rejection_reason = reason
        self.save()
        
    def request_enhancement(self, amount, reason=None):
        """Request enhancement of pre-authorized amount"""
        from django.utils import timezone
        if not self.is_cashless_claim:
            raise ValueError("Enhancement can only be requested for cashless claims")
            
        self.enhancement_requested = True
        self.enhancement_amount = amount
        if reason:
            self.enhancement_reason = reason
        self.status = 'enhancement_requested'
        self.save()
        
    def finalize_claim(self, final_amount=None):
        """Finalize the claim after treatment completion"""
        from django.utils import timezone
        if self.is_cashless_claim and self.status in ['pre_auth_approved', 'enhancement_requested']:
            if final_amount:
                self.claim_amount = final_amount
            self.status = 'payment_pending'
            self.save()
        
    def mark_payment_completed(self):
        """Mark the payment as completed"""
        self.status = 'payment_completed'
        self.save()
    
    @classmethod
    def create_from_visit(cls, visit, policy, created_by, is_cashless=False):
        """
        Automatically create an insurance form from a patient visit.
        Pulls relevant data from the visit, diagnoses, and patient profile.
        """
        from django.utils import timezone
        
        # Get the latest diagnosis from the visit if available
        diagnosis_text = None
        diagnosis_obj = None
        
        try:
            # This assumes there is a 'diagnoses' related_name in the Diagnosis model
            latest_diagnosis = visit.diagnoses.order_by('-diagnosis_date').first()
            if latest_diagnosis:
                diagnosis_text = latest_diagnosis.diagnosis
                diagnosis_obj = latest_diagnosis
        except:
            # If there's no relation or any other error, use the visit's diagnosis field
            diagnosis_text = visit.diagnosis
        
        # Get the latest vital signs
        vital_signs = None
        try:
            vital_signs = visit.vital_signs.order_by('-recorded_at').first()
        except:
            pass
        
        # Get patient details from patient profile
        patient = visit.patient
        patient_profile = None
        try:
            patient_profile = patient.profile
        except:
            pass
        
        # Create the form with basic details
        form = cls.objects.create(
            visit=visit,
            policy=policy,
            created_by=created_by,
            is_cashless_claim=is_cashless,
            diagnosis=diagnosis_text,
            treatment_description=visit.treatment_notes or "Treatment details to be added",
            claim_amount=0.00,  # Will need to be updated later
            
            # Pre-populate with patient medical details if available
            past_history=patient_profile.chronic_conditions if patient_profile and hasattr(patient_profile, 'chronic_conditions') else None,
            
            # Hospital and treatment details
            treatment_type='emergency' if visit.visit_type == 'emergency' else 'planned',
            hospitalization_type='outpatient' if visit.visit_type == 'outpatient' else 'shared_room',
            expected_days_of_stay=7 if visit.visit_type == 'inpatient' else 1,
            admission_date=timezone.now().date(),
            expected_discharge_date=(timezone.now() + timezone.timedelta(days=7)).date() if visit.visit_type == 'inpatient' else timezone.now().date(),
            treating_doctor=visit.attending_doctor.profile.name if visit.attending_doctor and hasattr(visit.attending_doctor, 'profile') else None,
            
            # Status should be draft initially
            status='draft',
        )
        
        # If vital signs exist, add them to clinical findings
        if vital_signs:
            bp_text = f"BP: {vital_signs.blood_pressure_systolic}/{vital_signs.blood_pressure_diastolic}" if vital_signs.blood_pressure_systolic else ""
            temp_text = f"Temp: {vital_signs.temperature}°{vital_signs.temperature_unit}" if vital_signs.temperature else ""
            hr_text = f"HR: {vital_signs.heart_rate}" if vital_signs.heart_rate else ""
            spo2_text = f"SpO2: {vital_signs.oxygen_saturation}%" if vital_signs.oxygen_saturation else ""
            
            vital_text = ", ".join(filter(None, [bp_text, temp_text, hr_text, spo2_text]))
            if vital_text:
                form.clinical_findings = vital_text
        
        # Add lab results if available
        try:
            lab_results = visit.lab_results.all()
            if lab_results:
                lab_text = "Lab Results: " + "; ".join([f"{lab.test_name}: {lab.result}" for lab in lab_results[:5]])
                form.investigation_details = lab_text
        except:
            pass
        
        # Add prescriptions if available
        try:
            prescriptions = visit.prescriptions.all()
            if prescriptions:
                med_text = "Medications: " + "; ".join([f"{rx.medication_name} {rx.dosage}" for rx in prescriptions[:5]])
                if form.treatment_description:
                    form.treatment_description += "\n\n" + med_text
                else:
                    form.treatment_description = med_text
        except:
            pass
            
        # Calculate claim amount based on charges
        try:
            charges = visit.charges.all()
            if charges:
                total = sum(charge.amount for charge in charges)
                form.claim_amount = total
                
                # Break down charges by type
                room_charges = sum(charge.amount for charge in charges if charge.charge_type == 'room_charge')
                if room_charges > 0:
                    form.room_rent_per_day = room_charges / max(1, form.expected_days_of_stay)
                
                # Operation theatre charges
                ot_charges = sum(charge.amount for charge in charges if charge.charge_type == 'procedure' or charge.charge_type == 'surgery')
                if ot_charges > 0:
                    form.ot_charges = ot_charges
                
                # Professional fees
                prof_fees = sum(charge.amount for charge in charges if charge.charge_type == 'consultation')
                if prof_fees > 0:
                    form.professional_fees = prof_fees
                    
                # Investigation charges
                investigation_charges = sum(charge.amount for charge in charges if charge.charge_type == 'lab_test' or charge.charge_type == 'imaging')
                if investigation_charges > 0:
                    form.investigation_charges = investigation_charges
                    
                # Medicine and consumables
                medicine_charges = sum(charge.amount for charge in charges if charge.charge_type == 'medication')
                if medicine_charges > 0:
                    form.medicine_consumables = medicine_charges
        except:
            pass
        
        # Save the form after updating all fields
        form.save()
        return form
    
    def auto_populate_from_previous_forms(self):
        """
        Auto-populate fields from previous insurance forms for the same patient,
        useful for recurring treatments
        """
        # Get patient from the visit
        patient = self.visit.patient
        
        # Find previous forms for this patient that were approved
        previous_forms = InsuranceForm.objects.filter(
            visit__patient=patient,
            status__in=['approved', 'payment_completed'],
        ).exclude(id=self.id).order_by('-created_at')
        
        # If no previous forms, return
        if not previous_forms.exists():
            return False
            
        # Get the most recent one
        prev_form = previous_forms.first()
        
        # Fields to copy if our current field is empty or null
        fields_to_copy = [
            'icd_code', 'past_history', 'proposed_line_of_treatment', 
            'route_of_drug_administration', 'treatment_type',
            'hospitalization_type', 'treating_doctor', 'doctor_registration_number'
        ]
        
        # Copy fields if they're empty in the current form but have values in the previous form
        updated = False
        for field in fields_to_copy:
            current_val = getattr(self, field)
            prev_val = getattr(prev_form, field)
            
            if (current_val is None or current_val == '' or current_val == []) and prev_val:
                setattr(self, field, prev_val)
                updated = True
                
        if updated:
            self.save()
            
        return updated
    
    def update_from_visit_data(self):
        """
        Update the form with the latest data from the visit
        Useful when visit details have been updated after form creation
        """
        visit = self.visit
        updated = False
        
        # Update diagnosis if it was changed
        if visit.diagnosis and visit.diagnosis != self.diagnosis:
            self.diagnosis = visit.diagnosis
            updated = True
            
        # Update treatment notes if they were changed
        if visit.treatment_notes and visit.treatment_notes != self.treatment_description:
            self.treatment_description = visit.treatment_notes
            updated = True
            
        # Update doctor if it was changed
        if visit.attending_doctor and visit.attending_doctor.profile:
            doctor_name = visit.attending_doctor.profile.name
            if doctor_name and doctor_name != self.treating_doctor:
                self.treating_doctor = doctor_name
                updated = True
        
        # Update charges/claim amount if they were changed
        try:
            total_charges = sum(charge.amount for charge in visit.charges.all())
            if total_charges > 0 and total_charges != self.claim_amount:
                self.claim_amount = total_charges
                updated = True
        except:
            pass
            
        if updated:
            self.save()
            
        return updated
