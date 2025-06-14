from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DocumentViewSet, AccessRequestViewSet, PatientDocumentListCreateAPIView, PatientDocumentDeleteAPIView, DoctorPatientDocumentListAPIView

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'access-requests', AccessRequestViewSet, basename='accessrequest')

urlpatterns = [
    path('', include(router.urls)),
    path('patient/documents/', PatientDocumentListCreateAPIView.as_view(), name='patient-documents'),
    path('patient/documents/<int:pk>/', PatientDocumentDeleteAPIView.as_view(), name='patient-document-delete'),
    path('doctor/patient/<int:user_id>/documents/', DoctorPatientDocumentListAPIView.as_view(), name='doctor-patient-documents'),
] 