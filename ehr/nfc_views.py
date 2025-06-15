from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import NFCCard, NFCSession, EmergencyAccess, Document, AccessRequest
from .serializers import (NFCCardSerializer, NFCSessionSerializer, 
                         EmergencyAccessSerializer, EmergencyDocumentSerializer, DocumentSerializer)
import uuid
from datetime import timedelta

User = get_user_model()

class NFCCardViewSet(viewsets.ModelViewSet):
    """ViewSet for managing NFC cards."""
    serializer_class = NFCCardSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return NFCCard.objects.all()
        if hasattr(self.request.user, 'profile') and self.request.user.user_type.name == 'Doctor':
            # Doctors can see NFC cards of patients they have approved access to
            approved_patients = AccessRequest.objects.filter(
                doctor=self.request.user, 
                is_approved=True
            ).values_list('patient', flat=True)
            return NFCCard.objects.filter(patient__in=approved_patients)
        return NFCCard.objects.filter(patient=self.request.user)
    
    def perform_create(self, serializer):
        # Check if user already has a card
        if NFCCard.objects.filter(patient=serializer.validated_data['patient']).exists():
            raise serializers.ValidationError("User already has an NFC card")
        serializer.save()
    
    @action(detail=True, methods=['post'], url_path='tap')
    def tap_nfc_card(self, request, pk=None):
        """Simulate tapping an NFC card to create a new session."""
        nfc_card = self.get_object()
        
        # Update last used timestamp
        nfc_card.last_used = timezone.now()
        nfc_card.save()
        
        # Create a new session (valid for 4 hours)
        session = NFCSession.objects.create(patient=nfc_card.patient)
        
        # Return session data
        serializer = NFCSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='emergency-access')
    def create_emergency_access(self, request, pk=None):
        """Create emergency access token for a patient's NFC card."""
        nfc_card = self.get_object()
        
        # Create emergency access token (valid for 24 hours)
        emergency = EmergencyAccess.objects.create(
            patient=nfc_card.patient,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Return emergency access data
        serializer = EmergencyAccessSerializer(emergency)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class NFCSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing NFC sessions."""
    serializer_class = NFCSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return NFCSession.objects.all()
        if hasattr(self.request.user, 'profile') and self.request.user.user_type.name == 'Doctor':
            # Doctors can see active sessions of patients they have approved access to
            approved_patients = AccessRequest.objects.filter(
                doctor=self.request.user, 
                is_approved=True
            ).values_list('patient', flat=True)
            return NFCSession.objects.filter(
                patient__in=approved_patients,
                is_active=True,
                expires_at__gt=timezone.now()
            )
        return NFCSession.objects.filter(patient=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='invalidate')
    def invalidate_session(self, request, pk=None):
        """Invalidate a session (log out)."""
        session = self.get_object()
        
        if request.user.is_staff or request.user == session.patient:
            session.invalidate()
            return Response({'status': 'session invalidated'}, status=status.HTTP_200_OK)
        
        return Response(
            {'detail': 'Not authorized to invalidate this session'}, 
            status=status.HTTP_403_FORBIDDEN
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_nfc_session(request):
    """Verify if an NFC session is valid."""
    session_token = request.query_params.get('token')
    
    if not session_token:
        return Response(
            {'detail': 'Session token is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        session = NFCSession.objects.get(session_token=session_token)
        
        if session.is_valid:
            # Return patient basic details
            data = {
                'valid': True,
                'patient_id': session.patient.id,
                'expires_at': session.expires_at
            }
            
            # Add patient name if available
            if hasattr(session.patient, 'profile'):
                data['patient_name'] = session.patient.profile.name
            
            return Response(data, status=status.HTTP_200_OK)
        
        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)
        
    except NFCSession.DoesNotExist:
        return Response({'valid': False}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def emergency_access(request, token):
    """Access emergency medical information with a token."""
    try:
        # Find valid emergency access token
        emergency = EmergencyAccess.objects.get(access_token=token)
        
        if not emergency.is_valid:
            return Response(
                {'detail': 'Emergency access token has expired'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Update access stats
        emergency.access_count += 1
        emergency.last_accessed = timezone.now()
        emergency.save()
        
        # Get emergency-accessible documents
        documents = Document.objects.filter(
            patient=emergency.patient,
            is_emergency_accessible=True
        )
        
        # Get basic patient data
        patient_data = {
            'patient_id': emergency.patient.id,
        }
        
        # Add profile data if available
        if hasattr(emergency.patient, 'profile'):
            profile = emergency.patient.profile
            patient_data.update({
                'name': profile.name,
                'date_of_birth': profile.date_of_birth,
                'phone_number': profile.phone_number
            })
        
        # Serialize documents for emergency view
        document_serializer = EmergencyDocumentSerializer(documents, many=True)
        
        # Combine patient data and documents
        response_data = {
            'patient': patient_data,
            'documents': document_serializer.data,
            'access_expires': emergency.expires_at
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except EmergencyAccess.DoesNotExist:
        return Response(
            {'detail': 'Invalid emergency access token'}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_nfc_qr_code(request):
    """Generate a QR code that emulates an NFC card tap."""
    from .utils import generate_nfc_qr_code
    
    try:
        # Get the user's NFC card
        nfc_card = NFCCard.objects.get(patient=request.user)
        
        if not nfc_card.is_active:
            return Response(
                {'detail': 'Your NFC card is not active. Please contact admin.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate QR code
        qr_code = generate_nfc_qr_code(nfc_card)
        
        return Response({
            'qr_code': qr_code,
            'expires_in': '4 hours'
        }, status=status.HTTP_200_OK)
        
    except NFCCard.DoesNotExist:
        return Response(
            {'detail': 'You do not have an NFC card assigned.'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_emergency_qr_code(request):
    """Generate an emergency QR code for the patient."""
    from .utils import generate_emergency_qr_code
    
    # Only patients can generate emergency codes
    if not hasattr(request.user, 'profile') or request.user.user_type.name != 'Patient':
        return Response(
            {'detail': 'Only patients can generate emergency codes.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Generate emergency QR code
    qr_code = generate_emergency_qr_code(request.user)
    
    return Response({
        'qr_code': qr_code,
        'expires_in': '24 hours'
    }, status=status.HTTP_200_OK)
