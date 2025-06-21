from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import PatientVisit, VisitCharge, Document, NFCSession, SessionActivity
from .serializers import (
    PatientVisitListSerializer,
    PatientVisitDetailSerializer,
    PatientVisitCreateSerializer, 
    PatientVisitUpdateSerializer,
    VisitChargeSerializer,
    VisitChargeCreateSerializer,
    DocumentSerializer,
    SessionActivitySerializer
)
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()

class PatientVisitViewSet(viewsets.ModelViewSet):
    """ViewSet for managing patient hospital visits."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PatientVisitCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PatientVisitUpdateSerializer
        elif self.action == 'retrieve':
            return PatientVisitDetailSerializer
        return PatientVisitListSerializer
    
    def get_queryset(self):
        try:
            user = self.request.user
            if user.is_staff:
                return PatientVisit.objects.all().select_related('patient', 'attending_doctor', 'created_by')
                
            elif hasattr(user, 'user_type'):
                if user.user_type.name == 'Patient':
                    return PatientVisit.objects.filter(patient=user).select_related('patient', 'attending_doctor', 'created_by')
                
                elif user.user_type.name == 'Doctor':
                    # Doctors can only see visits where they are the attending doctor
                    # or visits linked to their active NFC sessions
                    doctor_visits = PatientVisit.objects.filter(attending_doctor=user)
                    session_visits = PatientVisit.objects.filter(
                        sessions__accessed_by=user,
                        sessions__is_active=True
                    )
                    return (doctor_visits | session_visits).distinct().select_related('patient', 'attending_doctor', 'created_by')
                    
            return PatientVisit.objects.none()
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientVisitViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error
            return PatientVisit.objects.none()
    
    def perform_create(self, serializer):
        """Set the created_by field when creating a visit."""
        import logging
        logger = logging.getLogger('django.request')
        
        user = self.request.user
        
        # Only Admin can create visits
        if not user.is_staff:
            logger.warning(f"Non-staff user {user.id} attempted to create visit")
            raise PermissionDenied("Only staff can create visits")

        try:
            # Create the visit (session handling is now done in serializer)
            visit = serializer.save(created_by=user)
            
            # Log the activity if we can find the session from request data
            session_token = self.request.data.get('session_token') or self.request.query_params.get('session_token')
            if session_token:
                try:
                    from .models import NFCSession, SessionActivity
                    session = NFCSession.objects.get(session_token=session_token)
                    
                    # Log this activity
                    SessionActivity.log_activity(
                        session=session,
                        user=user,
                        activity_type='create_visit',
                        visit=visit,
                        details=f"Created visit of type {visit.visit_type}"
                    )
                except NFCSession.DoesNotExist:
                    logger.warning(f"Could not find session with token {session_token} for activity logging")
            
            return visit
        except Exception as e:
            logger.error(f"Error creating visit: {str(e)}")
            raise ValidationError({"error": f"Error creating visit: {str(e)}"})
    
    def update(self, request, *args, **kwargs):
        """Update a visit with additional validation."""
        user = self.request.user
        visit = self.get_object()
        
        # Check if the user can edit this visit - with improved error messages
        can_edit, error_message = visit.can_be_edited_by(user)
        if not can_edit:
            if error_message and "active NFC session" in error_message:
                raise ValidationError({
                    "session_token": error_message,
                    "error_code": "expired_session"
                })
            else:
                raise PermissionDenied(error_message or 'You do not have permission to edit this visit')
        
        # If we have a session token, log this activity
        session_token = request.data.get('session_token') or request.query_params.get('session_token')
        if session_token:
            try:
                session = NFCSession.objects.get(session_token=session_token)
                
                # Validate session
                is_valid, error_code, error_message = session.validate_session()
                if not is_valid:
                    raise ValidationError({
                        "session_token": error_message,
                        "error_code": error_code
                    })
                
                # Log this activity  
                SessionActivity.log_activity(
                    session=session,
                    user=user,
                    activity_type='update_visit',
                    visit=visit,
                    details=f"Updated visit data"
                )
            except NFCSession.DoesNotExist:
                # Not raising error here since we validated user has permission some other way
                pass
        
        return super().update(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Get details of a visit with additional validation."""
        user = self.request.user
        visit = self.get_object()
        
        # For non-staff users who aren't the patient, check session permissions
        if not user.is_staff and user != visit.patient and user != visit.attending_doctor:
            if hasattr(user, 'user_type') and user.user_type.name == 'Doctor':
                if not visit.has_active_session_for_user(user):
                    raise ValidationError({
                        "session_token": "Doctors need an active NFC session to view visit details. Please generate a new session by tapping the NFC card.", 
                        "error_code": "expired_session"
                    })
        
        # If we have a session token, log this view activity
        session_token = request.query_params.get('session_token')
        if session_token:
            try:
                session = NFCSession.objects.get(session_token=session_token)
                
                # Validate session
                is_valid, error_code, error_message = session.validate_session()
                if not is_valid:
                    raise ValidationError({
                        "session_token": error_message,
                        "error_code": error_code
                    })
                
                # Log this activity  
                SessionActivity.log_activity(
                    session=session,
                    user=user,
                    activity_type='view_visit',
                    visit=visit,
                    details=f"Viewed visit details"
                )
            except NFCSession.DoesNotExist:
                # Not raising error here since we validated user has permission some other way
                pass
        
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """Complete a visit and checkout the patient."""
        visit = self.get_object()
        user = request.user
        
        # Check if the user can edit this visit - with improved error messages
        can_edit, error_message = visit.can_be_edited_by(user)
        if not can_edit:
            if error_message and "active NFC session" in error_message:
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': error_message,
                    'error_code': 'expired_session'
                }, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Only staff or attending doctor can checkout a patient'
                }, status=status.HTTP_403_FORBIDDEN)
            
        if visit.status == 'completed':
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'This visit has already been completed'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # If we have a session token, validate it
        session_token = request.data.get('session_token')
        session = None
        
        if session_token:
            try:
                session = NFCSession.objects.get(session_token=session_token)
                
                # Validate session
                is_valid, error_code, error_message = session.validate_session()
                if not is_valid:
                    return Response({
                        'status': False,
                        'code': status.HTTP_400_BAD_REQUEST,
                        'message': error_message,
                        'error_code': error_code
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except NFCSession.DoesNotExist:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Invalid session token provided',
                    'error_code': 'invalid_token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        # Perform checkout operations - now with the user for activity logging
        visit.checkout(checked_out_by=user)
        
        # Log this activity if we have a session
        if session:
            SessionActivity.log_activity(
                session=session, 
                user=user,
                activity_type='checkout_visit',
                visit=visit,
                details=f"Checked out patient visit"
            )
        
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'message': 'Patient has been checked out successfully',
            'data': PatientVisitDetailSerializer(visit).data
        })
    
    @action(detail=True, methods=['post'])
    def add_charge(self, request, pk=None):
        """Add a charge/billing item to the visit."""
        visit = self.get_object()
        
        # Only allow staff to add charges
        if not request.user.is_staff:
            return Response({
                'status': False,
                'code': status.HTTP_403_FORBIDDEN,
                'message': 'Only staff can add charges to a visit'
            }, status=status.HTTP_403_FORBIDDEN)
            
        serializer = VisitChargeCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Add the charge
            charge = serializer.save(
                visit=visit, 
                added_by=request.user
            )
            
            # Update the total amount
            total_charges = visit.charges.aggregate(total=Sum('amount'))['total'] or 0
            visit.total_amount = total_charges
            visit.save()
            
            return Response({
                'status': True,
                'code': status.HTTP_201_CREATED,
                'message': 'Charge added successfully',
                'data': VisitChargeSerializer(charge).data
            }, status=status.HTTP_201_CREATED)
            
        return Response({
            'status': False,
            'code': status.HTTP_400_BAD_REQUEST,
            'message': 'Invalid charge data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def charges(self, request, pk=None):
        """List all charges for a visit."""
        visit = self.get_object()
        charges = visit.charges.all()
        
        serializer = VisitChargeSerializer(charges, many=True)
        
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None):
        """Associate a document with this visit."""
        visit = self.get_object()
        
        # Validate document_id in request
        document_id = request.data.get('document_id')
        if not document_id:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'document_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            document = Document.objects.get(id=document_id)
            
            # Check if document belongs to the same patient
            if document.patient != visit.patient:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'The document does not belong to this patient'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Associate document with visit
            document.visit = visit
            document.save()
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Document added to visit successfully',
                'data': DocumentSerializer(document).data
            })
            
        except Document.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Document not found'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='upload-document')
    def upload_document(self, request, pk=None):
        """Upload a document and associate it with this visit."""
        visit = self.get_object()
        
        # Validate file in request
        if 'file' not in request.FILES:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'File is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        file = request.FILES['file']
        
        # Create the document instance
        document = Document.objects.create(
            patient=visit.patient,
            visit=visit,
            file=file,
            uploaded_by=request.user
        )
        
        return Response({
            'status': True,
            'code': status.HTTP_201_CREATED,
            'message': 'Document uploaded successfully',
            'data': DocumentSerializer(document).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_session(self, request, pk=None):
        """Associate an NFC session with this visit."""
        visit = self.get_object()
        user = request.user
        
        # Validate session_token in request
        session_token = request.data.get('session_token')
        if not session_token:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'session_token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get session by token only
            session = NFCSession.objects.get(session_token=session_token)
            
            # Validate session
            is_valid, error_code, error_message = session.validate_session()
            if not is_valid:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': error_message,
                    'error_code': error_code
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if session belongs to the same patient
            if session.patient != visit.patient:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'The session does not belong to this patient'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user is authorized to link this session
            if not user.is_staff and user != visit.attending_doctor and user != visit.patient:
                # If doctor is not the attending doctor, check if they accessed the session
                if hasattr(user, 'user_type') and user.user_type.name == 'Doctor' and session.accessed_by != user:
                    return Response({
                        'status': False,
                        'code': status.HTTP_403_FORBIDDEN,
                        'message': 'You are not authorized to link this session to the visit'
                    }, status=status.HTTP_403_FORBIDDEN)
                
            # Associate session with visit
            session.visit = visit
            session.save()
            
            # If the user is a doctor and not the attending doctor, set them as the attending doctor
            if hasattr(user, 'user_type') and user.user_type.name == 'Doctor' and visit.attending_doctor is None:
                visit.attending_doctor = user
                visit.save()
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Session added to visit successfully'
            })
            
        except NFCSession.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def validate_session(self, request):
        """
        Validate a session token and return its status and associated information.
        This endpoint can be used to check if a session is still valid before using it.
        """
        session_token = request.data.get('session_token')
        if not session_token:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'session_token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get session by token
            session = NFCSession.objects.get(session_token=session_token)
            
            # Validate session
            is_valid, error_code, error_message = session.validate_session()
            
            # Basic session information
            session_data = {
                'session_id': session.id,
                'patient_id': session.patient_id,
                'session_type': session.session_type,
                'started_at': session.started_at,
                'expires_at': session.expires_at,
                'is_active': session.is_active,
                'is_valid': is_valid,
            }
            
            if session.visit:
                session_data['visit_id'] = session.visit.id
                session_data['visit_number'] = session.visit.visit_number
            
            if session.accessed_by:
                session_data['accessed_by_id'] = session.accessed_by.id
                if hasattr(session.accessed_by, 'profile'):
                    session_data['accessed_by_name'] = session.accessed_by.profile.name
            
            if not is_valid:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': error_message,
                    'error_code': error_code,
                    'session': session_data
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Log this validation check
            SessionActivity.log_activity(
                session=session,
                user=request.user,
                activity_type='validate_session',
                visit=session.visit,
                details=f"Validated session token"
            )
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Session is valid',
                'session': session_data
            })
            
        except NFCSession.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Invalid session token',
                'error_code': 'invalid_token'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def extend_session(self, request):
        """
        Extend the validity period of a session token.
        This endpoint can be used when a session is about to expire but the user is still active.
        """
        session_token = request.data.get('session_token')
        if not session_token:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'session_token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Optional hours parameter, default to 4 hours
        try:
            hours = int(request.data.get('hours', 4))
            if hours <= 0 or hours > 24:
                raise ValueError("Hours must be between 1 and 24")
        except ValueError:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid hours value. Must be between 1 and 24.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get session by token
            session = NFCSession.objects.get(session_token=session_token)
            
            # Check if session is still active (even if expired)
            if not session.is_active:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Cannot extend an inactive session',
                    'error_code': 'inactive_session'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Extend the session
            session.expires_at = timezone.now() + timedelta(hours=hours)
            session.save()
            
            # Log this extension
            SessionActivity.log_activity(
                session=session,
                user=request.user,
                activity_type='extend_session',
                visit=session.visit,
                details=f"Extended session validity by {hours} hours"
            )
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': f'Session extended by {hours} hours',
                'expires_at': session.expires_at
            })
            
        except NFCSession.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Invalid session token',
                'error_code': 'invalid_token'
            }, status=status.HTTP_404_NOT_FOUND)

class VisitChargeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing visit charges/billing."""
    serializer_class = VisitChargeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        try:
            user = self.request.user
            if user.is_staff:
                return VisitCharge.objects.all()
                
            elif hasattr(user, 'user_type'):
                if user.user_type.name == 'Patient':
                    # Patients can see charges for their visits
                    return VisitCharge.objects.filter(visit__patient=user)
                
                elif user.user_type.name == 'Doctor':
                    # Doctors can see charges for their patients' visits
                    return VisitCharge.objects.filter(visit__attending_doctor=user)
                    
            return VisitCharge.objects.none()
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in VisitChargeViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error
            return VisitCharge.objects.none()
    
    def perform_create(self, serializer):
        """Set the added_by field when creating a charge."""
        serializer.save(added_by=self.request.user)

class SessionActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing session activity logs."""
    serializer_class = SessionActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter activities based on user role and permissions."""
        try:
            user = self.request.user
            
            # Admin can see all activities
            if user.is_staff:
                return SessionActivity.objects.all().select_related(
                    'session', 'performed_by', 'visit', 'document'
                )
                
            elif hasattr(user, 'user_type'):
                if user.user_type.name == 'Patient':
                    # Patients can see activities related to their sessions/visits/documents
                    return SessionActivity.objects.filter(
                        Q(session__patient=user) | 
                        Q(visit__patient=user) | 
                        Q(document__patient=user)
                    ).select_related('session', 'performed_by', 'visit', 'document')
                
                elif user.user_type.name == 'Doctor':
                    # Doctors can see activities where they are the performer or the attending doctor
                    return SessionActivity.objects.filter(
                        Q(performed_by=user) | 
                        Q(visit__attending_doctor=user) | 
                        Q(session__accessed_by=user)
                    ).select_related('session', 'performed_by', 'visit', 'document')
                    
            return SessionActivity.objects.none()
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in SessionActivityViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error
            return SessionActivity.objects.none()
            
    def get_session_activities(self, session_token):
        """Helper method to get activities for a specific session."""
        try:
            session = NFCSession.objects.get(session_token=session_token)
            return SessionActivity.objects.filter(session=session).order_by('-timestamp')
        except NFCSession.DoesNotExist:
            return SessionActivity.objects.none()
            
    @action(detail=False, methods=['get'])
    def by_session(self, request):
        """Get activities for a specific session token."""
        session_token = request.query_params.get('session_token')
        if not session_token:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'session_token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        activities = self.get_session_activities(session_token)
        serializer = self.get_serializer(activities, many=True)
        
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'data': serializer.data
        })
            
    @action(detail=False, methods=['get'])
    def by_visit(self, request):
        """Get activities for a specific patient visit."""
        visit_id = request.query_params.get('visit_id')
        if not visit_id:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'visit_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            visit = PatientVisit.objects.get(id=visit_id)
            
            # Check permissions
            user = request.user
            can_view, error_message = visit.can_be_edited_by(user)
            if not can_view and user != visit.patient:
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': error_message or 'You do not have permission to view this visit'
                }, status=status.HTTP_403_FORBIDDEN)
                
            activities = SessionActivity.objects.filter(visit=visit).order_by('-timestamp')
            serializer = self.get_serializer(activities, many=True)
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'data': serializer.data
            })
            
        except PatientVisit.DoesNotExist:
            return Response({
                'status': False,
                'code': status.HTTP_404_NOT_FOUND,
                'message': 'Visit not found'
            }, status=status.HTTP_404_NOT_FOUND)
