import logging
from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.auth.models import User
from .models import Empleado, Curso, Participacion, Titulacion, Notificacion, SolicitudCurso
from .utils import create_notification_with_email

logger = logging.getLogger('formacion.business')
security_logger = logging.getLogger('formacion.security')
anomaly_logger = logging.getLogger('formacion.anomaly')

# --- Señales de Autenticación ---

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Registra logins exitosos con información de seguridad."""
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    security_logger.info(
        f"User login successful: {user.username}",
        extra={
            'user': user.username,
            'ip': ip,
            'user_agent': user_agent[:200],
            'action': 'login_success'
        }
    )

    # Detección de login desde IP inusual
    if hasattr(user, 'last_login_ip') and user.last_login_ip != ip:
        anomaly_logger.info(
            f"Login from different IP: {user.username}",
            extra={
                'pattern': 'ip_change',
                'severity': 'low',
                'user': user.username,
                'ip': ip,
                'previous_ip': getattr(user, 'last_login_ip', 'unknown')
            }
        )

    # Actualizar IP del último login
    if hasattr(user, 'last_login_ip'):
        user.last_login_ip = ip
        user.save(update_fields=['last_login_ip'])


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Registra intentos de login fallidos."""
    username = credentials.get('username', 'unknown')
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    security_logger.warning(
        f"Failed login attempt for user: {username}",
        extra={
            'user': username,
            'ip': ip,
            'user_agent': user_agent[:200],
            'action': 'login_failed'
        }
    )

    # Contar intentos fallidos por IP (lógica simple)
    # En producción, usar Redis o similar para tracking más sofisticado
    failed_attempts = getattr(request, '_failed_login_count', 0) + 1
    request._failed_login_count = failed_attempts

    if failed_attempts >= 5:  # Umbral configurable
        anomaly_logger.warning(
            f"Multiple failed login attempts from IP: {ip}",
            extra={
                'pattern': 'brute_force_attempt',
                'severity': 'high',
                'user': username,
                'ip': ip,
                'attempts': failed_attempts
            }
        )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Registra logouts."""
    ip = get_client_ip(request)

    security_logger.info(
        f"User logout: {user.username}",
        extra={
            'user': user.username,
            'ip': ip,
            'action': 'logout'
        }
    )


# --- Señales de Modelos de Negocio ---

@receiver(pre_save, sender=Curso)
def log_curso_changes(sender, instance, **kwargs):
    """Registra cambios en cursos."""
    if instance.pk:  # Si es una actualización
        try:
            old_instance = Curso.objects.get(pk=instance.pk)
            changes = {}
            for field in ['nombre', 'plazas_totales', 'plazas_disponibles', 'fecha_inicio', 'fecha_fin']:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}

            if changes:
                logger.info(
                    f"Curso modified: {instance.nombre} (ID: {instance.pk})",
                    extra={
                        'user': getattr(instance, '_modified_by', 'system'),
                        'action': 'curso_modified',
                        'resource': f"curso_{instance.pk}",
                        'changes': changes
                    }
                )

                # Detección de cambios críticos
                if 'plazas_disponibles' in changes and changes['plazas_disponibles']['new'] < 0:
                    anomaly_logger.error(
                        f"Critical: Course {instance.nombre} has negative available spots",
                        extra={
                            'pattern': 'negative_capacity',
                            'severity': 'critical',
                            'resource': f"curso_{instance.pk}"
                        }
                    )
        except Curso.DoesNotExist:
            pass  # Nuevo curso


@receiver(post_save, sender=Participacion)
def log_participacion_changes(sender, instance, created, **kwargs):
    """Registra cambios en participaciones."""
    action = 'participacion_created' if created else 'participacion_modified'

    logger.info(
        f"Participacion {'created' if created else 'modified'}: {instance.empleado.username} -> {instance.curso.nombre}",
        extra={
            'user': getattr(instance, '_modified_by', instance.empleado.username),
            'action': action,
            'resource': f"participacion_{instance.pk}",
            'estado': instance.estado,
            'curso_id': instance.curso.id,
            'empleado_id': instance.empleado.id
        }
    )

    # Detección de anomalías en participaciones
    if created:
        # Verificar si el empleado ya tiene muchas participaciones activas
        active_participations = Participacion.objects.filter(
            empleado=instance.empleado,
            estado__in=['confirmado', 'asistido']
        ).count()

        if active_participations > 10:  # Umbral configurable
            anomaly_logger.warning(
                f"Employee {instance.empleado.username} has {active_participations} active participations",
                extra={
                    'pattern': 'high_participation_count',
                    'severity': 'medium',
                    'user': instance.empleado.username,
                    'resource': f"participacion_{instance.pk}"
                }
            )


@receiver(post_save, sender=Titulacion)
def log_titulacion_changes(sender, instance, created, **kwargs):
    """Registra cambios en titulaciones."""
    action = 'titulacion_created' if created else 'titulacion_modified'

    logger.info(
        f"Titulacion {'created' if created else 'modified'}: {instance.nombre} for {instance.empleado.username}",
        extra={
            'user': getattr(instance, '_modified_by', instance.empleado.username),
            'action': action,
            'resource': f"titulacion_{instance.pk}",
            'estado': instance.estado,
            'tipo_titulacion': instance.tipo_titulacion
        }
    )

    # Notificación automática cuando una titulación cambia a pendiente
    if instance.estado == 'pendiente' and created:
        # Buscar usuarios RRHH para notificar
        from django.contrib.auth.models import Group
        try:
            rrhh_group = Group.objects.get(name='RRHH')
            rrhh_users = rrhh_group.user_set.all()

            for rrhh_user in rrhh_users:
                create_notification_with_email(
                    usuario=rrhh_user,
                    mensaje=f"Nueva titulación pendiente de validación: {instance.nombre} de {instance.empleado.get_full_name()}",
                    tipo='info',
                    url=f"/formacion/titulaciones_pendientes_rrhh/"
                )
        except Group.DoesNotExist:
            logger.warning("Grupo RRHH no encontrado para notificaciones de titulaciones")


@receiver(post_save, sender=SolicitudCurso)
def log_solicitud_curso_changes(sender, instance, created, **kwargs):
    """Registra cambios en solicitudes de curso."""
    action = 'solicitud_created' if created else 'solicitud_modified'

    logger.info(
        f"Solicitud {'created' if created else 'modified'}: {instance.titulo_curso_solicitado} by {instance.solicitante.username}",
        extra={
            'user': instance.solicitante.username,
            'action': action,
            'resource': f"solicitud_{instance.pk}",
            'estado': instance.estado
        }
    )

    # Detección de solicitudes inusuales
    if created:
        # Contar solicitudes recientes del mismo usuario
        recent_solicitudes = SolicitudCurso.objects.filter(
            solicitante=instance.solicitante,
            fecha_solicitud__gte=instance.fecha_solicitud.replace(hour=0, minute=0, second=0)
        ).count()

        if recent_solicitudes > 3:  # Umbral configurable
            anomaly_logger.info(
                f"High solicitud frequency: {instance.solicitante.username} has {recent_solicitudes} requests today",
                extra={
                    'pattern': 'high_request_frequency',
                    'severity': 'low',
                    'user': instance.solicitante.username,
                    'resource': f"solicitud_{instance.pk}"
                }
            )


@receiver(post_delete, sender=Curso)
def log_curso_deletion(sender, instance, **kwargs):
    """Registra eliminación de cursos."""
    logger.warning(
        f"Curso deleted: {instance.nombre} (ID: {instance.pk})",
        extra={
            'user': getattr(instance, '_deleted_by', 'system'),
            'action': 'curso_deleted',
            'resource': f"curso_{instance.pk}"
        }
    )


@receiver(post_delete, sender=Participacion)
def log_participacion_deletion(sender, instance, **kwargs):
    """Registra eliminación de participaciones."""
    logger.warning(
        f"Participacion deleted: {instance.empleado.username} from {instance.curso.nombre}",
        extra={
            'user': getattr(instance, '_deleted_by', 'system'),
            'action': 'participacion_deleted',
            'resource': f"participacion_{instance.pk}"
        }
    )


def get_client_ip(request):
    """Obtiene la IP real del cliente considerando proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
