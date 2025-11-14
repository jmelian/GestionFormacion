import time
import logging
import json
from django.conf import settings
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('formacion.performance')
security_logger = logging.getLogger('formacion.security')
anomaly_logger = logging.getLogger('formacion.anomaly')

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para logging detallado de requests/responses con monitoreo de performance
    y detección de anomalías.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.suspicious_patterns = [
            r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b.*\b(UNION|SCRIPT|EXEC|CMD)\b',
            r'<script[^>]*>.*?</script>',
            r'\b(OR|AND)\s+1\s*=\s*1\b',
            r'\b(admin|root|superuser)\b.*\b(password|pwd|pass)\b',
        ]

    def process_request(self, request):
        """Registra el inicio del request con información de seguridad."""
        request.start_time = time.time()

        # Reset query count for this request
        connection.queries_log.clear()

        # Log de seguridad para requests potencialmente sospechosos
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip = self.get_client_ip(request)
        path = request.path
        method = request.method

        # Detección de patrones sospechosos
        request_body = ''
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'body'):
                    request_body = request.body.decode('utf-8', errors='ignore')[:1000]  # Limitar tamaño
            except:
                request_body = 'Unable to decode body'

        # Verificar patrones de ataque comunes
        suspicious_detected = self._check_suspicious_patterns(path, request_body, user_agent)

        if suspicious_detected:
            anomaly_logger.warning(
                f"Suspicious request detected",
                extra={
                    'pattern': 'suspicious_request',
                    'severity': 'high',
                    'user': getattr(request.user, 'username', 'anonymous'),
                    'ip': ip,
                    'method': method,
                    'path': path,
                    'user_agent': user_agent[:200],
                    'request_size': len(request_body) if request_body else 0
                }
            )

        # Log normal de requests
        logger.info(
            f"Request started: {method} {path}",
            extra={
                'user': getattr(request.user, 'username', 'anonymous'),
                'ip': ip,
                'method': method,
                'path': path,
                'user_agent': user_agent[:200],
                'is_authenticated': request.user.is_authenticated
            }
        )

    def process_response(self, request, response):
        """Registra el fin del request con métricas de performance."""
        duration = (time.time() - request.start_time) * 1000  # Convertir a ms

        # Contar queries de base de datos
        db_queries = len(connection.queries)
        db_time = sum(float(q.get('time', 0)) for q in connection.queries) * 1000  # Convertir a ms

        ip = self.get_client_ip(request)
        user = getattr(request.user, 'username', 'anonymous')
        method = request.method
        path = request.path
        status_code = response.status_code

        # Detección de anomalías de performance
        if duration > getattr(settings, 'MONITORING_THRESHOLDS', {}).get('response_time', {}).get('critical', 10000):
            anomaly_logger.error(
                f"Critical response time detected: {duration:.2f}ms",
                extra={
                    'pattern': 'slow_response',
                    'severity': 'critical',
                    'user': user,
                    'ip': ip,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration': f"{duration:.2f}",
                    'db_queries': db_queries,
                    'db_time': f"{db_time:.2f}"
                }
            )
        elif duration > getattr(settings, 'MONITORING_THRESHOLDS', {}).get('response_time', {}).get('high', 5000):
            anomaly_logger.warning(
                f"High response time detected: {duration:.2f}ms",
                extra={
                    'pattern': 'slow_response',
                    'severity': 'high',
                    'user': user,
                    'ip': ip,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration': f"{duration:.2f}",
                    'db_queries': db_queries,
                    'db_time': f"{db_time:.2f}"
                }
            )

        # Detección de alta cantidad de queries
        if db_queries > 50:  # Umbral configurable
            anomaly_logger.warning(
                f"High database query count: {db_queries} queries",
                extra={
                    'pattern': 'high_query_count',
                    'severity': 'medium',
                    'user': user,
                    'ip': ip,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'duration': f"{duration:.2f}",
                    'db_queries': db_queries,
                    'db_time': f"{db_time:.2f}"
                }
            )

        # Log de performance normal
        logger.info(
            f"Request completed: {method} {path} -> {status_code} in {duration:.2f}ms",
            extra={
                'user': user,
                'ip': ip,
                'method': method,
                'path': path,
                'status_code': status_code,
                'duration': f"{duration:.2f}",
                'db_queries': db_queries,
                'db_time': f"{db_time:.2f}",
                'response_size': len(response.content) if hasattr(response, 'content') else 0
            }
        )

        return response

    @staticmethod
    def get_client_ip(request):
        """Obtiene la IP real del cliente considerando proxies."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _check_suspicious_patterns(self, path, body, user_agent):
        """Verifica si el request contiene patrones sospechosos."""
        import re

        text_to_check = f"{path} {body} {user_agent}".lower()

        for pattern in self.suspicious_patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True
        return False


class BusinessLogicLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para logging de operaciones de negocio críticas.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Registra operaciones de negocio críticas."""
        view_name = f"{view_func.__module__}.{view_func.__name__}"

        # Operaciones críticas que requieren logging especial
        critical_views = [
            'formacion.views.crear_editar_curso',
            'formacion.views.aprobar_solicitud_obligatoria',
            'formacion.views.rechazar_solicitud_obligatoria',
            'formacion.views.marcar_completado_unificado',
            'formacion.views.titulaciones_pendientes_rrhh',
        ]

        if view_name in critical_views:
            business_logger = logging.getLogger('formacion.business')
            business_logger.info(
                f"Business operation started: {view_name}",
                extra={
                    'user': getattr(request.user, 'username', 'anonymous'),
                    'action': view_func.__name__,
                    'resource': view_name.split('.')[-1],
                    'ip': RequestLoggingMiddleware.get_client_ip(request),
                    'method': request.method,
                    'path': request.path,
                    'status_code': 'unknown',  # Add missing field
                    'duration': 'unknown',     # Add missing field
                    'db_queries': 'unknown',   # Add missing field
                    'db_time': 'unknown'       # Add missing field
                }
            )