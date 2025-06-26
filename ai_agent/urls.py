from django.urls import path
from . import views

app_name = 'ai_agent'

urlpatterns = [
    path('verification/<int:insurance_form_id>/', views.trigger_verification, name='trigger_verification'),
    path('verification/<int:insurance_form_id>/result/', views.verification_result, name='verification_result'),
]
