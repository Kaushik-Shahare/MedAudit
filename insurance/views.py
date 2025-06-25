from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import InsuranceDocument, InsuranceType, InsurancePolicy, InsuranceForm
from .serializers import (
    InsuranceDocumentSerializer,
    InsuranceTypeSerializer,
    InsurancePolicySerializer,
    InsurancePolicyDetailSerializer,
    InsurancePolicyCreateSerializer,
    InsuranceFormSerializer,
    InsuranceFormDetailSerializer,
    InsuranceFormCreateSerializer,
    AIApprovalSerializer
)
from account.models import UserType

# Custom permissions
class IsAdminOrDoctor(permissions.BasePermission):
    """
    Custom permission to only allow admins or doctors to perform actions.
    """
    def has_permission(self, request, view):
        # Return true if user is a superuser or has user_type as Admin or Doctor
        if request.user and request.user.is_superuser:
            return True 
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type and
            request.user.user_type.name in ['admin', 'Admin', 'Doctor', 'doctor']
        )

class InsuranceTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for insurance types.
    Admin can create, update, delete; all authenticated users can view.
    """
    queryset = InsuranceType.objects.all()
    serializer_class = InsuranceTypeSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'coverage_percentage', 'is_cashless']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrDoctor()]
        return [permissions.IsAuthenticated()]


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for insurance policies.
    """
    queryset = InsurancePolicy.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['policy_number', 'provider', 'patient__email']
    ordering_fields = ['valid_till', 'created_at', 'provider']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrDoctor()]
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InsurancePolicyCreateSerializer
        if self.action == 'retrieve':
            return InsurancePolicyDetailSerializer
        return InsurancePolicySerializer
    
    def get_queryset(self):
        user = self.request.user
        # Admin or superadmin can see all policies
        if user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin'):
            return InsurancePolicy.objects.all()
        # Doctors can see all their patients' policies
        elif user.user_type and user.user_type.name.lower() == 'doctor':
            # This is a simplification - in a real app, you'd likely have a more complex
            # relationship between doctors and patients
            return InsurancePolicy.objects.all()
        # Patients can only see their own policies
        else:
            return InsurancePolicy.objects.filter(patient=user)
    
    @action(detail=False, methods=['get'])
    def active(self):
        """Get only active (non-expired) policies"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(is_active=True, valid_from__lte=today, valid_till__gte=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def patient_policies(self, request):
        """Get policies for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({"error": "patient_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = self.request.user

        # Admin or superadmin can see all patient policies
        if user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin'):
            queryset = InsurancePolicy.objects.filter(patient_id=patient_id)
        # Doctors can see their patients' policies
        elif user.user_type and user.user_type.name.lower() == 'doctor':
            # You might want to check if the requested patient belongs to this doctor
            # For now, assuming doctors can see any patient's policies
            queryset = InsurancePolicy.objects.filter(patient_id=patient_id)
        # Patients can only see their own policies
        else:
            # Only allow if the requested patient_id matches the user's id
            if int(patient_id) == user.id:
                queryset = InsurancePolicy.objects.filter(patient_id=patient_id)
            else:
                return Response(
                    {"error": "You can only view your own policies"}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class InsuranceFormViewSet(viewsets.ModelViewSet):
    """
    ViewSet for insurance forms linked to patient visits.
    """
    queryset = InsuranceForm.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['visit__visit_number', 'reference_number', 'policy__policy_number']
    ordering_fields = ['created_at', 'status', 'claim_amount']
    
    def get_permissions(self):
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InsuranceFormCreateSerializer
        if self.action == 'retrieve':
            return InsuranceFormDetailSerializer
        return InsuranceFormSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Admin can see all forms
        if user.user_type and user.user_type.name == 'admin':
            return InsuranceForm.objects.all()
        # Doctors can see all their patients' forms
        elif user.user_type and user.user_type.name == 'doctor':
            return InsuranceForm.objects.filter(
                Q(visit__attending_doctor=user) | Q(created_by=user)
            )
        # Patients can only see their own forms
        else:
            return InsuranceForm.objects.filter(visit__patient=user)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit the insurance form for processing"""
        insurance_form = self.get_object()
        insurance_form.submit()
        serializer = InsuranceFormDetailSerializer(insurance_form)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve the insurance form (admin only)"""
        if not request.user.user_type or request.user.user_type.name != 'admin':
            return Response(
                {"error": "Only admins can approve insurance forms"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        approved_amount = request.data.get('approved_amount')
        
        if approved_amount:
            try:
                approved_amount = float(approved_amount)
            except ValueError:
                return Response({"error": "Invalid approved_amount"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            approved_amount = insurance_form.claim_amount
            
        insurance_form.approve(approved_amount=approved_amount)
        serializer = InsuranceFormDetailSerializer(insurance_form)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject the insurance form (admin only)"""
        if not request.user.user_type or request.user.user_type.name != 'admin':
            return Response(
                {"error": "Only admins can reject insurance forms"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        reason = request.data.get('reason', '')
        insurance_form.reject(reason=reason)
        serializer = InsuranceFormDetailSerializer(insurance_form)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ai_approval(self, request, pk=None):
        """Process AI-based approval for the insurance form (admin only)"""
        if not request.user.user_type or request.user.user_type.name != 'admin':
            return Response(
                {"error": "Only admins can trigger AI approval"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        serializer = AIApprovalSerializer(data=request.data)
        
        if serializer.is_valid():
            is_approved = serializer.validated_data['is_approved']
            confidence_score = serializer.validated_data.get('confidence_score')
            analysis = serializer.validated_data.get('analysis')
            approved_amount = serializer.validated_data.get('approved_amount')
            
            # Update the AI-related fields
            insurance_form.is_ai_approved = is_approved
            insurance_form.ai_confidence_score = confidence_score
            insurance_form.ai_analysis = analysis
            insurance_form.ai_processing_date = timezone.now()
            
            # If AI approves, update the form status
            if is_approved:
                insurance_form.approve(approved_amount=approved_amount, ai_approved=True)
            
            insurance_form.save()
            result_serializer = InsuranceFormDetailSerializer(insurance_form)
            return Response(result_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def visit_forms(self, request):
        """Get forms for a specific visit"""
        visit_id = request.query_params.get('visit_id')
        if not visit_id:
            return Response({"error": "visit_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        queryset = self.get_queryset().filter(visit_id=visit_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def cashless_claims(self, request):
        """Get only cashless insurance claims"""
        queryset = self.get_queryset().filter(is_cashless_claim=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
