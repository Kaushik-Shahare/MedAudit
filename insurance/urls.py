from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InsuranceTypeViewSet,
    InsurancePolicyViewSet,
    InsuranceFormViewSet
)

router = DefaultRouter()
router.register(r'types', InsuranceTypeViewSet)
router.register(r'policies', InsurancePolicyViewSet)
router.register(r'forms', InsuranceFormViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

