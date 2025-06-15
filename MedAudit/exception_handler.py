from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException,
    NotFound,
    MethodNotAllowed,
    Throttled,
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
    NotAcceptable,
    UnsupportedMediaType,
    PermissionDenied,
)
from rest_framework import status
import logging

# Set up logger
logger = logging.getLogger('django.request')
from django.http import Http404
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
    SuspiciousOperation,
    FieldDoesNotExist,
)
from django.db import IntegrityError, DatabaseError, OperationalError
import requests.exceptions
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Django REST Framework that returns
    JSON responses for all exceptions instead of HTML.
    """
    
    # Handle DRF exceptions first
    if isinstance(exc, NotAuthenticated):
        custom_response = {
            "status": False,
            "code": status.HTTP_401_UNAUTHORIZED,
            "message": exc.detail if hasattr(exc, 'detail') else "Authentication credentials were not provided.",
        }
        return Response(custom_response, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, AuthenticationFailed):
        custom_response = {
            "status": False,
            "code": status.HTTP_401_UNAUTHORIZED,
            "message": exc.detail if hasattr(exc, 'detail') else "Incorrect authentication credentials.",
        }
        return Response(custom_response, status=status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, (DjangoPermissionDenied, PermissionDenied)):
        message = str(exc) or "You do not have permission to perform this action."
        custom_response = {
            "status": False,
            "code": status.HTTP_403_FORBIDDEN,
            "message": message,
        }
        return Response(custom_response, status=status.HTTP_403_FORBIDDEN)

    if isinstance(exc, Throttled):
        custom_response = {
            "status": False,
            "code": status.HTTP_429_TOO_MANY_REQUESTS,
            "message": exc.detail if hasattr(exc, 'detail') else "Request was throttled.",
        }
        return Response(custom_response, status=status.HTTP_429_TOO_MANY_REQUESTS)

    if isinstance(exc, MethodNotAllowed):
        custom_response = {
            "status": False,
            "code": status.HTTP_405_METHOD_NOT_ALLOWED,
            "message": exc.detail if hasattr(exc, 'detail') else "Method not allowed.",
        }
        return Response(custom_response, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    if isinstance(exc, ValidationError):
        custom_response = {
            "status": False,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": exc.detail if hasattr(exc, 'detail') else "Invalid input.",
        }
        return Response(custom_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, ParseError):
        custom_response = {
            "status": False,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": exc.detail if hasattr(exc, 'detail') else "Malformed request.",
        }
        return Response(custom_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, NotAcceptable):
        custom_response = {
            "status": False,
            "code": status.HTTP_406_NOT_ACCEPTABLE,
            "message": exc.detail if hasattr(exc, 'detail') else "Could not satisfy the request Accept header.",
        }
        return Response(custom_response, status=status.HTTP_406_NOT_ACCEPTABLE)

    if isinstance(exc, UnsupportedMediaType):
        custom_response = {
            "status": False,
            "code": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "message": exc.detail if hasattr(exc, 'detail') else "Unsupported media type.",
        }
        return Response(custom_response, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    if isinstance(exc, APIException):
        custom_response = {
            "status": False,
            "code": exc.status_code,
            "message": exc.detail if hasattr(exc, 'detail') else "API error.",
        }
        return Response(custom_response, status=exc.status_code)

    # Handle Django exceptions
    if isinstance(exc, ObjectDoesNotExist):
        message = str(exc) or "The requested resource was not found."
        custom_response = {
            "status": False,
            "code": status.HTTP_404_NOT_FOUND,
            "message": message,
        }
        return Response(custom_response, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, Http404):
        message = str(exc) or "The requested URL was not found on this server."
        custom_response = {
            "status": False,
            "code": status.HTTP_404_NOT_FOUND,
            "message": message,
        }
        return Response(custom_response, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            message = exc.message_dict
        elif hasattr(exc, 'messages'):
            message = exc.messages
        else:
            message = str(exc)
            
        custom_response = {
            "status": False,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": message,
        }
        return Response(custom_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, SuspiciousOperation):
        custom_response = {
            "status": False,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": "Invalid request. Suspicious operation detected.",
        }
        return Response(custom_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, FieldDoesNotExist):
        custom_response = {
            "status": False,
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Server configuration error. Required field not found.",
        }
        return Response(custom_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Handle database exceptions
    if isinstance(exc, IntegrityError):
        custom_response = {
            "status": False,
            "code": status.HTTP_400_BAD_REQUEST,
            "message": "Database integrity error. Please check your data.",
        }
        return Response(custom_response, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, OperationalError):
        custom_response = {
            "status": False,
            "code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "message": "Database operation failed. Please try again later.",
        }
        return Response(custom_response, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if isinstance(exc, DatabaseError):
        custom_response = {
            "status": False,
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "A database error occurred. Please contact support.",
        }
        return Response(custom_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Handle requests exceptions
    if isinstance(exc, requests.exceptions.ConnectionError):
        custom_response = {
            "status": False,
            "code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "message": "Network connection failed. Check your connection.",
        }
        return Response(custom_response, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if isinstance(exc, requests.exceptions.Timeout):
        custom_response = {
            "status": False,
            "code": status.HTTP_504_GATEWAY_TIMEOUT,
            "message": "Request timed out. Please try again later.",
        }
        return Response(custom_response, status=status.HTTP_504_GATEWAY_TIMEOUT)

    if isinstance(exc, requests.exceptions.RequestException):
        custom_response = {
            "status": False,
            "code": status.HTTP_502_BAD_GATEWAY,
            "message": "Network error occurred. Please try again.",
        }
        return Response(custom_response, status=status.HTTP_502_BAD_GATEWAY)

    # Handle other exceptions
    if isinstance(exc, PermissionError):
        custom_response = {
            "status": False,
            "code": status.HTTP_403_FORBIDDEN,
            "message": str(exc),
        }
        return Response(custom_response, status=status.HTTP_403_FORBIDDEN)

    # Handle default DRF exceptions
    response = exception_handler(exc, context)
    if response is not None:
        return response
        
    # Log the exception for better debugging
    if hasattr(exc, '__str__'):
        logger.error(f"Exception in API request: {str(exc)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Fallback for unhandled exceptions
    custom_response = {
        "status": False,
        "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "message": "An unexpected error occurred. Please contact support.",
    }
    return Response(custom_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
