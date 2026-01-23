import logging
import time
from functools import wraps
from django.conf import settings
from django.db import connection

logger = logging.getLogger('formacion.performance')
business_logger = logging.getLogger('formacion.business')
anomaly_logger = logging.getLogger('formacion.anomaly')

def log_performance(func):
    """
    Decorador para logging de performance de funciones.
    Registra tiempo de ejecución, queries de BD y uso de memoria.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        initial_queries = len(connection.queries)

        try:
            result = func(*args, **kwargs)

            duration = (time.time() - start_time) * 1000  # ms
            db_queries = len(connection.queries) - initial_queries
            db_time = sum(float(q.get('time', 0)) for q in connection.queries[initial_queries:]) * 1000

            logger.info(
                f"Function {func.__name__} completed",
                extra={
                    'user': getattr(args[0] if args and hasattr(args[0], 'user') else None, 'username', 'system'),
                    'action': func.__name__,
                    'resource': func.__module__,
                    'duration': f"{duration:.2f}",
                    'db_queries': db_queries,
                    'db_time': f"{db_time:.2f}"
                }
            )

            # Detección de anomalías de performance
            if duration > 5000:  # 5 segundos
                anomaly_logger.warning(
                    f"Slow function execution: {func.__name__}",
                    extra={
                        'pattern': 'slow_function',
                        'severity': 'high',
                        'function': func.__name__,
                        'duration': f"{duration:.2f}",
                        'db_queries': db_queries
                    }
                )

            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"Function {func.__name__} failed after {duration:.2f}ms",
                extra={
                    'user': getattr(args[0] if args and hasattr(args[0], 'user') else None, 'username', 'system'),
                    'action': func.__name__,
                    'resource': func.__module__,
                    'duration': f"{duration:.2f}",
                    'error': str(e)
                }
            )
            raise

    return wrapper


def log_business_operation(operation_name, user=None, resource=None, extra_data=None):
    """
    Decorador para logging de operaciones de negocio críticas.

    Args:
        operation_name (str): Nombre de la operación
        user: Usuario que realiza la operación (opcional, se obtiene del request)
        resource: Recurso afectado (opcional)
        extra_data (dict): Datos adicionales para el log
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Intentar obtener el usuario del primer argumento si es un request
            request = args[0] if args and hasattr(args[0], 'user') else None
            current_user = user or (request.user if request else None)
            username = getattr(current_user, 'username', 'system') if current_user else 'system'

            log_data = {
                'user': username,
                'action': operation_name,
                'resource': resource or func.__module__
            }

            if extra_data:
                log_data.update(extra_data)

            business_logger.info(
                f"Business operation: {operation_name}",
                extra=log_data
            )

            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_anomaly(pattern, severity, message, **extra_data):
    """
    Función utilitaria para logging de anomalías detectadas.

    Args:
        pattern (str): Patrón de anomalía detectado
        severity (str): Severidad ('low', 'medium', 'high', 'critical')
        message (str): Mensaje descriptivo
        **extra_data: Datos adicionales
    """
    anomaly_logger.log(
        getattr(logging, severity.upper(), logging.WARNING),
        message,
        extra={
            'pattern': pattern,
            'severity': severity,
            **extra_data
        }
    )


def validate_business_rule(rule_name, condition, error_message=None, user=None):
    """
    Valida reglas de negocio y registra violaciones.

    Args:
        rule_name (str): Nombre de la regla
        condition (bool): Condición que debe ser True
        error_message (str): Mensaje si la condición falla
        user: Usuario relacionado

    Returns:
        bool: True si la regla se cumple, False si se viola
    """
    if not condition:
        username = getattr(user, 'username', 'system') if user else 'system'

        anomaly_logger.error(
            f"Business rule violation: {rule_name}",
            extra={
                'pattern': 'business_rule_violation',
                'severity': 'high',
                'user': username,
                'rule': rule_name,
                'message': error_message or f"Rule {rule_name} violated"
            }
        )

        business_logger.warning(
            f"Business rule {rule_name} violated by {username}",
            extra={
                'user': username,
                'action': 'rule_violation',
                'resource': rule_name,
                'message': error_message
            }
        )

        return False
    return True


class AnomalyDetector:
    """
    Clase para detección de anomalías en tiempo real.
    """

    def __init__(self):
        self.patterns = {
            'login_failures': {'threshold': 5, 'window': 300},  # 5 fallos en 5 minutos
            'course_capacity': {'threshold': 0, 'window': None},  # Capacidad negativa
            'response_time': {'threshold': 10000, 'window': None},  # 10 segundos
            'db_queries': {'threshold': 100, 'window': None},  # 100 queries por request
        }
        self.counters = {}

    def check_login_failures(self, ip, username):
        """Verifica intentos de login fallidos."""
        key = f"login_fail_{ip}_{username}"
        current_time = time.time()

        if key not in self.counters:
            self.counters[key] = []

        # Limpiar entradas antiguas
        self.counters[key] = [t for t in self.counters[key]
                             if current_time - t < self.patterns['login_failures']['window']]

        self.counters[key].append(current_time)

        if len(self.counters[key]) >= self.patterns['login_failures']['threshold']:
            log_anomaly(
                'brute_force',
                'critical',
                f"Brute force attack detected from IP {ip} for user {username}",
                ip=ip,
                user=username,
                attempts=len(self.counters[key])
            )
            return True
        return False

    def check_course_capacity(self, course, available_spots):
        """Verifica capacidad negativa de cursos."""
        if available_spots < 0:
            log_anomaly(
                'negative_capacity',
                'high',
                f"Course {course.nombre} has negative capacity: {available_spots}",
                course_id=course.id,
                course_name=course.nombre,
                available_spots=available_spots
            )
            return True
        return False

    def check_performance(self, response_time, db_queries):
        """Verifica métricas de performance."""
        anomalies = []

        if response_time > self.patterns['response_time']['threshold']:
            anomalies.append('slow_response')

        if db_queries > self.patterns['db_queries']['threshold']:
            anomalies.append('high_query_count')

        if anomalies:
            severity = 'critical' if response_time > 30000 else 'high'
            log_anomaly(
                ','.join(anomalies),
                severity,
                f"Performance anomaly detected: {response_time:.2f}ms, {db_queries} queries",
                response_time=response_time,
                db_queries=db_queries
            )
            return True
        return False


# Instancia global del detector de anomalías
anomaly_detector = AnomalyDetector()