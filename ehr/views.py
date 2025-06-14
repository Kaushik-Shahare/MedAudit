from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Document, AccessRequest, DoctorProfile, PatientProfile
from .serializers import DocumentSerializer, AccessRequestSerializer
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patient_profile'):
            return Document.objects.filter(patient=user.patient_profile)
        elif hasattr(user, 'doctor_profile'):
            approved_patients = AccessRequest.objects.filter(doctor=user.doctor_profile, is_approved=True).values_list('patient', flat=True)
            return Document.objects.filter(patient__in=approved_patients, is_approved=True)
        elif user.is_staff:
            return Document.objects.all()
        return Document.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'doctor_profile'):
            serializer.save(uploaded_by=user, is_approved=False)
        elif hasattr(user, 'patient_profile'):
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
        if hasattr(user, 'doctor_profile'):
            return AccessRequest.objects.filter(doctor=user.doctor_profile)
        elif user.is_staff:
            return AccessRequest.objects.all()
        return AccessRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'doctor_profile'):
            serializer.save(doctor=user.doctor_profile, is_approved=False)

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
        if not hasattr(request.user, 'patient_profile'):
            return Response({'detail': 'Only patients can view their documents.'}, status=status.HTTP_403_FORBIDDEN)
        documents = Document.objects.filter(patient=request.user.patient_profile)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Upload a new document for the authenticated patient
        if not hasattr(request.user, 'patient_profile'):
            return Response({'detail': 'Only patients can upload documents.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data.copy()
        data['patient'] = request.user.patient_profile.id
        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(uploaded_by=request.user, is_approved=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PatientDocumentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # Delete a document owned by the authenticated patient
        if not hasattr(request.user, 'patient_profile'):
            return Response({'detail': 'Only patients can delete their documents.'}, status=status.HTTP_403_FORBIDDEN)
        document = get_object_or_404(Document, pk=pk, patient=request.user.patient_profile)
        document.delete()
        return Response({'detail': 'Document deleted.'}, status=status.HTTP_204_NO_CONTENT)

class DoctorPatientDocumentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Doctor views patient documents if access is granted
        if not hasattr(request.user, 'doctor_profile'):
            return Response({'detail': 'Only doctors can view patient documents.'}, status=status.HTTP_403_FORBIDDEN)
        patient_user = get_object_or_404(User, pk=user_id)
        if not hasattr(patient_user, 'patient_profile'):
            return Response({'detail': 'User is not a patient.'}, status=status.HTTP_400_BAD_REQUEST)
        access = AccessRequest.objects.filter(doctor=request.user.doctor_profile, patient=patient_user.patient_profile, is_approved=True).exists()
        if not access:
            return Response({'detail': 'Access not granted to this patient.'}, status=status.HTTP_403_FORBIDDEN)
        documents = Document.objects.filter(patient=patient_user.patient_profile, is_approved=True)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
