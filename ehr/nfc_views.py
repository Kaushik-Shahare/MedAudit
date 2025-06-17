from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from MedAudit.exception_handler import custom_exception_handler
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
    lookup_field = 'card_id'
    
    def get_queryset(self):
        try:
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
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in NFCCardViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error to prevent breaking page loads
            # The actual exception will be handled by DRF's exception handler
            return NFCCard.objects.none()
    
    def perform_create(self, serializer):
        try:
            # Check if user already has a card
            # Only Admin can create NFC cards for patients
            if not self.request.user.is_staff:
                raise serializers.ValidationError("Only admin can create NFC cards for patients")
            # Ensure the patient does not already have an NFC card
            if 'patient' not in serializer.validated_data:
                raise serializers.ValidationError("Patient is required to create an NFC card")
            # Check if the patient already has an NFC card
            if NFCCard.objects.filter(patient=serializer.validated_data['patient']).exists():
                raise serializers.ValidationError("User already has an NFC card")
            serializer.save()
        except serializers.ValidationError:
            # Re-raise validation errors to be handled by DRF
            raise
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in NFCCardViewSet.perform_create: {str(e)}")
            # Raise as validation error to be handled by DRF
            raise serializers.ValidationError(f"An unexpected error occurred: {str(e)}")
    
class NFCSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing NFC sessions."""
    serializer_class = NFCSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Override permissions to allow unauthenticated access for retrieving session details.
        This is needed for emergency access scenarios where users aren't logged in.
        """
        if self.action == 'retrieve':
            # Allow anyone to retrieve session details by ID
            return []
        return super().get_permissions()
    
    def get_queryset(self):
        try:
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
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in NFCSessionViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error
            return NFCSession.objects.none()
    
    @action(detail=True, methods=['post'], url_path='invalidate')
    def invalidate_session(self, request, pk=None):
        """Invalidate a session (log out)."""
        try:
            session = self.get_object()
            
            if request.user.is_staff or request.user == session.patient:
                session.invalidate()
                return Response({
                    'status': True,
                    'code': status.HTTP_200_OK,
                    'message': 'Session invalidated successfully'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'status': False,
                'code': status.HTTP_403_FORBIDDEN,
                'message': 'Not authorized to invalidate this session'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in invalidate_session: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_nfc_session(request):
    """Verify if an NFC session is valid."""
    try:
        session_token = request.query_params.get('token')
        
        if not session_token:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Session token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            session = NFCSession.objects.get(session_token=session_token)
            
            if session.is_valid:
                # Return patient basic details and session info
                data = {
                    'valid': True,
                    'patient_id': session.patient.id,
                    'expires_at': session.expires_at,
                    'session_type': session.session_type,
                    'documents_endpoint': f'/api/ehr/nfc/session/{session.session_token}/documents/'
                }
                
                # Add patient name if available
                if hasattr(session.patient, 'profile'):
                    data['patient_name'] = session.patient.profile.name
                
                return Response({
                    'status': True,
                    'code': status.HTTP_200_OK,
                    'data': data,
                    'message': 'Session verified successfully'
                }, status=status.HTTP_200_OK)
            
            return Response({
                'status': False,
                'code': status.HTTP_401_UNAUTHORIZED,
                'message': 'Session has expired or is no longer valid',
                'data': {'valid': False}
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        except NFCSession.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Session not found',
                'data': {'valid': False}
            }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as exc:
        import logging
        logger = logging.getLogger('django.request')
        logger.error(f"Error in verify_nfc_session: {str(exc)}")
        
        # Get context for the custom exception handler
        context = {'request': request, 'view': None}
        response = custom_exception_handler(exc, context)
        return response

@api_view(['GET'])
@permission_classes([AllowAny])
def emergency_access(request, token):
    """Access emergency medical information with a token."""
    try:
        try:
            # Find valid emergency access token
            emergency = EmergencyAccess.objects.get(access_token=token)
            
            if not emergency.is_valid:
                return Response({
                    'status': False,
                    'code': status.HTTP_401_UNAUTHORIZED,
                    'message': 'Emergency access token has expired'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
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
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Emergency access granted',
                'data': response_data
            }, status=status.HTTP_200_OK)
            
        except EmergencyAccess.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Invalid emergency access token'
            }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as exc:
        import logging
        logger = logging.getLogger('django.request')
        logger.error(f"Error in emergency_access: {str(exc)}")
        
        # Get context for the custom exception handler
        context = {'request': request, 'view': None}
        response = custom_exception_handler(exc, context)
        return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_nfc_qr_code(request):
    """Generate a QR code that emulates an NFC card tap."""
    try:
        from .utils import generate_nfc_qr_code
        
        try:
            # Get the user's NFC card
            nfc_card = NFCCard.objects.get(patient=request.user)
            
            if not nfc_card.is_active:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Your NFC card is not active. Please contact admin.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate QR code
            qr_code = generate_nfc_qr_code(nfc_card)
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'QR code generated successfully',
                'data': {
                    'qr_code': qr_code,
                    'expires_in': '4 hours'
                }
            }, status=status.HTTP_200_OK)
            
        except NFCCard.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'You do not have an NFC card assigned.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as exc:
        import logging
        logger = logging.getLogger('django.request')
        logger.error(f"Error in generate_nfc_qr_code: {str(exc)}")
        
        # Get the context from the request for the custom exception handler
        context = {'request': request, 'view': None}
        response = custom_exception_handler(exc, context)
        return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_emergency_qr_code(request):
    """Generate an emergency QR code for the patient."""
    try:
        from .utils import generate_emergency_qr_code
        
        # Only patients can generate emergency codes
        if not hasattr(request.user, 'profile') or request.user.user_type.name != 'Patient':
            return Response({
                'status': False,
                'code': status.HTTP_403_FORBIDDEN,
                'message': 'Only patients can generate emergency codes.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate emergency QR code
        qr_code = generate_emergency_qr_code(request.user)
        
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'message': 'Emergency QR code generated successfully',
            'data': {
                'qr_code': qr_code,
                'expires_in': '24 hours'
            }
        }, status=status.HTTP_200_OK)
    except Exception as exc:
        import logging
        logger = logging.getLogger('django.request')
        logger.error(f"Error in generate_emergency_qr_code: {str(exc)}")
        
        # Get context for the custom exception handler
        context = {'request': request, 'view': None}
        response = custom_exception_handler(exc, context)
        return response

