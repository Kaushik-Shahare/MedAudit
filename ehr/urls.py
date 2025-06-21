from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (DocumentViewSet, AccessRequestViewSet, PatientDocumentListCreateAPIView, 
                   PatientDocumentDeleteAPIView, DoctorPatientDocumentListAPIView, PatientEmergencyDocsAPIView,
                   nfc_session_documents)
from .nfc_views import (NFCCardViewSet, NFCSessionViewSet, verify_nfc_session, emergency_access,
                      generate_nfc_qr_code, generate_emergency_qr_code, tap_nfc_card_public)
from .visit_views import (PatientVisitViewSet, VisitChargeViewSet, SessionActivityViewSet,
                       VitalSignsViewSet, DiagnosisViewSet, LabResultViewSet, PrescriptionViewSet)

# Set up the regular API routers
router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'access-requests', AccessRequestViewSet, basename='accessrequest')
router.register(r'nfc-cards', NFCCardViewSet, basename='nfccard')
router.register(r'nfc-sessions', NFCSessionViewSet, basename='nfcsession')
router.register(r'patient-visits', PatientVisitViewSet, basename='patientvisit')
router.register(r'visit-charges', VisitChargeViewSet, basename='visitcharge')
router.register(r'session-activities', SessionActivityViewSet, basename='sessionactivity')

# Medical document APIs - restricted to medical staff (doctors and admins)
router.register(r'vital-signs', VitalSignsViewSet, basename='vitalsigns')
router.register(r'diagnoses', DiagnosisViewSet, basename='diagnosis')
router.register(r'lab-results', LabResultViewSet, basename='labresult')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')

urlpatterns = [
    path('', include(router.urls)),
    # Patient document management
    path('patient/documents/', PatientDocumentListCreateAPIView.as_view(), name='patient-documents'),
    path('patient/documents/<int:pk>/', PatientDocumentDeleteAPIView.as_view(), name='patient-document-delete'),
    path('patient/emergency-docs/', PatientEmergencyDocsAPIView.as_view(), name='patient-emergency-docs'),
    path('doctor/patient/<int:user_id>/documents/', DoctorPatientDocumentListAPIView.as_view(), name='doctor-patient-documents'),
    
    # NFC functionality
    path('nfc/verify-session/', verify_nfc_session, name='verify-nfc-session'),
    path('nfc/generate-qr/', generate_nfc_qr_code, name='generate-nfc-qr'),
    path('nfc/session/<str:session_token>/documents/', nfc_session_documents, name='nfc-session-documents'),
    path('nfc/tap/<uuid:card_id>/', tap_nfc_card_public, name='universal-nfc-tap'),  # Single unified tap endpoint
    path('emergency/generate-qr/', generate_emergency_qr_code, name='generate-emergency-qr'),
    path('emergency-access/<str:token>/', emergency_access, name='emergency-access'),
] 