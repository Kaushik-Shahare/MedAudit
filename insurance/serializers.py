from rest_framework import serializers
from .models import InsuranceDocument, InsuranceType, InsurancePolicy, InsuranceForm
from ehr.models import PatientVisit
from account.serializers import UserDetailSerializer as UserMinimalSerializer


class InsuranceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceDocument
        fields = '__all__'


class InsuranceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceType
        fields = '__all__'


class InsurancePolicySerializer(serializers.ModelSerializer):
    insurance_type_name = serializers.ReadOnlyField(source='insurance_type.name')
    patient_email = serializers.ReadOnlyField(source='patient.email')
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_number', 'patient', 'patient_email', 'insurance_type',
            'insurance_type_name', 'provider', 'issuer', 'valid_from', 'valid_till',
            'sum_insured', 'premium_amount', 'is_active', 'is_valid', 'created_at', 'updated_at'
        ]


class InsurancePolicyDetailSerializer(serializers.ModelSerializer):
    insurance_type = InsuranceTypeSerializer(read_only=True)
    patient = UserMinimalSerializer(read_only=True)
    is_valid = serializers.ReadOnlyField()
    
    class Meta:
        model = InsurancePolicy
        fields = '__all__'


class InsurancePolicyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        exclude = ['created_at', 'updated_at']


class InsuranceFormSerializer(serializers.ModelSerializer):
    policy_number = serializers.ReadOnlyField(source='policy.policy_number')
    provider_name = serializers.ReadOnlyField(source='policy.provider')
    visit_number = serializers.ReadOnlyField(source='visit.visit_number')
    created_by_name = serializers.ReadOnlyField(source='created_by.email')
    patient_name = serializers.ReadOnlyField(source='visit.patient.email')
    
    class Meta:
        model = InsuranceForm
        fields = [
            'id', 'visit', 'visit_number', 'policy', 'policy_number', 'provider_name',
            'created_by', 'created_by_name', 'patient_name', 'claim_amount', 'status',
            'diagnosis', 'treatment_description', 'reference_number', 'is_ai_approved',
            'ai_confidence_score', 'is_cashless_claim', 'provider_type',
            # Patient condition and medical details
            'icd_code', 'presenting_complaints', 'past_history', 'clinical_findings',
            'proposed_line_of_treatment', 'investigation_details', 'route_of_drug_administration',
            # Hospital and treatment details
            'treatment_type', 'hospitalization_type', 'expected_days_of_stay',
            'admission_date', 'expected_discharge_date', 'treating_doctor',
            'doctor_registration_number', 'is_injury_related', 'injury_details',
            'is_maternity_related', 'date_of_delivery',
            # Financial details
            'room_rent_per_day', 'icu_charges_per_day', 'ot_charges',
            'professional_fees', 'medicine_consumables', 'investigation_charges', 'approved_amount',
            # Pre-authorization details
            'pre_authorization_reference', 'pre_authorization_date', 'pre_authorized_amount',
            'pre_auth_remarks',
            # Enhancement details
            'enhancement_requested', 'enhancement_amount', 'enhancement_reason',
            # Process dates
            'submission_date', 'approval_date', 'rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_ai_approved', 'ai_confidence_score', 
                           'ai_analysis', 'ai_processing_date', 'approval_date', 'submission_date']


class InsuranceFormDetailSerializer(serializers.ModelSerializer):
    policy = InsurancePolicySerializer(read_only=True)
    created_by_details = UserMinimalSerializer(source='created_by', read_only=True)
    treatment_type_display = serializers.CharField(source='get_treatment_type_display', read_only=True)
    hospitalization_type_display = serializers.CharField(source='get_hospitalization_type_display', read_only=True)
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InsuranceForm
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'is_ai_approved', 'ai_confidence_score', 
                           'ai_analysis', 'ai_processing_date', 'approval_date', 'submission_date']


