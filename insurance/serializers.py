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
            'ai_confidence_score', 'is_cashless_claim', 'pre_authorization_reference',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_ai_approved', 'ai_confidence_score']


class InsuranceFormDetailSerializer(serializers.ModelSerializer):
    policy = InsurancePolicySerializer(read_only=True)
    
    class Meta:
        model = InsuranceForm
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class InsuranceFormCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceForm
        fields = [
            'visit', 'policy', 'diagnosis', 'treatment_description', 
            'claim_amount', 'is_cashless_claim', 'pre_authorization_reference',
            'pre_authorization_date', 'pre_authorized_amount'
        ]

    def validate(self, data):
        # Check if patient has active policy
        policy = data.get('policy')
        if policy and not policy.is_valid:
            raise serializers.ValidationError("The selected insurance policy is not currently valid")

        # Check if visit and policy belong to same patient
        visit = data.get('visit')
        if visit and policy and visit.patient != policy.patient:
            raise serializers.ValidationError("The insurance policy does not belong to the patient of this visit")
            
        return data


class AIApprovalSerializer(serializers.Serializer):
    """Serializer for AI-based approval of insurance forms."""
    is_approved = serializers.BooleanField()
    confidence_score = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    analysis = serializers.JSONField(required=False)
    approved_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
