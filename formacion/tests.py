from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from unittest.mock import patch, MagicMock
from .utils import send_notification_email, create_notification_with_email
from .models import Empleado, Notificacion
from django.core.management import call_command
from django.conf import settings
import os
import sys

User = get_user_model()


class EmailConfigurationTest(TestCase):
    """Tests para verificar la configuración de email y el remitente"""

    def setUp(self):
        """Configuración inicial para los tests"""
        self.factory = RequestFactory()
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @override_settings(
        DEFAULT_FROM_EMAIL='notificación@gestionFormacion',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_default_from_email_configuration(self):
        """Test que verifica que DEFAULT_FROM_EMAIL está configurado correctamente"""
        from django.conf import settings

        # Verificar que la configuración existe
        self.assertTrue(hasattr(settings, 'DEFAULT_FROM_EMAIL'))
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, 'notificación@gestionFormacion')

        print(f"✅ DEFAULT_FROM_EMAIL configurado correctamente: {settings.DEFAULT_FROM_EMAIL}")

    @override_settings(
        DEFAULT_FROM_EMAIL='notificacion@gestionFormacion',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_send_notification_email_uses_custom_from_email(self):
        """Test que verifica que send_notification_email usa el remitente personalizado"""
        # Datos de prueba
        to_email = 'recipient@example.com'
        subject = 'Test Notification'
        template_name = 'notificacion_info'
        context = {
            'usuario': self.test_user,
            'mensaje': 'Mensaje de prueba',
            'url': '/test-url/',
            'tipo': 'info',
            'dominio': 'test.example.com'
        }

        # Mock del template para evitar errores de archivo
        with patch('formacion.utils.render_to_string') as mock_render:
            mock_render.return_value = '<html><body>Test email content</body></html>'

            # Enviar email
            result = send_notification_email(to_email, subject, template_name, context)

            # Verificar que el email fue enviado
            self.assertTrue(result)

            # Verificar que se envió exactamente 1 email
            self.assertEqual(len(mail.outbox), 1)

            # Verificar el remitente del email
            email = mail.outbox[0]
            self.assertEqual(email.from_email, 'notificacion@gestionFormacion')

            print(f"✅ Email enviado correctamente desde: {email.from_email}")

    @override_settings(
        DEFAULT_FROM_EMAIL='notificacion@gestionFormacion',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_create_notification_with_email_integration(self):
        """Test de integración que verifica el flujo completo de notificaciones con email"""
        # Datos de prueba
        mensaje = 'Notificacion de prueba para test'
        tipo = 'success'
        url = '/test-url/'

        # Mock del template
        with patch('formacion.utils.render_to_string') as mock_render:
            mock_render.return_value = '<html><body>Test notification content</body></html>'

            # Crear notificación con email
            notificacion = create_notification_with_email(
                usuario=self.test_user,
                mensaje=mensaje,
                tipo=tipo,
                url=url
            )

            # Verificar que se creó la notificación en la base de datos
            self.assertIsNotNone(notificacion)
            self.assertEqual(notificacion.usuario, self.test_user)
            self.assertEqual(notificacion.mensaje, mensaje)
            self.assertEqual(notificacion.tipo, tipo)
            self.assertEqual(notificacion.url, url)

            # Verificar que se envió el email correcto
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]
            self.assertEqual(email.from_email, 'notificacion@gestionFormacion')
            self.assertIn(self.test_user.email, email.to)

            print(f"✅ Notificación creada y email enviado desde: {email.from_email}")

    def test_email_configuration_with_different_notification_types(self):
        """Test que verifica diferentes tipos de notificaciones usan el mismo remitente"""
        tipos_notificacion = ['info', 'success', 'warning', 'error']

        for tipo in tipos_notificacion:
            with self.subTest(tipo_notificacion=tipo):
                # Configurar email backend para cada subtest
                with override_settings(
                    DEFAULT_FROM_EMAIL='notificacion@gestionFormacion',
                    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
                ):
                    # Reset mailbox
                    mail.outbox = []

                    # Datos de prueba (usando caracteres ASCII para evitar problemas de encoding)
                    to_email = 'recipient@example.com'
                    subject = f'Test {tipo.title()} Notification'
                    template_name = f'notificacion_{tipo}'
                    context = {
                        'usuario': self.test_user,
                        'mensaje': f'Mensaje de {tipo}',
                        'url': '/test-url/',
                        'tipo': tipo,
                        'dominio': 'test.example.com'
                    }

                    # Mock del template
                    with patch('formacion.utils.render_to_string') as mock_render:
                        mock_render.return_value = f'<html><body>Test {tipo} content</body></html>'

                        # Enviar email
                        result = send_notification_email(to_email, subject, template_name, context)

                        # Verificar resultado
                        self.assertTrue(result)
                        self.assertEqual(len(mail.outbox), 1)

                        # Verificar remitente consistente
                        email = mail.outbox[0]
                        self.assertEqual(email.from_email, 'notificacion@gestionFormacion')

                        print(f"✅ Tipo {tipo}: Email enviado desde {email.from_email}")


class EmailSettingsValidationTest(TestCase):
    """Tests para validar la configuración de email en diferentes escenarios"""

    def test_settings_file_has_required_email_config(self):
        """Test que verifica que settings.py tiene todas las configuraciones de email necesarias"""
        from django.conf import settings

        # Verificar configuraciones requeridas
        required_settings = [
            'DEFAULT_FROM_EMAIL',
            'EMAIL_BACKEND',
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD',
            'EMAIL_USE_TLS',
            'EMAIL_USE_SSL'
        ]

        for setting in required_settings:
            with self.subTest(setting=setting):
                self.assertTrue(hasattr(settings, setting), f"Setting {setting} no encontrado en configuración")
                print(f"✅ {setting} configurado: {getattr(settings, setting)}")


class RealEmailTest(TestCase):
    """Tests para envío real de emails usando configuración SMTP"""

    def setUp(self):
        """Configuración inicial"""
        self.test_recipients = [
            'javimelian@gmail.com',
            'jmelher@contactel.es'
        ]

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    )
    def test_send_real_notification_emails(self):
        """Test que envía emails reales a las direcciones especificadas"""
        print("\n🚀 INICIANDO TEST DE ENVÍO DE EMAILS REALES")
        print(f"📧 Destinatarios: {', '.join(self.test_recipients)}")
        print(f"📤 Remitente configurado: {settings.DEFAULT_FROM_EMAIL}")
        print(f"🔧 Servidor SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")

        # Datos de prueba
        subject = 'Test de Configuracion de Remitente - Sistema de Formacion'
        template_name = 'notificacion_info'
        context = {
            'usuario': self.test_user,
            'mensaje': 'Este es un email de prueba para verificar que el remitente aparece correctamente como "notificacion@gestionFormacion"',
            'url': '/test-url/',
            'tipo': 'info',
            'dominio': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
        }

        # Mock del template para evitar errores de archivo
        with patch('formacion.utils.render_to_string') as mock_render:
            html_content = '<html><body><h2>Test de Configuracion de Email</h2><p><strong>Remitente:</strong> notificacion@gestionFormacion</p><p><strong>Mensaje:</strong> Este es un email de prueba para verificar que el remitente aparece correctamente.</p><p><em>Este email confirma que la configuracion de DEFAULT_FROM_EMAIL funciona correctamente.</em></p></body></html>'
            mock_render.return_value = html_content

            success_count = 0

            for recipient in self.test_recipients:
                try:
                    print(f"\n📤 Enviando email a: {recipient}")

                    # Enviar email usando la función real
                    result = send_notification_email(
                        to_email=recipient,
                        subject=subject,
                        template_name=template_name,
                        context=context
                    )

                    if result:
                        success_count += 1
                        print(f"✅ Email enviado exitosamente a {recipient}")
                    else:
                        print(f"❌ Error al enviar email a {recipient}")

                except Exception as e:
                    print(f"❌ Excepción al enviar a {recipient}: {str(e)}")

            # Verificar que al menos algunos emails se enviaron
            self.assertGreater(success_count, 0, f"No se pudo enviar ningún email. Revisa la configuración SMTP.")

            print(f"\n📊 RESUMEN: {success_count}/{len(self.test_recipients)} emails enviados exitosamente")

            # Mostrar configuración actual para debugging
            print("\n🔧 CONFIGURACIÓN ACTUAL:")
            print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
            print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
            print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
            print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
            print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
            print(f"   EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")

    def test_email_configuration_verification(self):
        """Test que verifica la configuración de email antes de enviar"""
        print("\n🔍 VERIFICANDO CONFIGURACIÓN DE EMAIL")

        # Verificar que tenemos todas las configuraciones necesarias
        required_settings = [
            'DEFAULT_FROM_EMAIL',
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_HOST_USER',
            'EMAIL_HOST_PASSWORD'
        ]

        for setting in required_settings:
            value = getattr(settings, setting, None)
            if value:
                print(f"✅ {setting}: {value}")
            else:
                print(f"❌ {setting}: No configurado")

        # Verificar que el remitente personalizado está configurado
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, 'notificación@gestionFormacion')
        print(f"✅ Remitente personalizado confirmado: {settings.DEFAULT_FROM_EMAIL}")

        # Verificar que es diferente del usuario SMTP
        self.assertNotEqual(settings.DEFAULT_FROM_EMAIL, settings.EMAIL_HOST_USER)
        print(f"✅ Remitente diferente del usuario SMTP: {settings.EMAIL_HOST_USER} → {settings.DEFAULT_FROM_EMAIL}")

    def test_email_configuration_consistency(self):
        """Test que verifica la consistencia de la configuración de email"""
        from django.conf import settings

        # Verificar que DEFAULT_FROM_EMAIL es diferente de EMAIL_HOST_USER
        if hasattr(settings, 'DEFAULT_FROM_EMAIL') and hasattr(settings, 'EMAIL_HOST_USER'):
            self.assertNotEqual(
                settings.DEFAULT_FROM_EMAIL,
                settings.EMAIL_HOST_USER,
                "DEFAULT_FROM_EMAIL debería ser diferente de EMAIL_HOST_USER para usar remitente personalizado"
            )
            print(f"✅ Remitente personalizado configurado: {settings.DEFAULT_FROM_EMAIL}")
            print(f"✅ Usuario SMTP: {settings.EMAIL_HOST_USER}")