class InsuranceFormCreateSerializer(serializers.ModelSerializer):
    auto_populate = serializers.BooleanField(default=False, write_only=True, 
        help_text="Set to true to auto-populate form data from the patient visit")
    
    class Meta:
        model = InsuranceForm
        fields = [
            # Automation options
            'auto_populate',
            # Basic form fields
            'visit', 'policy', 'status', 'is_cashless_claim', 'provider_type',
            # Medical details
            'diagnosis', 'treatment_description', 'icd_code', 'presenting_complaints',
            'past_history', 'clinical_findings', 'proposed_line_of_treatment', 
            'investigation_details', 'route_of_drug_administration',
            # Hospital and treatment details
            'treatment_type', 'hospitalization_type', 'expected_days_of_stay',
            'admission_date', 'expected_discharge_date', 'treating_doctor',
            'doctor_registration_number', 'is_injury_related', 'injury_details',
            'is_maternity_related', 'date_of_delivery',
            # Financial details
            'claim_amount', 'room_rent_per_day', 'icu_charges_per_day', 'ot_charges',
            'professional_fees', 'medicine_consumables', 'investigation_charges',
            # Pre-authorization details for cashless claims
            'pre_authorization_reference', 'pre_authorization_date', 'pre_authorized_amount',
            'pre_auth_remarks',
            # Reference number
            'reference_number'
        ]

    def validate(self, data):
        # Debug
        print("InsuranceFormCreateSerializer validate method called")
        print(f"Data received: {data}")
        
        # Extract and remove auto_populate flag if present
        auto_populate = data.pop('auto_populate', False)
        
        # Check if patient has active policy
        policy = data.get('policy')
        if policy and not policy.is_valid:
            raise serializers.ValidationError("The selected insurance policy is not currently valid")

        # Check if visit and policy belong to same patient
        visit = data.get('visit')
        if visit and policy:
            print(f"Visit patient: {visit.patient.id}, Policy patient: {policy.patient.id}")
            if visit.patient != policy.patient:
                raise serializers.ValidationError("The insurance policy does not belong to the patient of this visit")
        
        # Validate cashless claim requirements
        if data.get('is_cashless_claim', False):
            if not policy.insurance_type.is_cashless:
                raise serializers.ValidationError("This insurance policy type does not support cashless claims")
            
            if policy.insurance_type.requires_pre_authorization:
                # Check if pre-authorization details are provided for cashless claims
                if not data.get('pre_authorization_reference') and data.get('status') != 'draft':
                    raise serializers.ValidationError("Pre-authorization reference is required for cashless claims")
        
        # Set default status if not provided
        if 'status' not in data:
            data['status'] = 'draft'
            
        # For injury-related claims, ensure details are provided
        if data.get('is_injury_related', False) and not data.get('injury_details'):
            raise serializers.ValidationError("Injury details are required for injury-related claims")
            
        # For maternity-related claims, ensure delivery date is provided
        if data.get('is_maternity_related', False) and not data.get('date_of_delivery'):
            raise serializers.ValidationError("Date of delivery is required for maternity-related claims")
        
        # Store the auto_populate flag in the context for later use
        self.context['auto_populate'] = auto_populate
            
        return data
        
    def create(self, validated_data):
        print(f"Creating insurance form with data: {validated_data}")
        
        # Check if we need to auto-populate
        auto_populate = self.context.get('auto_populate', False)
        
        # If auto-populate is enabled and we only have minimal data, use the factory method
        if auto_populate and self.context.get('request'):
            visit = validated_data.get('visit')
            policy = validated_data.get('policy')
            created_by = self.context['request'].user
            is_cashless = validated_data.get('is_cashless_claim', False)
            
            if visit and policy and created_by:
                # Use the factory method to create a pre-populated form
                print(f"Auto-populating insurance form from visit data")
                instance = InsuranceForm.create_from_visit(
                    visit=visit,
                    policy=policy,
                    created_by=created_by,
                    is_cashless=is_cashless
                )
                
                # Update the instance with any explicitly provided values
                for field, value in validated_data.items():
                    if value is not None and field not in ['visit', 'policy', 'created_by', 'is_cashless_claim']:
                        setattr(instance, field, value)
                
                # Also, try to populate from previous forms if available
                instance.auto_populate_from_previous_forms()
                
                # Save the updated instance
                instance.save()
                
                print(f"Created and auto-populated insurance form with ID: {instance.id}")
                return instance
        
        # If auto-populate is disabled or we don't have sufficient data, use the normal flow
        instance = super().create(validated_data)
        print(f"Created insurance form with ID: {instance.id}")
        return instance


class AIApprovalSerializer(serializers.Serializer):
    """Serializer for AI-based approval of insurance forms."""
    is_approved = serializers.BooleanField()
    confidence_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    analysis = serializers.JSONField(required=False)
    approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
