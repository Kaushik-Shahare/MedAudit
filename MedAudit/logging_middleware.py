import logging
import json
import uuid
import contextvars
from asgiref.sync import sync_to_async


request_context = contextvars.ContextVar('request', default=None)

import logging
import json
import asyncio

class RequestResponseLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _log_request(self, request):
        logger = logging.getLogger('django.request')
        logger.debug("Incoming Request:")
        logger.debug(f"  Method: {request.method}")
        logger.debug(f"  URL: {request.get_full_path()}")

        if request.body:
            try:
                request_data = json.loads(request.body.decode('utf-8'))
                formatted_request_body = json.dumps(request_data, indent=4)
            except (json.JSONDecodeError, UnicodeDecodeError):
                formatted_request_body = request.body.decode('utf-8', errors='ignore')
            logger.debug("  Request Body:")
            logger.debug(formatted_request_body)

    def _log_response(self, response):
        logger = logging.getLogger('django.request')
        logger.debug("Outgoing Response:")
        logger.debug(f"  Status: {response.status_code}")
        if hasattr(response, 'content'):
            try:
                response_data = json.loads(response.content.decode('utf-8'))
                formatted_response_content = json.dumps(response_data, indent=4)
            except (json.JSONDecodeError, UnicodeDecodeError):
                formatted_response_content = response.content.decode('utf-8', errors='ignore')
            logger.debug("  Response Content:")
            logger.debug(formatted_response_content)

    def __call__(self, request):
        self._log_request(request)
        response = self.get_response(request)
        if asyncio.iscoroutine(response):
            return self._handle_async_response(request, response)
        self._log_response(response)
        return response

    async def _handle_async_response(self, request, coro):
        try:
            response = await coro
            self._log_response(response)
            return response
        except Exception:
            logging.getLogger('django.request').exception("Exception during async response")
            from django.http import HttpResponseServerError
            return HttpResponseServerError("Internal Server Error")




class RequestContextFilter(logging.Filter):
    def filter(self, record):
        request = request_context.get()
        user_id = username = ''
        ip = user_agent = ''

        if request:
            record.request_id = getattr(request, 'id', '')
            ip = request.META.get('REMOTE_ADDR', '')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = getattr(request.user, 'id', None)
                try:
                    if hasattr(request.user, "personalinfo") and hasattr(request.user.personalinfo, "full_name"):
                        username = request.user.personalinfo.full_name
                    else:
                        username = getattr(request.user, "username", "")
                except Exception:
                    username = getattr(request.user, 'username', '')
        else:
            record.request_id = ''

        record.ip = ip
        record.user_agent = user_agent
        record.user_id = user_id
        record.username = username

        return True

class ExcludeAutoreloadFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('File')