from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
import smtplib

logger = logging.getLogger(__name__)


class CustomSMTPBackend:
    """
    Custom SMTP backend that forces a specific hostname for EHLO/HELO command.
    This solves the issue with Docker containers having unqualified hostnames.
    """
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None, **kwargs):
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        self.username = username or settings.EMAIL_HOST_USER
        self.password = password or settings.EMAIL_HOST_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.EMAIL_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.EMAIL_USE_SSL
        self.timeout = timeout
        self.fail_silently = fail_silently
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile
        # Force a fully qualified hostname for SMTP
        self.hostname = 'gesform.contactel.es'
        self.connection = None

    def open(self):
        """
        Ensures we have a connection to the email server.
        Returns whether or not a new connection was required.
        """
        if self.connection:
            return False
        try:
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            else:
                self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

            # Force our custom hostname in the EHLO command
            self.connection.ehlo(self.hostname)

            if self.use_tls:
                self.connection.starttls()
                # Re-do EHLO after STARTTLS with our custom hostname
                self.connection.ehlo(self.hostname)

            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise

    def close(self):
        """Closes the connection to the email server."""
        if self.connection is None:
            return
        try:
            self.connection.quit()
        except Exception:
            if not self.fail_silently:
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        """
        Sends one or more EmailMessage objects and returns the number of email
        messages sent.
        """
        if not email_messages:
            return 0
        new_conn_created = self.open()
        if not self.connection:
            return 0
        num_sent = 0
        for message in email_messages:
            sent = self._send(message)
            if sent:
                num_sent += 1
        if new_conn_created:
            self.close()
        return num_sent

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        try:
            self.connection.sendmail(
                email_message.from_email,
                email_message.recipients(),
                email_message.message().as_bytes(linesep='\r\n')
            )
        except Exception:
            if not self.fail_silently:
                raise
            return False
        return True