@api_view(['POST', 'GET'])  # Support both POST and GET for convenience
@permission_classes([AllowAny])  # Allow anyone to tap an NFC card
def tap_nfc_card_public(request, card_id):
    """
    Universal API endpoint for tapping an NFC card.
    
    - For anonymous users: Creates an emergency access session (limited to emergency documents)
    - For doctors/admin: Creates a full access session (all patient documents)
    - For patient: Creates a self-access session
    - For other logged-in users: Creates an emergency session
    
    All accesses are logged for security and auditing purposes.
    Sessions last 4 hours by default.
    """
    try:
        # Log the request details for debugging
        import logging
        logger = logging.getLogger('django.request')
        
        # Try to get the NFCard
        try:
            nfc_card = NFCCard.objects.get(card_id=card_id)
        except NFCCard.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': f'NFC card with card_id={card_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update last used timestamp
        nfc_card.last_used = timezone.now()
        nfc_card.save()
        
        # Default to anonymous emergency access
        session_type = 'anonymous'
        accessed_by = None
        
        # Check if there's an authenticated user and determine access type
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            accessed_by = request.user
            logger.info(f"Authenticated NFC tap: User={request.user.email}, Card={card_id}")
            
            # Determine access type based on user role
            if request.user.is_staff:
                session_type = 'doctor'  # Staff members get full access
                logger.info(f"Admin full access granted: {request.user.email}")
                
            elif hasattr(request.user, 'user_type') and request.user.user_type:
                if request.user.user_type.name == 'Doctor':
                    session_type = 'doctor'  # Doctors get full access
                    logger.info(f"Doctor full access: {request.user.email}")
                elif request.user == nfc_card.patient:
                    session_type = 'patient'  # Patients accessing their own data
                    logger.info(f"Patient self-access: {request.user.email}")
                else:
                    session_type = 'emergency'  # Other users get emergency access
                    logger.info(f"Emergency access: {request.user.email} (type: {request.user.user_type.name})")
            else:
                # User without a specified type
                if request.user == nfc_card.patient:
                    session_type = 'patient'  # Patient self-access
                else:
                    session_type = 'emergency'  # Emergency access for others
        else:
            # Anonymous user access (no login)
            logger.info(f"Anonymous emergency access to card: {card_id}")
        
        # Create the session with the determined access level
        session = NFCSession.objects.create(
            patient=nfc_card.patient,
            accessed_by=accessed_by,
            session_type=session_type
        )
        
        # Return session data along with what kind of access was granted
        serializer = NFCSessionSerializer(session)
        
        # Build response with appropriate access level information
        response_data = {
            'status': True,
            'code': status.HTTP_201_CREATED,
            'message': f'NFC card tapped successfully, {session_type} access granted',
            'data': {
                'session': serializer.data,
                'access_type': session_type,
                'documents_url': f'/api/ehr/nfc/session/{session.session_token}/documents/',
                'expires_at': session.expires_at,
                'access_level': 'Full access' if session_type in ['doctor', 'patient'] else 'Emergency access only'
            }
        }
        
        # Add patient profile information that's always accessible
        if hasattr(nfc_card.patient, 'profile'):
            profile = nfc_card.patient.profile
            response_data['data']['patient'] = {
                'name': getattr(profile, 'name', None),
                'date_of_birth': getattr(profile, 'date_of_birth', None),
                'phone_number': getattr(profile, 'phone_number', None)
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
        
    except Exception as exc:
        import logging
        import traceback
        logger = logging.getLogger('django.request')
        logger.error(f"Error in NFC tap: {str(exc)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return Response({
            'status': False,
            'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': 'An error occurred while processing the NFC tap',
            'error': str(exc)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
