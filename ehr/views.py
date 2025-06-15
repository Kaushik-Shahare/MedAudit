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

User = get_user_model()

# Create your views here.

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.user_type.name == 'Patient':
            return Document.objects.filter(patient=user.profile)
        elif hasattr(user, 'profile') and user.profile.user_type.name == 'Doctor':
            approved_patients = AccessRequest.objects.filter(doctor=user.profile, is_approved=True).values_list('patient', flat=True)
            return Document.objects.filter(patient__in=approved_patients, is_approved=True)
        elif user.is_staff:
            return Document.objects.all()
        return Document.objects.none()
    
    @action(detail=True, methods=['post'])
    def toggle_emergency_access(self, request, pk=None):
        """Toggle a document as accessible in emergency situations."""
        document = self.get_object()
        
        # Only allow patient or admin to toggle emergency access
        if request.user != document.patient and not request.user.is_staff:
            return Response(
                {'detail': 'Only the patient or an admin can set emergency access permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Toggle emergency access flag
        document.is_emergency_accessible = not document.is_emergency_accessible
        document.save()
        
        return Response({
            'id': document.id,
            'is_emergency_accessible': document.is_emergency_accessible
        })

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.user_type.name == 'Doctor':
            serializer.save(uploaded_by=user, is_approved=False)
        elif hasattr(user, 'profile') and user.profile.user_type.name == 'Patient':
            serializer.save(uploaded_by=user, is_approved=True)
        elif user.is_staff:
            serializer.save(uploaded_by=user, is_approved=True)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        document = self.get_object()
        document.is_approved = True
        document.save()
        return Response({'status': 'document approved'})

class AccessRequestViewSet(viewsets.ModelViewSet):
    queryset = AccessRequest.objects.all()
    serializer_class = AccessRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.user_type.name == 'Doctor':
            return AccessRequest.objects.filter(doctor=user.profile)
        elif user.is_staff:
            return AccessRequest.objects.all()
        return AccessRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.user_type.name == 'Doctor':
            serializer.save(doctor=user.profile, is_approved=False)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        access_request = self.get_object()
        access_request.is_approved = True
        access_request.approved_at = timezone.now()
        access_request.save()
        return Response({'status': 'access approved'})

class PatientDocumentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # List all documents for the authenticated patient
        if request.user.user_type.name != 'Patient':
            return Response({'detail': 'Only patients can view their documents.'}, status=status.HTTP_403_FORBIDDEN)
        documents = Document.objects.filter(patient=request.user)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Upload a new document for the authenticated patient
        if request.user.user_type.name != 'Patient':
            return Response({'detail': 'Only patients can upload documents.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Create a copy of the request data
        data = request.data.copy()
        data['patient'] = request.user.id
        
        # Check if file is in the request
        if 'file' not in request.FILES:
            return Response({'detail': 'No file was uploaded.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size - additional check before serializer validation
        file_obj = request.FILES['file']
        if file_obj.size > 100 * 1024 * 1024:  # 100MB
            return Response({'detail': 'File size exceeds the limit of 100MB.'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        # Process with serializer
        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            try:
                document = serializer.save(uploaded_by=request.user, is_approved=True)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                # Log the error for debugging
                print(f"Error saving document: {str(e)}")
                return Response({'detail': f'Error uploading file: {str(e)}'}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PatientDocumentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # Delete a document owned by the authenticated patient
        if request.user.user_type.name != 'Patient':
            return Response({'detail': 'Only patients can delete their documents.'}, status=status.HTTP_403_FORBIDDEN)
        document = get_object_or_404(Document, pk=pk, patient=request.user)
        document.delete()
        return Response({'detail': 'Document deleted.'}, status=status.HTTP_204_NO_CONTENT)
        
class PatientEmergencyDocsAPIView(APIView):
    """View for patients to manage their emergency accessible documents."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Patient can only view their own emergency documents
        if request.user.user_type.name != 'Patient':
            return Response({'detail': 'Only patients can access this view.'}, 
                         status=status.HTTP_403_FORBIDDEN)
        
        # Get documents marked as emergency accessible
        documents = Document.objects.filter(patient=request.user, is_emergency_accessible=True)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        # Set emergency accessible flag for multiple documents
        if request.user.user_type.name != 'Patient':
            return Response({'detail': 'Only patients can modify emergency access.'}, 
                         status=status.HTTP_403_FORBIDDEN)
        
        document_ids = request.data.get('document_ids', [])
        set_accessible = request.data.get('is_emergency_accessible', True)
        
        if not document_ids:
            return Response({'detail': 'No document IDs provided.'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Update all specified documents owned by the patient
        updated = Document.objects.filter(
            id__in=document_ids, 
            patient=request.user
        ).update(is_emergency_accessible=set_accessible)
        
        return Response({
            'detail': f'Updated emergency access for {updated} documents.',
            'is_emergency_accessible': set_accessible
        })

class DoctorPatientDocumentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Doctor views patient documents if access is granted
        if request.user.user_type.name != 'Doctor':
            return Response({'detail': 'Only doctors can view patient documents.'}, status=status.HTTP_403_FORBIDDEN)
        patient_user = get_object_or_404(User, pk=user_id)
        if patient_user.user_type.name != 'Patient':
            return Response({'detail': 'User is not a patient.'}, status=status.HTTP_400_BAD_REQUEST)
        access = AccessRequest.objects.filter(doctor=request.user, patient=patient_user, is_approved=True).exists()
        if not access:
            return Response({'detail': 'Access not granted to this patient.'}, status=status.HTTP_403_FORBIDDEN)
        documents = Document.objects.filter(patient=patient_user, is_approved=True)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
