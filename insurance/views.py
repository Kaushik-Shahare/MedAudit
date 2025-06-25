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
    search_fields = ['visit__visit_number', 'reference_number', 'policy__policy_number', 'diagnosis', 'icd_code']
    ordering_fields = ['created_at', 'status', 'claim_amount', 'submission_date', 'approval_date']
    
    def list(self, request, *args, **kwargs):
        """Override list to provide detailed debugging"""
        # Debug info
        print(f"User: {request.user}, User type: {request.user.user_type if hasattr(request.user, 'user_type') else 'No type'}")
        print(f"Is superuser: {request.user.is_superuser}")
        
        # Get forms based on permissions
        queryset = self.filter_queryset(self.get_queryset())
        print(f"Total forms after filtering: {queryset.count()}")
        
        # Show all forms in system for debugging
        all_forms = InsuranceForm.objects.all()
        print(f"Total forms in system: {all_forms.count()}")
        if all_forms.count() > 0:
            for form in all_forms:
                print(f"Form ID: {form.id}, Visit: {form.visit_id}, Policy: {form.policy_id}, Created by: {form.created_by_id}")
        
        # Apply additional filters if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        is_cashless = request.query_params.get('is_cashless')
        if is_cashless is not None:
            is_cashless_bool = is_cashless.lower() == 'true'
            queryset = queryset.filter(is_cashless_claim=is_cashless_bool)
        
        treatment_type = request.query_params.get('treatment_type')
        if treatment_type:
            queryset = queryset.filter(treatment_type=treatment_type)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': True,
            'code': status.HTTP_200_OK, 
            'count': queryset.count(),
            'data': serializer.data
        })
    
    def get_permissions(self):
        return [permissions.IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InsuranceFormCreateSerializer
        if self.action == 'retrieve' or self.action in ['submit', 'approve', 'reject', 'ai_approval', 
                                                      'request_enhancement', 'finalize_claim', 
                                                      'mark_payment_completed']:
            return InsuranceFormDetailSerializer
        return InsuranceFormSerializer
    
    def get_queryset(self):
        user = self.request.user
        # Admin or superadmin can see all forms
        if user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin'):
            return InsuranceForm.objects.all()
        # Doctors can see all their patients' forms
        elif user.user_type and user.user_type.name.lower() == 'doctor':
            return InsuranceForm.objects.filter(
                Q(visit__attending_doctor=user) | Q(created_by=user)
            )
        # Patients can only see their own forms
        else:
            return InsuranceForm.objects.filter(visit__patient=user)
    
    def perform_create(self, serializer):
        return serializer.save(created_by=self.request.user)
        
    def create(self, request, *args, **kwargs):
        """Override create to return detailed information after creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        
        # Use the detail serializer for the response
        detail_serializer = InsuranceFormDetailSerializer(instance)
        
        return Response({
            'status': True,
            'message': 'Insurance form created successfully',
            'data': detail_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit the insurance form for processing"""
        insurance_form = self.get_object()
        insurance_form.submit()
        serializer = InsuranceFormDetailSerializer(insurance_form)
        return Response({
            'status': True,
            'message': f"Insurance form {insurance_form.id} submitted successfully",
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve the insurance form (admin/superadmin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin')):
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
        
        return Response({
            'status': True,
            'message': f"Insurance form {insurance_form.id} approved successfully",
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject the insurance form (admin/superadmin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin')):
            return Response(
                {"error": "Only admins can reject insurance forms"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {"error": "Rejection reason is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        insurance_form.reject(reason=reason)
        serializer = InsuranceFormDetailSerializer(insurance_form)
        
        return Response({
            'status': True,
            'message': f"Insurance form {insurance_form.id} rejected",
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def ai_approval(self, request, pk=None):
        """Process AI-based approval for the insurance form (admin/superadmin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin')):
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
            
            return Response({
                'status': True,
                'message': f"AI approval processed for insurance form {insurance_form.id}",
                'data': result_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def request_enhancement(self, request, pk=None):
        """Request enhancement for a cashless claim (doctor or admin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() in ['admin', 'doctor'])):
            return Response(
                {"error": "Only doctors or admins can request enhancement"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        
        # Validate that this is a cashless claim
        if not insurance_form.is_cashless_claim:
            return Response(
                {"error": "Enhancement can only be requested for cashless claims"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate that the form is in an appropriate state
        if insurance_form.status not in ['pre_auth_approved']:
            return Response(
                {"error": "Enhancement can only be requested for pre-authorized forms"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get enhancement details
        amount = request.data.get('amount')
        reason = request.data.get('reason')
        
        if not amount:
            return Response(
                {"error": "Enhancement amount is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not reason:
            return Response(
                {"error": "Enhancement reason is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            amount = float(amount)
        except ValueError:
            return Response(
                {"error": "Invalid enhancement amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        insurance_form.request_enhancement(amount=amount, reason=reason)
        serializer = InsuranceFormDetailSerializer(insurance_form)
        
        return Response({
            'status': True,
            'message': f"Enhancement requested for insurance form {insurance_form.id}",
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def finalize_claim(self, request, pk=None):
        """Finalize a cashless claim after treatment (doctor or admin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() in ['admin', 'doctor'])):
            return Response(
                {"error": "Only doctors or admins can finalize claims"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        
        # Validate that this is a cashless claim
        if not insurance_form.is_cashless_claim:
            return Response(
                {"error": "Only cashless claims need to be finalized"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate that the form is in an appropriate state
        if insurance_form.status not in ['pre_auth_approved', 'enhancement_requested']:
            return Response(
                {"error": "Only pre-authorized or enhancement-requested forms can be finalized"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get final amount if provided
        final_amount = request.data.get('final_amount')
        if final_amount:
            try:
                final_amount = float(final_amount)
            except ValueError:
                return Response(
                    {"error": "Invalid final amount"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        insurance_form.finalize_claim(final_amount=final_amount)
        serializer = InsuranceFormDetailSerializer(insurance_form)
        
        return Response({
            'status': True,
            'message': f"Claim finalized for insurance form {insurance_form.id}",
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def mark_payment_completed(self, request, pk=None):
        """Mark payment as completed for a claim (admin only)"""
        user = request.user
        if not (user.is_superuser or (user.user_type and user.user_type.name.lower() == 'admin')):
            return Response(
                {"error": "Only admins can mark payments as completed"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        insurance_form = self.get_object()
        
        # Validate that the form is in an appropriate state
        if insurance_form.status != 'payment_pending':
            return Response(
                {"error": "Only forms with pending payment can be marked as completed"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        insurance_form.mark_payment_completed()
        serializer = InsuranceFormDetailSerializer(insurance_form)
        
        return Response({
            'status': True,
            'message': f"Payment marked as completed for insurance form {insurance_form.id}",
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def visit_forms(self, request):
        """Get forms for a specific visit"""
        visit_id = request.query_params.get('visit_id')
        if not visit_id:
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': "visit_id query parameter is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # For debugging
        print(f"Looking for insurance forms with visit_id={visit_id}")
        
        # Get all forms for this visit, regardless of permission filtering
        # This ensures we can debug if forms exist but aren't being returned due to permission issues
        all_forms = InsuranceForm.objects.filter(visit_id=visit_id)
        print(f"Total forms found for this visit (before permission filtering): {all_forms.count()}")
        
        # Get the filtered queryset based on user permissions
        queryset = self.get_queryset().filter(visit_id=visit_id)
        print(f"Forms available to user after permission filtering: {queryset.count()}")
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def cashless_claims(self, request):
        """Get only cashless insurance claims"""
        queryset = self.get_queryset().filter(is_cashless_claim=True)
        
        # Apply additional filters if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'count': queryset.count(),
            'data': serializer.data
        })
        
    @action(detail=False, methods=['get'])
    def pending_preauth(self, request):
        """Get all pending pre-authorization forms"""
        queryset = self.get_queryset().filter(status='pre_auth_pending')
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'count': queryset.count(),
            'data': serializer.data
        })
        
    @action(detail=False, methods=['get'])
    def enhancement_requests(self, request):
        """Get all forms with enhancement requests"""
        queryset = self.get_queryset().filter(status='enhancement_requested')
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': True,
            'code': status.HTTP_200_OK,
            'count': queryset.count(),
            'data': serializer.data
        })
        
    @action(detail=False, methods=['post'])
    def auto_create_from_visit(self, request):
        """
        Auto-create an insurance form from existing patient visit data.
        Requires:
        - visit_id: ID of the patient visit
        - policy_id: ID of the insurance policy to use
        - is_cashless: boolean indicating if this is a cashless claim
        """
        visit_id = request.data.get('visit_id')
        policy_id = request.data.get('policy_id')
        is_cashless = request.data.get('is_cashless', False)
        
        if not visit_id or not policy_id:
            return Response({
                'status': False,
                'message': 'Both visit_id and policy_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the visit and policy
            from ehr.models import PatientVisit
            visit = PatientVisit.objects.get(id=visit_id)
            policy = InsurancePolicy.objects.get(id=policy_id)
            
            # Check if user has permission to access this visit
            if not visit.can_be_edited_by(request.user)[0]:
                return Response({
                    'status': False,
                    'message': 'You do not have permission to create an insurance form for this visit'
                }, status=status.HTTP_403_FORBIDDEN)
                
            # Check if visit and policy belong to same patient
            if visit.patient != policy.patient:
                return Response({
                    'status': False,
                    'message': 'The insurance policy does not belong to the patient of this visit'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Check if policy is valid
            if not policy.is_valid:
                return Response({
                    'status': False,
                    'message': 'The selected insurance policy is not currently valid'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Check if form already exists for this visit
            if InsuranceForm.objects.filter(visit=visit).exists():
                existing_forms = InsuranceForm.objects.filter(visit=visit)
                return Response({
                    'status': False,
                    'message': f'Insurance form(s) already exist for this visit. Form IDs: {", ".join([str(f.id) for f in existing_forms])}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the form using our factory method
            form = InsuranceForm.create_from_visit(
                visit=visit,
                policy=policy,
                created_by=request.user,
                is_cashless=is_cashless
            )
            
            # Try to populate from previous forms
            form.auto_populate_from_previous_forms()
            
            # Return the created form
            serializer = InsuranceFormDetailSerializer(form)
            return Response({
                'status': True,
                'message': 'Insurance form auto-created successfully from visit data',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except PatientVisit.DoesNotExist:
            return Response({
                'status': False,
                'message': 'Visit not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except InsurancePolicy.DoesNotExist:
            return Response({
                'status': False,
                'message': 'Insurance policy not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': False,
                'message': f'Error creating form: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_from_visit_data(self, request, pk=None):
        """Update an insurance form with the latest data from the visit"""
        form = self.get_object()
        
        # Check if the user has permission to edit this form
        user = request.user
        if not (user.is_superuser or 
                (user.user_type and user.user_type.name.lower() in ['admin', 'doctor']) or 
                user == form.created_by or 
                user == form.visit.attending_doctor):
            return Response({
                'status': False,
                'message': 'You do not have permission to update this form'
            }, status=status.HTTP_403_FORBIDDEN)
            
        # Update the form from visit data
        updated = form.update_from_visit_data()
        
        if updated:
            serializer = InsuranceFormDetailSerializer(form)
            return Response({
                'status': True,
                'message': 'Form updated successfully with latest visit data',
                'data': serializer.data
            })
        else:
            return Response({
                'status': False,
                'message': 'No updates were made to the form'
            })
