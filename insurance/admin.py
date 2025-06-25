from django.contrib import admin
from .models import InsuranceDocument, InsuranceType, InsurancePolicy, InsuranceForm

@admin.register(InsuranceDocument)
class InsuranceDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_id', 'patient_id', 'document_type', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['patient_id', 'document_type']

@admin.register(InsuranceType)
class InsuranceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_cashless', 'coverage_percentage', 'max_coverage_amount', 'requires_pre_authorization']
    list_filter = ['is_cashless', 'requires_pre_authorization']
    search_fields = ['name', 'description']

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'patient', 'insurance_type', 'provider', 'valid_from', 'valid_till', 'is_active']
    list_filter = ['is_active', 'insurance_type', 'provider']
    search_fields = ['policy_number', 'patient__email', 'provider']
    date_hierarchy = 'valid_till'

@admin.register(InsuranceForm)
class InsuranceFormAdmin(admin.ModelAdmin):
    list_display = ['id', 'visit', 'policy', 'claim_amount', 'status', 'is_ai_approved', 'is_cashless_claim']
    list_filter = ['status', 'is_ai_approved', 'is_cashless_claim', 'created_at']
    search_fields = ['visit__visit_number', 'policy__policy_number', 'reference_number']
    fieldsets = [
        ('Basic Information', {
            'fields': ['visit', 'policy', 'created_by', 'status']
        }),
        ('Claim Details', {
            'fields': ['diagnosis', 'treatment_description', 'claim_amount', 'approved_amount']
        }),
        ('AI Processing', {
            'fields': ['is_ai_approved', 'ai_confidence_score', 'ai_processing_date', 'ai_analysis']
        }),
        ('Cashless Processing', {
            'fields': ['is_cashless_claim', 'pre_authorization_reference', 'pre_authorization_date', 'pre_authorized_amount']
        }),
        ('References', {
            'fields': ['reference_number', 'submission_date', 'approval_date', 'rejection_reason']
        })
    ]