def send_notification_email(to_email, subject, template_name, context):
    """
    Envía un email de notificación usando una plantilla HTML con backend SMTP personalizado.

    Args:
        to_email (str): Dirección de email del destinatario
        subject (str): Asunto del email
        template_name (str): Nombre de la plantilla HTML (sin extensión)
        context (dict): Contexto para renderizar la plantilla

    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    from django.core.mail import EmailMessage

    logger.debug(f"Intentando enviar email - Destinatario: {to_email}, Asunto: {subject}, Template: {template_name}")

    try:
        # Renderizar la plantilla HTML
        template_path = f'formacion/email/{template_name}.html'
        logger.debug(f"Renderizando template: {template_path}")
        html_message = render_to_string(template_path, context)
        logger.debug(f"Template renderizado exitosamente, tamaño: {len(html_message)} caracteres")

        # Configuración del email
        from_email = settings.DEFAULT_FROM_EMAIL
        logger.debug(f"Configuración email - From: {from_email}, Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}, SSL: {settings.EMAIL_USE_SSL}")

        # Crear mensaje de email usando EmailMessage
        email = EmailMessage(
            subject=subject,
            body=html_message,  # Mensaje HTML directamente
            from_email=from_email,
            to=[to_email],
        )
        email.content_subtype = 'html'  # Establecer como HTML

        # Usar nuestro backend SMTP personalizado
        logger.debug("Ejecutando envío con CustomSMTPBackend...")
        backend = CustomSMTPBackend()
        num_sent = backend.send_messages([email])

        if num_sent > 0:
            logger.info(f"✅ Email enviado correctamente a {to_email} con asunto '{subject}' usando hostname personalizado")
            return True
        else:
            logger.error(f"❌ No se pudo enviar el email a {to_email} - backend devolvió 0 mensajes enviados")
            return False

    except Exception as e:
        # Log detallado del error
        logger.error(f"❌ Error al enviar email a {to_email}: {str(e)}")
        logger.error(f"Detalles del error - Tipo: {type(e).__name__}, Asunto: {subject}, Template: {template_name}")

        # Si es un error específico de SMTP, log adicional
        if hasattr(e, 'smtp_code'):
            logger.error(f"Código SMTP: {e.smtp_code}")
        if hasattr(e, 'smtp_error'):
            logger.error(f"Error SMTP: {e.smtp_error}")

        # Log del contexto para debugging
        logger.debug(f"Contexto del email: {context}")

        return False


def create_notification_with_email(usuario, mensaje, tipo='info', url=None):
    """
    Crea una notificación interna y envía un email si la notificación requiere intervención del usuario.

    Args:
        usuario: Instancia del modelo Empleado (usuario destinatario)
        mensaje (str): Mensaje de la notificación
        tipo (str): Tipo de notificación ('info', 'success', 'warning', 'error')
        url (str, optional): URL de la notificación

    Returns:
        Notificacion: La instancia de notificación creada
    """
    from .models import Notificacion

    logger.info(f"Creando notificación para {usuario.username}: tipo={tipo}, url={url}, email={getattr(usuario, 'email', None)}")

    # Crear la notificación interna
    try:
        notificacion = Notificacion.objects.create(
            usuario=usuario,
            mensaje=mensaje,
            tipo=tipo,
            url=url,
            leida=False
        )
        logger.info(f"Notificación interna creada exitosamente: ID={notificacion.id}")
    except Exception as e:
        logger.error(f"Error al crear notificación interna para {usuario.username}: {e}", exc_info=True)
        raise

    # Evaluar condiciones para envío de email
    has_url = bool(url)
    has_email_attr = hasattr(usuario, 'email')
    has_email_value = bool(getattr(usuario, 'email', None))

    logger.debug(f"Evaluando condiciones de email - URL: {has_url}, tiene_attr_email: {has_email_attr}, tiene_valor_email: {has_email_value}")

    # Si la notificación tiene una URL (indica acción requerida) y el usuario tiene email, enviar email
    if has_url and has_email_attr and has_email_value:
        logger.info(f"Intentando enviar email a {usuario.email} por notificación con URL (tipo: {tipo})")

        try:
            # Determinar el template y asunto basado en el tipo de notificación
            from django.conf import settings

            prefix = getattr(settings, 'EMAIL_SUBJECT_PREFIX', '[GesForm]')

            if tipo == 'success':
                template_name = 'notificacion_success'
                subject = f'{prefix} Notificación de Éxito - Sistema de Formación'
            elif tipo == 'warning':
                template_name = 'notificacion_warning'
                subject = f'{prefix} Notificación de Advertencia - Sistema de Formación'
            elif tipo == 'error':
                template_name = 'notificacion_error'
                subject = f'{prefix} Notificación de Error - Sistema de Formación'
            else:  # info
                template_name = 'notificacion_info'
                subject = f'{prefix} Notificación - Sistema de Formación'

            # Determinar el dominio correcto para los emails
            if 'xwiki.contactel.es' in str(settings.ALLOWED_HOSTS):
                dominio = 'xwiki.contactel.es:8082'
            elif settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS[0] != '*':
                dominio = settings.ALLOWED_HOSTS[0]
            else:
                dominio = 'localhost:8082'

            # Crear contexto para el email
            context = {
                'usuario': usuario,
                'mensaje': mensaje,
                'url': url,
                'tipo': tipo,
                'dominio': dominio,
            }

            logger.debug(f"Contexto de email preparado - template: {template_name}, subject: {subject}")

            # Enviar el email
            success = send_notification_email(
                to_email=usuario.email,
                subject=subject,
                template_name=template_name,
                context=context
            )

            if success:
                logger.info(f"✅ Email enviado exitosamente a {usuario.email} para notificación ID {notificacion.id}")
            else:
                logger.error(f"❌ Falló el envío de email a {usuario.email} para notificación ID {notificacion.id}")

        except Exception as e:
            logger.error(f"❌ Error inesperado al procesar envío de email para {usuario.email}: {e}", exc_info=True)

    else:
        # Log detallado de por qué NO se envía email
        reasons = []
        if not has_url:
            reasons.append("no tiene URL")
        if not has_email_attr:
            reasons.append("usuario no tiene atributo email")
        if not has_email_value:
            reasons.append("email del usuario está vacío")

        reason_str = ", ".join(reasons)
        logger.info(f"ℹ️ No se envía email para notificación ID {notificacion.id} - Razón: {reason_str}")

    return notificacion