from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, login, logout
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, LoginSerializer, ForgotPasswordSerializer, ProfileUpdateSerializer, UserProfileSerializer, UserDetailSerializer
from MedAudit.exception_handler import custom_exception_handler

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'status': True,
                    'code': status.HTTP_201_CREATED,
                    'message': 'User registered successfully.'
                }, status=status.HTTP_201_CREATED)
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid registration data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in RegisterView: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data
                refresh = RefreshToken.for_user(user)
                
                # Get user details using the UserDetailSerializer
                user_serializer = UserDetailSerializer(user)
                
                return Response({
                    'status': True,
                    'code': status.HTTP_200_OK,
                    'message': 'Login successful',
                    'data': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'user': user_serializer.data
                    },
                })
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid login credentials',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in LoginView: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class LogoutView(APIView):
    def post(self, request):
        try:
            logout(request)
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Logged out successfully.'
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in LogoutView: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ForgotPasswordSerializer(data=request.data)
            if serializer.is_valid():
                # Here you would send a password reset email
                return Response({
                    'status': True,
                    'code': status.HTTP_200_OK,
                    'message': 'Password reset instructions sent.'
                }, status=status.HTTP_200_OK)
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid data provided for password reset',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in ForgotPasswordView: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            serializer = UserDetailSerializer(user)
            return Response({
                'status': True,
                'code': status.HTTP_200_OK,
                'message': 'Profile retrieved successfully',
                'data': serializer.data
            })
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in ProfileUpdateView.get: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response

    def put(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Advance user_stage to 2 if profile is now complete
                if request.user.user_stage == 1:
                    request.user.user_stage = 2
                    request.user.save()
                return Response({
                    'status': True,
                    'code': status.HTTP_200_OK,
                    'message': 'Profile updated successfully',
                    'data': serializer.data
                })
            return Response({
                'status': False,
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Invalid profile data',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            import logging
            logger = logging.getLogger('django.request')
            logger.error(f"Error in ProfileUpdateView.put: {str(exc)}")
            
            # Use the custom exception handler
            response = custom_exception_handler(exc, self.get_renderer_context())
            return response
