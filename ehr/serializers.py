from rest_framework import serializers
from .models import Document, AccessRequest, NFCCard, NFCSession, EmergencyAccess, PatientVisit, VisitCharge, SessionActivity
from django.contrib.auth import get_user_model
import os
from account.serializers import UserDetailSerializer

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
    accessed_by = UserDetailSerializer(read_only=True)
    patient = UserDetailSerializer(read_only=True)
    valid = serializers.SerializerMethodField()
    
    class Meta:
        model = NFCSession
        fields = ['id', 'patient', 'accessed_by',
                 'session_type', 'session_token', 'started_at', 'expires_at', 
                 'is_active', 'valid', 'visit']
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

class VisitChargeSerializer(serializers.ModelSerializer):
    added_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitCharge
        fields = ['id', 'description', 'amount', 'charge_type', 'date_added', 
                 'added_by', 'added_by_name', 'insurance_covered'
                 ]
        read_only_fields = ['date_added']
    
    def get_added_by_name(self, obj):
        if obj.added_by and hasattr(obj.added_by, 'profile'):
            return obj.added_by.profile.name
        elif obj.added_by:
            return obj.added_by.email
        return None

class VisitChargeCreateSerializer(serializers.ModelSerializer):
    """Used for creating new charges"""
    class Meta:
        model = VisitCharge
        fields = ['description', 'amount', 'charge_type', 'insurance_covered']

class PatientVisitListSerializer(serializers.ModelSerializer):
    """Serializer for listing patient visits with minimal information"""
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientVisit
        fields = ['id', 'visit_number', 'patient', 'patient_name', 'check_in_time', 
                 'check_out_time', 'status', 'visit_type', 'attending_doctor', 'doctor_name',
                 'total_amount', 'payment_status', 'duration'
                 ]
    
    def get_patient_name(self, obj):
        if hasattr(obj.patient, 'profile'):
            return obj.patient.profile.name
        return obj.patient.email
    
    def get_doctor_name(self, obj):
        if obj.attending_doctor and hasattr(obj.attending_doctor, 'profile'):
            return obj.attending_doctor.profile.name
        elif obj.attending_doctor:
            return obj.attending_doctor.email
        return None
        
    def get_duration(self, obj):
        if obj.check_out_time and obj.check_in_time:
            duration = obj.check_out_time - obj.check_in_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return None

class PatientVisitDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a patient visit including related documents and charges"""
    patient = UserDetailSerializer(read_only=True)
    attending_doctor = UserDetailSerializer(read_only=True)
    created_by = UserDetailSerializer(read_only=True)
    charges = VisitChargeSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    sessions = NFCSessionSerializer(many=True, read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientVisit
        fields = '__all__'
        
    def get_duration(self, obj):
        if obj.check_out_time and obj.check_in_time:
            duration = obj.check_out_time - obj.check_in_time
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return None

class PatientVisitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new patient visits"""
    session_token = serializers.CharField(required=True, write_only=True)  # Only accept session_token
    
    class Meta:
        model = PatientVisit
        # fields = ['patient', 'visit_type', 'reason_for_visit', 'attending_doctor', 'session_token']
        fields = "__all__"
        
    def validate(self, attrs):
        # Get session_token and check if it's in query params if not in body
        session_token = attrs.get('session_token')
        if not session_token:
            request = self.context.get('request')
            if request:
                session_token = request.query_params.get('session_token')
                if session_token:
                    attrs['session_token'] = session_token
        
        # Still no session token found
        if not session_token:
            raise serializers.ValidationError({
                "session_token": "A valid session_token is required when creating visits"
            })
            
        try:
            # Get session by token only
            session = NFCSession.objects.get(session_token=session_token)
                
            if not session.is_valid:
                raise serializers.ValidationError({
                    "session_token": "The provided NFC session is not valid or has expired"
                })
            
            # Ensure session patient matches visit patient
            if session.patient.id != attrs['patient'].id:
                raise serializers.ValidationError({
                    "session_token": "The NFC session does not belong to this patient"
                })
                
            # Store the actual session object for use in create method
            attrs['_session'] = session

            
        except NFCSession.DoesNotExist:
            raise serializers.ValidationError({
                "session_token": "Invalid session token provided"
            })

        # Validate that doctor_id is valid if provided
        if 'attending_doctor' in attrs:
            doctor_id = attrs['attending_doctor'].id
            print(f"Validating doctor_id: {doctor_id}")
            try:
                doctor = User.objects.filter(id=doctor_id).first()
                if not doctor or not doctor.user_type or doctor.user_type.name != 'Doctor':
                    raise serializers.ValidationError({
                        "attending_doctor": "The specified doctor does not exist or is not a valid doctor"
                    })
            except Exception as e:
                # Catch any exceptions during validation to ensure we return a 400 error
                raise serializers.ValidationError({
                    "attending_doctor": "Error validating doctor: The doctor may not exist or have the correct role"
                })
                
        return attrs
        
    def create(self, validated_data):
        """
        Remove session_token from validated_data before creating PatientVisit instance
        as it's not a field in the PatientVisit model.
        """
        import logging
        logger = logging.getLogger('django.request')
        
        # Extract the session_token and session object before creating the visit
        session_token = validated_data.pop('session_token', None)
        session = validated_data.pop('_session', None)
        
        try:
            # Create the PatientVisit instance without the creating_session field
            instance = super().create(validated_data)
            
            # If we have a session, try to link it to the visit using raw SQL if needed
            if session:
                try:
                    # Try the standard Django ORM approach first
                    instance.creating_session = session
                    instance.save()
                except Exception as orm_error:
                    logger.warning(f"Could not set creating_session via ORM: {str(orm_error)}")
                    
                    # The field might not exist in the database yet, 
                    # but we still want the session to be linked to the visit
                    session.visit = instance
                    session.save()
                    
                    logger.info(f"Session {session.id} linked to visit {instance.id} via session.visit")
                    return instance
                
                # If we got here, ORM update succeeded, now update session too
                session.visit = instance
                session.save()
                logger.info(f"Session {session.id} linked to visit {instance.id} bidirectionally")
                
            return instance
                
        except Exception as e:
            logger.error(f"Error in PatientVisitCreateSerializer.create: {str(e)}")
            raise serializers.ValidationError(f"Error creating visit: {str(e)}")

class PatientVisitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating patient visits"""
    class Meta:
        model = PatientVisit
        fields = ['status', 'attending_doctor', 'diagnosis', 'treatment_notes', 
                 'follow_up_required', 'follow_up_date', 'total_amount', 
                 'insurance_coverage', 'payment_status']

class SessionActivitySerializer(serializers.ModelSerializer):
    """Serializer for session activity logs"""
    performed_by_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    visit_number = serializers.SerializerMethodField()
    document_description = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionActivity
        fields = [
            'id', 'session', 'performed_by', 'performed_by_name', 
            'activity_type', 'timestamp', 'visit', 'visit_number',
            'document', 'document_description', 'details',
            'patient_name'
        ]
    
    def get_performed_by_name(self, obj):
        if obj.performed_by and hasattr(obj.performed_by, 'profile'):
            return obj.performed_by.profile.name
        elif obj.performed_by:
            return obj.performed_by.email
        return None
    
    def get_patient_name(self, obj):
        patient = None
        if obj.visit:
            patient = obj.visit.patient
        elif obj.document:
            patient = obj.document.patient
        elif obj.session:
            patient = obj.session.patient
            
        if patient and hasattr(patient, 'profile'):
            return patient.profile.name
        elif patient:
            return patient.email
        return None
    
    def get_visit_number(self, obj):
        if obj.visit:
            return obj.visit.visit_number
        return None
    
    def get_document_description(self, obj):
        if obj.document:
            return obj.document.description
        return None
