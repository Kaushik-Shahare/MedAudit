from django.contrib import admin
from .models import AIVerificationResult

@admin.register(AIVerificationResult)
class AIVerificationResultAdmin(admin.ModelAdmin):
    list_display = ('insurance_form', 'status', 'confidence_score', 'is_approved', 'created_at', 'completed_at')
    list_filter = ('status', 'is_approved')
    search_fields = ('insurance_form__reference_number', 'verification_summary')
    readonly_fields = ('created_at', 'completed_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('insurance_form', 'status', 'is_approved', 'confidence_score', 'created_at', 'completed_at')
        }),
        ('Verification Results', {
            'fields': ('verification_summary', 'verification_result')
        }),
        ('Sub-Agent Results', {
            'fields': ('eligibility_verification', 'diagnostic_verification', 'treatment_verification',
                      'billing_verification', 'fraud_detection')
        }),
        ('Reflection Information', {
            'fields': ('iteration_count', 'reflections')
        }),
    )
