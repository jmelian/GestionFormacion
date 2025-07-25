# formacion/context_processors.py
from .models import Notificacion, Empleado # Asegúrate de importar Empleado y Notificacion
from django.conf import settings

# Importamos las funciones específicas de tus vistas para determinar los roles
# (Quitamos es_rrhh_o_formacion_o_direccion, ya que no existe en tus views.py)
from .views import es_coordinador, es_formacion_o_direccion 

def global_context(request):
    """
    Procesador de contexto global para añadir variables comunes a todas las plantillas.
    Incluye el número de notificaciones no leídas y los roles del usuario.
    """
    context = {}
    user = request.user

    if user.is_authenticated:
        # Notificaciones
        # Asumiendo que 'usuario' es el campo ForeignKey en Notificacion que apunta a Empleado
        context['num_notificaciones'] = Notificacion.objects.filter(usuario=user, leida=False).count()

        # Roles del usuario
        grupos_usuario = user.groups.values_list('name', flat=True)

        context['es_rrhh'] = settings.GRUPO_RRHH in grupos_usuario
        context['es_formacion'] = settings.GRUPO_FORMACION in grupos_usuario
        context['es_direccion'] = settings.GRUPO_DIRECCION in grupos_usuario
        context['es_empleado'] = settings.GRUPO_EMPLEADO in grupos_usuario # Si tienes un grupo base para todos los empleados

        # Usamos las funciones de tus vistas para determinar roles combinados si es necesario
        context['es_coordinador'] = es_coordinador(user)
        context['es_formacion_o_direccion'] = es_formacion_o_direccion(user)
        
        # Ya no necesitamos context['es_rrhh_o_formacion_o_direccion'] aquí
        
    return context