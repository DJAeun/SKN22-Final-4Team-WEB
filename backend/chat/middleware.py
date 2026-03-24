import logging

from .models import VisitLog

logger = logging.getLogger(__name__)

# Paths to skip (API, static, admin, health checks, etc.)
SKIP_PREFIXES = (
    '/api/',
    '/static/',
    '/media/',
    '/health/',
    '/admin/',
    '/favicon.ico',
    '/ws/',
)


class VisitLogMiddleware:
    """
    Records a visit_logs row for every page-level HTTP request.
    Skips API, static, WebSocket, and admin requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only log successful page views (2xx/3xx), skip non-page requests
        try:
            path = request.path
            if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
                return response

            # Only log GET requests (actual page visits)
            if request.method != 'GET':
                return response

            # Only log successful responses
            if response.status_code >= 400:
                return response

            user = request.user if request.user.is_authenticated else None
            VisitLog.objects.create(user=user)

        except Exception as e:
            # Never let visit logging break the response
            logger.error(f"VisitLog error: {e}", exc_info=True)

        return response
