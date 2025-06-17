from rest_framework import serializers
from .models import Document, AccessRequest, NFCCard, NFCSession, EmergencyAccess
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class DocumentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = '__all__'
    
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email
        
    def validate_file(self, file):
        """
        Validate uploaded file - check file type and size
        """
        # Check file size (100MB limit)
        if file.size > 100 * 1024 * 1024:  # 100MB in bytes
            raise serializers.ValidationError("File size exceeds the maximum limit of 100MB.")
        
        # Get file extension
        file_name = file.name
        ext = os.path.splitext(file_name)[1].lower()
        
        # List of allowed file extensions
        allowed_extensions = [
            # Documents
            '.pdf', '.doc', '.docx', '.rtf', '.txt', '.xls', '.xlsx', '.ppt', '.pptx',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            # Others
            '.csv', '.json', '.xml'
        ]
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"File type {ext} is not supported. Allowed types: {', '.join(allowed_extensions)}")
            
        return file

class AccessRequestSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AccessRequest
        fields = '__all__'
        
    def get_doctor_name(self, obj):
        if hasattr(obj.doctor, 'profile'):
            return obj.doctor.profile.name
        return obj.doctor.email
        
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email

class NFCCardSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    
    class Meta:
        model = NFCCard
        fields = ['id', 'card_id', 'patient', 'patient_name', 'is_active', 'created_at', 'last_used']
        read_only_fields = ['card_id', 'created_at']
        lookup_field = 'card_id'
        extra_kwargs = {
            'url': {'lookup_field': 'card_id'}
        }
        
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email

class NFCSessionSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    accessed_by_name = serializers.SerializerMethodField()
    valid = serializers.SerializerMethodField()
    
    class Meta:
        model = NFCSession
        fields = ['id', 'patient', 'patient_name', 'accessed_by', 'accessed_by_name', 
                 'session_type', 'session_token', 'started_at', 'expires_at', 
                 'is_active', 'valid']
        read_only_fields = ['session_token', 'started_at', 'expires_at', 'session_type']
        
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email
    
    def get_accessed_by_name(self, obj):
        if obj.accessed_by and hasattr(obj.accessed_by, 'profile'):
            return obj.accessed_by.profile.name
        elif obj.accessed_by:
            return obj.accessed_by.email
        return None
        
    def get_valid(self, obj):
        return obj.is_valid

class EmergencyAccessSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    valid = serializers.SerializerMethodField()
    
    class Meta:
        model = EmergencyAccess
        fields = ['id', 'patient', 'patient_name', 'access_token', 'created_at',
                 'expires_at', 'last_accessed', 'access_count', 'valid']
        read_only_fields = ['access_token', 'created_at', 'expires_at', 
                           'last_accessed', 'access_count']
        
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email
        
    def get_valid(self, obj):
        return obj.is_valid

class EmergencyDocumentSerializer(serializers.ModelSerializer):
    """Serializer for emergency access to selected patient documents."""
    class Meta:
        model = Document
        fields = ['id', 'description', 'file', 'document_type', 'uploaded_at']
        read_only_fields = ['id', 'description', 'file', 'document_type', 'uploaded_at'] 