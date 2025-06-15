from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import Document, AccessRequest, NFCCard, NFCSession, EmergencyAccess
from .serializers import (DocumentSerializer, AccessRequestSerializer, NFCCardSerializer, 
                         NFCSessionSerializer, EmergencyAccessSerializer, EmergencyDocumentSerializer)
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
import uuid
from datetime import timedelta
from MedAudit.exception_handler import custom_exception_handler

User = get_user_model()

# Create your views here.

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        try:
            user = self.request.user
            if hasattr(user, 'profile') and user.user_type.name == 'Patient':
                return Document.objects.filter(patient=user)
            elif hasattr(user, 'profile') and user.user_type.name == 'Doctor':
                approved_patients = AccessRequest.objects.filter(doctor=user, is_approved=True).values_list('patient', flat=True)
                return Document.objects.filter(patient__in=approved_patients, is_approved=True)
            elif user.is_staff:
                return Document.objects.all()
            return Document.objects.none()
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in DocumentViewSet.get_queryset: {str(exc)}")
            
            # Return empty queryset on error to prevent breaking page loads
            # The actual exception will be handled by DRF's exception handler
            return Document.objects.none()
    
    @action(detail=True, methods=['post'])
    def toggle_emergency_access(self, request, pk=None):
        """Toggle a document as accessible in emergency situations."""
        try:
            document = self.get_object()
            
            # Only allow patient who owns the document or admin to toggle emergency access
            if request.user != document.patient and not request.user.is_staff:
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Only the patient or an admin can set emergency access permissions'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Toggle emergency access flag
            document.is_emergency_accessible = not document.is_emergency_accessible
            document.save()
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Emergency access setting updated successfully',
                'data': {
                    'id': document.id,
                    'is_emergency_accessible': document.is_emergency_accessible
                }
            })
        except Exception as e:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in toggle_emergency_access: {str(e)}")
            return Response({
                'status': False,
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'An unexpected error occurred while toggling emergency access.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        try:
            user = self.request.user
            if hasattr(user, 'profile') and user.user_type.name == 'Doctor':
                serializer.save(uploaded_by=user, patient=user, is_approved=False)
            elif hasattr(user, 'profile') and user.user_type.name == 'Patient':
                serializer.save(uploaded_by=user, patient=user, is_approved=True)
            elif user.is_staff:
                serializer.save(uploaded_by=user, is_approved=True)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in DocumentViewSet.perform_create: {str(exc)}")
            
            # Raise the exception to be handled by DRF
            raise

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        try:
            document = self.get_object()
            document.is_approved = True
            document.save()
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Document approved successfully'
            })
        except Exception as e:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in DocumentViewSet.approve: {str(e)}")
            return Response({
                'status': False,
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'An unexpected error occurred while approving the document.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccessRequestViewSet(viewsets.ModelViewSet):
    queryset = AccessRequest.objects.all()
    serializer_class = AccessRequestSerializer

    def get_queryset(self):
        try:
            user = self.request.user
            if hasattr(user, 'profile') and user.user_type.name == 'Doctor':
                return AccessRequest.objects.filter(doctor=user)
            elif user.is_staff:
                return AccessRequest.objects.all()
            return AccessRequest.objects.none()
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in AccessRequestViewSet.get_queryset: {str(e)}")
            # Return empty queryset on error
            return AccessRequest.objects.none()

    def perform_create(self, serializer):
        try:
            user = self.request.user
            if hasattr(user, 'profile') and user.user_type.name == 'Doctor':
                serializer.save(doctor=user, is_approved=False)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in AccessRequestViewSet.perform_create: {str(exc)}")
            
            # Raise the exception to be handled by DRF
            raise

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        try:
            access_request = self.get_object()
            access_request.is_approved = True
            access_request.approved_at = timezone.now()
            access_request.save()
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Access request approved successfully'
            })
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in AccessRequestViewSet.approve: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class PatientDocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # List all documents for the authenticated patient
            if request.user.user_type.name != 'Patient':
                return Response(
                    {'status': False, 'code': status.HTTP_403_FORBIDDEN, 'message': 'Only patients can view their documents.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            documents = Document.objects.filter(patient=request.user)
            serializer = DocumentSerializer(documents, many=True)
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Documents retrieved successfully.',
                'data': serializer.data
            })
        except Exception as exc:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientDocumentListCreateAPIView.get: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

    def post(self, request):
        try:
            # Upload a new document for the authenticated patient
            if request.user.user_type.name != 'Patient':
                return Response(
                    {'status': False, 'code': status.HTTP_403_FORBIDDEN, 'message': 'Only patients can upload documents.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create a copy of the request data
            data = request.data.copy()
            data['patient'] = request.user.id
            
            # Check if file is in the request
            if 'file' not in request.FILES:
                return Response(
                    {'status': False, 'code': status.HTTP_400_BAD_REQUEST, 'message': 'No file was uploaded.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate file size - additional check before serializer validation
            file_obj = request.FILES['file']
            if file_obj.size > 100 * 1024 * 1024:  # 100MB
                return Response(
                    {'status': False, 'code': status.HTTP_400_BAD_REQUEST, 'message': 'File size exceeds the limit of 100MB.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process with serializer
            serializer = DocumentSerializer(data=data)
            if serializer.is_valid():
                try:
                    document = serializer.save(uploaded_by=request.user, is_approved=True)
                    return Response({
                        'status': True, 
                        'code': status.HTTP_201_CREATED,
                        'message': 'Document uploaded successfully.',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                except Exception as e:
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger('django.request')
                    logger.error(f"Error saving document: {str(e)}")
                    
                    return Response(
                        {'status': False, 'code': status.HTTP_500_INTERNAL_SERVER_ERROR, 'message': f'Error uploading file: {str(e)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            return Response(
                {'status': False, 'code': status.HTTP_400_BAD_REQUEST, 'message': 'Invalid data', 'errors': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientDocumentListCreateAPIView.post: {str(e)}")
            
            return Response(
                {'status': False, 'code': status.HTTP_500_INTERNAL_SERVER_ERROR, 'message': 'An unexpected error occurred.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PatientDocumentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            # Delete a document owned by the authenticated patient
            if request.user.user_type.name != 'Patient':
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Only patients can delete their documents.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            document = get_object_or_404(Document, pk=pk, patient=request.user)
            document.delete()
            
            return Response({
                'status': True,
                'code': status.HTTP_204_NO_CONTENT,
                'message': 'Document deleted successfully.'
            }, status=status.HTTP_204_NO_CONTENT)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientDocumentDeleteAPIView.delete: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response
        
class PatientEmergencyDocsAPIView(APIView):
    """View for patients to manage their emergency accessible documents."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Patient can only view their own emergency documents
            if request.user.user_type.name != 'Patient':
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Only patients can access this view.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get documents marked as emergency accessible
            documents = Document.objects.filter(patient=request.user, is_emergency_accessible=True)
            serializer = DocumentSerializer(documents, many=True)
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Emergency documents retrieved successfully',
                'data': serializer.data
            })
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientEmergencyDocsAPIView.get: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response
    
    def post(self, request):
        try:
            # Set emergency accessible flag for multiple documents
            if request.user.user_type.name != 'Patient':
                return Response({
                    'status': False,
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Only patients can modify emergency access.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            document_ids = request.data.get('document_ids', [])
            set_accessible = request.data.get('is_emergency_accessible', True)
            
            if not document_ids:
                return Response({
                    'status': False,
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'No document IDs provided.'
                }, status.HTTP_400_BAD_REQUEST)
            
            # Update all specified documents owned by the patient
            updated = Document.objects.filter(
                id__in=document_ids, 
                patient=request.user
            ).update(is_emergency_accessible=set_accessible)
            
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': f'Updated emergency access for {updated} documents.',
                'data': {
                    'updated_count': updated,
                    'is_emergency_accessible': set_accessible
                }
            })
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in PatientEmergencyDocsAPIView.post: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class DoctorPatientDocumentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        # Doctor views patient documents if access is granted
        try:
            # First check if the user is a doctor
            if request.user.user_type.name != 'Doctor':
                return Response(
                    {'status': False, 'code': status.HTTP_403_FORBIDDEN, 'message': 'Only doctors can view patient documents.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Check if user_id is valid
            if not user_id or not str(user_id).isdigit():
                return Response(
                    {'status': False, 'code': status.HTTP_400_BAD_REQUEST, 'message': 'Invalid or missing patient ID.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Try to get the patient
            try:
                patient_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response(
                    {'status': False, 'code': status.HTTP_404_NOT_FOUND, 'message': 'Patient not found.'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Verify user is a patient
            if patient_user.user_type.name != 'Patient':
                return Response(
                    {'status': False, 'code': status.HTTP_400_BAD_REQUEST, 'message': 'User is not a patient.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if doctor has access
            access = AccessRequest.objects.filter(doctor=request.user, patient=patient_user, is_approved=True).exists()
            if not access:
                return Response(
                    {'status': False, 'code': status.HTTP_403_FORBIDDEN, 'message': 'Access not granted to this patient.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Get documents if all checks pass
            documents = Document.objects.filter(patient=patient_user, is_approved=True)
            serializer = DocumentSerializer(documents, many=True)
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Documents retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as exc:
            # Use the custom exception handler
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in DoctorPatientDocumentListAPIView: {str(exc)}")
            
            # Use the custom exception handler from MedAudit
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response
