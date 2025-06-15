from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Document, AccessRequest, NFCCard, NFCSession, EmergencyAccess

User = get_user_model()

# Custom admin actions and views
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'description', 'uploaded_at', 'is_approved', 'is_emergency_accessible')
    list_filter = ('is_approved', 'is_emergency_accessible', 'document_type')
    search_fields = ('description', 'patient__email')
    actions = ['make_emergency_accessible', 'make_non_emergency_accessible']
    
    def make_emergency_accessible(self, request, queryset):
        updated = queryset.update(is_emergency_accessible=True)
        self.message_user(request, f'{updated} documents were marked as emergency accessible.')
    make_emergency_accessible.short_description = "Mark selected documents as emergency accessible"
    
    def make_non_emergency_accessible(self, request, queryset):
        updated = queryset.update(is_emergency_accessible=False)
        self.message_user(request, f'{updated} documents were marked as non-emergency accessible.')
    make_non_emergency_accessible.short_description = "Mark selected documents as non-emergency accessible"

@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'patient', 'is_approved', 'requested_at', 'approved_at')
    list_filter = ('is_approved',)
    search_fields = ('doctor__email', 'patient__email')
    actions = ['approve_access']
    
    def approve_access(self, request, queryset):
        for access_request in queryset.filter(is_approved=False):
            access_request.is_approved = True
            access_request.approved_at = timezone.now()
            access_request.save()
        self.message_user(request, f'{queryset.count()} access requests were approved.')
    approve_access.short_description = "Approve selected access requests"

@admin.register(NFCCard)
class NFCCardAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'card_id', 'is_active', 'created_at', 'last_used')
    list_filter = ('is_active',)
    search_fields = ('patient__email', 'card_id')
    actions = ['activate_cards', 'deactivate_cards']
    
    def activate_cards(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} NFC cards were activated.')
    activate_cards.short_description = "Activate selected NFC cards"
    
    def deactivate_cards(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} NFC cards were deactivated.')
    deactivate_cards.short_description = "Deactivate selected NFC cards"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('manage/', self.admin_site.admin_view(self.nfc_management_view), name='nfc_card_management'),
            path('create/', self.admin_site.admin_view(self.create_nfc_card), name='create_nfc_card'),
            path('activate/<int:card_id>/', self.admin_site.admin_view(self.activate_nfc_card), name='activate_nfc_card'),
            path('deactivate/<int:card_id>/', self.admin_site.admin_view(self.deactivate_nfc_card), name='deactivate_nfc_card'),
        ]
        return custom_urls + urls
    
    def nfc_management_view(self, request):
        # Get all patients (users with patient user_type)
        patients = User.objects.filter(user_type__name='Patient')
        nfc_cards = NFCCard.objects.all().order_by('-created_at')
        
        context = {
            'patients': patients,
            'nfc_cards': nfc_cards,
            **self.admin_site.each_context(request),
        }
        return render(request, 'admin/nfc_card_management.html', context)
    
    def create_nfc_card(self, request):
        if request.method == 'POST':
            patient_id = request.POST.get('patient')
            try:
                patient = User.objects.get(id=patient_id)
                
                # Check if patient already has a card
                existing_card = NFCCard.objects.filter(patient=patient).first()
                if existing_card:
                    messages.error(request, f'Patient {patient.email} already has an NFC card.')
                else:
                    NFCCard.objects.create(patient=patient)
                    messages.success(request, f'NFC card created for patient {patient.email}.')
            except User.DoesNotExist:
                messages.error(request, 'Patient not found.')
        
        return HttpResponseRedirect('../manage/')
    
    def activate_nfc_card(self, request, card_id):
        card = get_object_or_404(NFCCard, id=card_id)
        card.is_active = True
        card.save()
        messages.success(request, f'Card for {card.patient.email} activated.')
        return HttpResponseRedirect('../manage/')
    
    def deactivate_nfc_card(self, request, card_id):
        card = get_object_or_404(NFCCard, id=card_id)
        card.is_active = False
        card.save()
        messages.success(request, f'Card for {card.patient.email} deactivated.')
        return HttpResponseRedirect('../manage/')

@admin.register(NFCSession)
class NFCSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'started_at', 'expires_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('patient__email',)
    actions = ['invalidate_sessions']
    
    def invalidate_sessions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} NFC sessions were invalidated.')
    invalidate_sessions.short_description = "Invalidate selected NFC sessions"

@admin.register(EmergencyAccess)
class EmergencyAccessAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'created_at', 'expires_at', 'last_accessed', 'access_count')
    search_fields = ('patient__email',)
