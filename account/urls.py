from django.urls import path
from .views import RegisterView, LoginView, LogoutView, ForgotPasswordView, ProfileUpdateView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='account-register'),
    path('login/', LoginView.as_view(), name='account-login'),
    path('logout/', LogoutView.as_view(), name='account-logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='account-forgot-password'),
    path('profile/', ProfileUpdateView.as_view(), name='account-profile'),
] 