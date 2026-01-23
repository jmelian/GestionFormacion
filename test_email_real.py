#!/usr/bin/env python
"""
Script para probar el envío real de emails con el nuevo remitente configurado.
"""
import os
import sys
import django
from unittest.mock import patch

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'formacion_demo.settings')
django.setup()

from django.conf import settings
from formacion.utils import send_notification_email

def test_real_email():
    """Función para enviar emails reales de prueba"""
    print("INICIANDO TEST DE ENVÍO DE EMAILS REALES")
    print("=" * 50)

    # Destinatarios de prueba
    recipients = [
        'javimelian@gmail.com',
        'jmelher@contactel.es'
    ]

    print(f"Destinatarios: {', '.join(recipients)}")
    print(f"Remitente configurado: {settings.DEFAULT_FROM_EMAIL}")
    print(f"Servidor SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"Usuario SMTP: {settings.EMAIL_HOST_USER}")
    print()

    # Datos del email de prueba
    subject = 'Test de Configuracion de Remitente - Sistema de Formacion'
    template_name = 'notificacion_info'
    context = {
        'usuario': type('MockUser', (), {'email': 'test@example.com', 'username': 'testuser'})(),
        'mensaje': 'Este es un email de prueba para verificar que el remitente aparece correctamente como "notificacion@gestionFormacion"',
        'url': '/test-url/',
        'tipo': 'info',
        'dominio': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
    }

    # Mock del template para evitar errores de archivo
    html_content = '''<html><body><h2>Test de Configuracion de Email</h2><p><strong>Remitente:</strong> notificacion@gestionFormacion</p><p><strong>Mensaje:</strong> Este es un email de prueba para verificar que el remitente aparece correctamente.</p><p><em>Este email confirma que la configuracion de DEFAULT_FROM_EMAIL funciona correctamente.</em></p></body></html>'''

    success_count = 0

    for recipient in recipients:
        try:
            print(f"Enviando email a: {recipient}")

            # Mock del template
            with patch('formacion.utils.render_to_string') as mock_render:
                mock_render.return_value = html_content

                # Enviar email usando la función real
                result = send_notification_email(
                    to_email=recipient,
                    subject=subject,
                    template_name=template_name,
                    context=context
                )

                if result:
                    success_count += 1
                    print(f"Email enviado exitosamente a {recipient}")
                else:
                    print(f"Error al enviar email a {recipient}")

        except Exception as e:
            print(f"Excepcion al enviar a {recipient}: {str(e)}")

    print("\n" + "=" * 50)
    print(f"RESUMEN: {success_count}/{len(recipients)} emails enviados exitosamente")

    if success_count > 0:
        print("\nEXITO! Los emails se enviaron correctamente.")
        print(f"Revisa tu bandeja de entrada en {recipients[0]} y {recipients[1]}")
        print("Verifica que el remitente aparece como: notificacion@gestionFormacion")
    else:
        print("\nNo se pudo enviar ningun email.")
        print("Revisa la configuracion SMTP en el archivo .env")

    print("\nCONFIGURACION ACTUAL:")
    print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"   EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"   EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")

if __name__ == '__main__':
    test_real_email()