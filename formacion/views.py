# formacion/views.py
import datetime, os, mimetypes
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from .models import Empleado, Departamento, Curso, Participacion, Preseleccion, Notificacion, Proveedor, Proyecto, Area, PuestoDeTrabajo, Titulacion, TIPO_TITULACION_MECES_MAP, SolicitudCurso, RequisitoPuestoFormacion, EncuestaSatisfaccion
from .forms import EmpleadoCreationForm, EmpleadoProfileForm, CursoForm, PreseleccionForm, ParticipacionForm, TitulacionForm, SolicitudCursoForm, AprobarParticipacionForm, MarcarCompletadoForm, EncuestaSatisfaccionForm
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import date
from django.db.models import Count, Q, Prefetch
from django.contrib.auth import logout
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string # Para renderizar el contenido del email
from django.utils.html import strip_tags
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.transaction import TransactionManagementError
from django.http import FileResponse, Http404, HttpResponseForbidden
import logging


# Obtenemos una instancia del logger para este módulo.
# El nombre del logger será el nombre del módulo, por ejemplo, 'formacion.views'.
logger = logging.getLogger(__name__)

# --- Funciones de Comprobación de Roles ---
def is_in_group(user, group_name):
    """
    Función auxiliar para verificar si un usuario autenticado pertenece a un grupo específico.
    Es la base de todas las demás funciones de comprobación de roles.
    """
    is_member = user.is_authenticated and user.groups.filter(name=group_name).exists()
    logger.debug(f"Comprobando si el usuario '{user.username}' pertenece al grupo '{group_name}'. Resultado: {is_member}")
    return is_member

def es_empleado(user):
    """
    Verifica si un usuario es un empleado. 
    En esta lógica, un empleado es cualquier usuario autenticado que pertenece al grupo 'Empleado'.
    """
    result = is_in_group(user, settings.GRUPO_EMPLEADO)
    logger.debug(f"Resultado de la comprobación 'es_empleado' para '{user.username}': {result}")
    return result

def es_coordinador(user):
    """
    Verifica si un usuario es un coordinador. 
    Un coordinador debe pertenecer al grupo 'Coordinador' Y estar asignado como
    coordinador de su propio departamento en el modelo 'Departamento'.
    """
    if not user.is_authenticated:
        logger.debug("Comprobación 'es_coordinador' fallida: Usuario no autenticado.")
        return False

    # Verificamos la pertenencia al grupo de Django
    is_in_coord_group = is_in_group(user, settings.GRUPO_COORDINADOR)
    logger.debug(f"'{user.username}' ¿es miembro del grupo '{settings.GRUPO_COORDINADOR}'?: {is_in_coord_group}")

    # Verificamos si el usuario es coordinador de su propio departamento
    is_coordinator_of_own_department = False
    if hasattr(user, 'departamento') and user.departamento is not None:
        # Aquí verificamos si el coordinador del departamento del usuario ES el propio usuario.
        if hasattr(user.departamento, 'coordinador') and user.departamento.coordinador == user:
            is_coordinator_of_own_department = True
            logger.debug(f"'{user.username}' es coordinador de su departamento '{user.departamento.nombre}'.")
        else:
            logger.debug(f"'{user.username}' NO es coordinador del departamento al que pertenece.")
    else:
        logger.debug(f"El usuario '{user.username}' no tiene un departamento asignado.")
            
    final_result = is_in_coord_group and is_coordinator_of_own_department
    logger.info(f"Comprobación final 'es_coordinador' para '{user.username}': {final_result}")

    return final_result

def es_formacion(user):
    """Verifica si un usuario pertenece al grupo 'Formación'."""
    result = is_in_group(user, settings.GRUPO_FORMACION)
    logger.debug(f"Resultado de la comprobación 'es_formacion' para '{user.username}': {result}")
    return result

def es_formacion_o_direccion(user):
    """
    Función que combina las comprobaciones para los grupos 'Formación' y 'Dirección'.
    Útil para el decorador @user_passes_test.
    """
    result = es_formacion(user) or es_direccion(user)
    logger.debug(f"Resultado de la comprobación 'es_formacion_o_direccion' para '{user.username}': {result}")
    return result

def es_formacion_o_direccion_o_rrhh(user):
    """
    Función que combina las comprobaciones para los grupos 'Formación', 'Dirección' y 'RRHH'.
    Útil para el decorador @user_passes_test.
    """
    result = es_formacion(user) or es_direccion(user) or es_rrhh(user)
    logger.debug(f"Resultado de la comprobación 'es_formacion_o_direccion_o_rrhh' para '{user.username}': {result}")
    return result

def es_rrhh(user):
    """Verifica si un usuario pertenece al grupo 'RRHH'."""
    result = is_in_group(user, settings.GRUPO_RRHH)
    logger.debug(f"Resultado de la comprobación 'es_rrhh' para '{user.username}': {result}")
    return result

def es_direccion(user):
    """Verifica si un usuario pertenece al grupo 'Dirección'."""
    result = is_in_group(user, settings.GRUPO_DIRECCION)
    logger.debug(f"Resultado de la comprobación 'es_direccion' para '{user.username}': {result}")
    return result

def es_admin(user):
    """Verifica si un usuario es un superusuario."""
    is_admin_user = user.is_authenticated and user.is_superuser
    logger.debug(f"Resultado de la comprobación 'es_admin' para '{user.username}': {is_admin_user}")
    return is_admin_user

def custom_logout(request):
    """
    Vista para cerrar la sesión de un usuario.
    Después de cerrar la sesión, redirige a la página de login.
    """
    user_to_logout = request.user.username if request.user.is_authenticated else "Usuario anónimo"
    logger.info(f"Cerrando sesión para el usuario: '{user_to_logout}'")
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('formacion:login')

def solo_superusuarios(user):
    """
    Función para el decorador @user_passes_test que solo permite el acceso a superusuarios.
    """
    result = user.is_superuser
    logger.debug(f"Resultado de la comprobación 'solo_superusuarios' para '{user.username}': {result}")
    return result


# --- Vistas Generales ---

from django.views.generic import ListView


@login_required
def proximos_cursos(request):
    """
    Vista que muestra todos los cursos que aún no han comenzado o que inician hoy.
    Solo los usuarios autenticados pueden acceder a esta página.
    """
    # Agregamos un log de información para registrar el acceso del usuario a esta vista.
    # Esto es útil para monitorear la actividad en la aplicación.
    logger.info(f"El usuario '{request.user.username}' ha accedido a la vista de próximos cursos.")

    try:
        # Obtenemos los cursos cuya fecha de inicio es igual o posterior a la fecha actual.
        # Ordenamos los resultados por la fecha de inicio para que los cursos más cercanos aparezcan primero.
        cursos = Curso.objects.filter(fecha_inicio__gte=date.today()).order_by('fecha_inicio')
        
        # Agregamos un log de depuración para mostrar cuántos cursos se encontraron.
        # Esto ayuda a verificar que la consulta está funcionando como se espera.
        logger.debug(f"Se encontraron {cursos.count()} cursos futuros para mostrar.")

    except Exception as e:
        # En caso de un error en la consulta a la base de datos, registramos la excepción.
        # Esto es crucial para la depuración en caso de un fallo.
        logger.error(f"Error al obtener los próximos cursos para el usuario '{request.user.username}': {e}", exc_info=True)
        # Aseguramos que 'cursos' sea una lista vacía para evitar un error en el render.
        cursos = [] 

    # Renderizamos la plantilla 'proximos_cursos.html', pasando la lista de cursos encontrados.
    return render(request, 'formacion/proximos_cursos.html', {'cursos': cursos})


@login_required
def mis_cursos(request):
    """
    Vista que muestra los cursos en los que un usuario autenticado está participando.
    """
    logger.info(f"El usuario '{request.user.username}' ha accedido a la vista de mis cursos.")

    try:
        participaciones = Participacion.objects.filter(
            empleado=request.user,
            estado__in=['aceptado', 'asistido', 'completado', 'pendiente', 'solicitado', 'confirmada']
        ).select_related('curso').order_by('curso__fecha_inicio')
        
        logger.debug(f"Se encontraron {participaciones.count()} participaciones para el usuario '{request.user.username}'.")

    except Exception as e:
        logger.error(f"Error al obtener las participaciones para el usuario '{request.user.username}': {e}", exc_info=True)
        participaciones = []

    return render(request, 'formacion/mis_cursos.html', {'participaciones': participaciones})

@login_required
@user_passes_test(es_coordinador, login_url='formacion:dashboard')
def equipo_departamento(request):
    """
    Vista que muestra la lista de empleados del mismo departamento que el
    coordinador autenticado.
    """
    # Registramos que un coordinador ha accedido a esta vista.
    logger.info(f"El coordinador '{request.user.username}' ha accedido a la vista de equipo de departamento.")

    try:
        empleado_coordinador = request.user
        departamento = empleado_coordinador.departamento

        # Si el coordinador no tiene un departamento asignado, lo registramos,
        # mostramos un mensaje y lo redirigimos. Esto evita errores de permisos.
        if not departamento:
            logger.warning(f"El usuario '{request.user.username}' intentó acceder a la vista de equipo sin un departamento asignado.")
            messages.error(request, 'No estás asignado como coordinador de ningún departamento.')
            return redirect('formacion:dashboard')

        # Obtenemos todos los empleados del mismo departamento, ordenados alfabéticamente
        # por apellido y nombre para una mejor visualización.
        equipo = Empleado.objects.filter(departamento=departamento).order_by('last_name', 'first_name')

        # Registramos el número de miembros del equipo encontrados para fines de depuración.
        logger.debug(f"Se encontraron {equipo.count()} miembros del equipo para el departamento '{departamento.nombre}'.")

    except Exception as e:
        # Si ocurre un error inesperado durante la consulta, lo registramos como crítico
        # y redirigimos al usuario con un mensaje de error.
        logger.error(f"Error al obtener el equipo del departamento para el usuario '{request.user.username}': {e}", exc_info=True)
        messages.error(request, 'Ocurrió un error inesperado al cargar los datos del equipo.')
        return redirect('formacion:dashboard')

    # Renderizamos la plantilla con la información del departamento y la lista de empleados.
    return render(request, 'formacion/equipo_departamento.html', {
        'departamento': departamento,
        'equipo': equipo
    })

@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u), login_url='formacion:dashboard')
def certificados_pendientes_rrhh(request):
    """
    Vista que muestra y permite validar los certificados pendientes de
    los empleados. Accesible solo para usuarios de RRHH y administradores.
    """
    # Registramos el acceso a la vista.
    logger.info(f"El usuario '{request.user.username}' (RRHH/Admin) ha accedido a la vista de certificados pendientes.")

    if request.method == 'POST':
        # Manejamos la validación de un certificado.
        participacion_id = request.POST.get('participacion_id')
        
        # Protegemos el código con un bloque try...except para capturar errores
        # durante la validación del certificado.
        try:
            # Obtenemos la participación o mostramos un error si no existe.
            participacion = get_object_or_404(Participacion, id=participacion_id)
            
            # Verificamos si la participación ya ha sido validada.
            if not participacion.validado:
                participacion.validado = True
                participacion.save()
                
                # Registramos el éxito de la validación.
                logger.info(f"El certificado de '{participacion.empleado.get_full_name()}' para el curso '{participacion.curso.nombre}' ha sido validado correctamente.")
                messages.success(request, f"Certificado de {participacion.empleado.get_full_name()} validado correctamente.")
            else:
                # Si el certificado ya estaba validado, lo registramos como advertencia.
                logger.warning(f"Se intentó validar un certificado ya validado para el empleado '{participacion.empleado.get_full_name()}'.")
                messages.info(request, "Este certificado ya estaba validado.")

        except Exception as e:
            # Si ocurre un error inesperado, lo registramos como crítico y mostramos un mensaje.
            logger.error(f"Error crítico al validar el certificado con ID '{participacion_id}': {e}", exc_info=True)
            messages.error(request, f"Ocurrió un error al validar el certificado con ID {participacion_id}.")
            
        return redirect('formacion:certificados_pendientes_rrhh')
    
    # Manejamos la petición GET para mostrar la lista de certificados pendientes.
    try:
        # Obtenemos las participaciones que cumplen con los criterios para ser validadas.
        participaciones = Participacion.objects.filter(
            validado=False,
            estado__in=['completado', 'asistido'],
            nota_final__isnull=False
        ).exclude(nota_final="").select_related('empleado__departamento', 'curso')

        # Registramos el número de certificados pendientes encontrados para propósitos de depuración.
        logger.debug(f"Se encontraron {participaciones.count()} certificados pendientes de validación.")

    except Exception as e:
        # Si la consulta a la base de datos falla, lo registramos como un error crítico.
        logger.error(f"Error al obtener la lista de certificados pendientes para el usuario '{request.user.username}': {e}", exc_info=True)
        messages.error(request, 'Ocurrió un error al cargar la lista de certificados pendientes.')
        return redirect('formacion:dashboard')

    # Renderizamos la plantilla con la lista de participaciones.
    return render(request, 'formacion/certificados_pendientes_rrhh.html', {'participaciones': participaciones})


@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u), login_url='formacion:dashboard')
def titulaciones_pendientes_rrhh(request):
    """
    Vista para que el personal de RRHH y los administradores gestionen las
    titulaciones de los empleados que están pendientes de revisión.
    Permite validar y rechazar titulaciones.
    """
    # Registramos el acceso a la vista.
    logger.info(f"El usuario '{request.user.username}' (RRHH/Admin) ha accedido a la vista de titulaciones pendientes.")

    if request.method == 'POST':
        # Manejamos las acciones de 'validar' o 'rechazar'.
        titulacion_id = request.POST.get('titulacion_id')
        action = request.POST.get('action') # 'validar' o 'rechazar'
        
        try:
            # Obtenemos la titulación o devolvemos un 404 si no existe.
            titulacion = get_object_or_404(Titulacion, id=titulacion_id)
        except Exception as e:
            # Capturamos cualquier error inesperado al obtener la titulación.
            logger.error(f"Error al obtener la titulación con ID '{titulacion_id}': {e}", exc_info=True)
            messages.error(request, 'No se pudo encontrar la titulación especificada.')
            return redirect('formacion:titulaciones_pendientes_rrhh')

        # Lógica para la acción de VALIDAR
        if action == 'validar':
            if titulacion.estado == 'pendiente':
                try:
                    with transaction.atomic():
                        titulacion.estado = 'aprobado' 
                        titulacion.save()

                        Notificacion.objects.create(
                            usuario=titulacion.empleado,
                            mensaje=f"Tu titulación de '{titulacion.nombre}' ha sido <strong>validada</strong> por RRHH.",
                            tipo='success',
                            url=reverse('formacion:detalle_titulacion', args=[titulacion.id]),
                            leida=False
                        )
                    # Registramos el éxito de la validación.
                    logger.info(f"Titulación '{titulacion.nombre}' de '{titulacion.empleado.get_full_name()}' validada por '{request.user.username}'.")
                    messages.success(request, f"Titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) validada correctamente.")
                except Exception as e:
                    # Si falla la transacción, lo registramos y notificamos al usuario.
                    logger.error(f"Error en la transacción al validar la titulación con ID '{titulacion_id}': {e}", exc_info=True)
                    messages.error(request, 'Ocurrió un error al validar la titulación. Por favor, inténtalo de nuevo.')
            else:
                # Si se intenta validar una titulación que ya tiene otro estado, lo registramos como advertencia.
                logger.warning(f"Intento de validar una titulación con estado '{titulacion.estado}' por el usuario '{request.user.username}'.")
                messages.info(request, f"Esta titulación ya estaba '{titulacion.get_estado_display()}'. No se puede validar.")
        
        # Lógica para la acción de RECHAZAR
        elif action == 'rechazar':
            motivo_rechazo = request.POST.get('motivo_rechazo', '').strip()
            if not motivo_rechazo:
                logger.warning(f"El usuario '{request.user.username}' intentó rechazar una titulación sin proporcionar un motivo. Titulación ID: {titulacion_id}.")
                messages.error(request, "El motivo del rechazo no puede estar vacío.")
                # Redirigimos para mantener los parámetros de la URL (paginación, orden).
                current_query_params = request.GET.urlencode()
                return redirect(f"{reverse('formacion:titulaciones_pendientes_rrhh')}?{current_query_params}")

            if titulacion.estado == 'pendiente':
                try:
                    with transaction.atomic():
                        titulacion.estado = 'rechazado'
                        titulacion.motivo_rechazo = motivo_rechazo
                        titulacion.save()

                        Notificacion.objects.create(
                            usuario=titulacion.empleado,
                            mensaje=f"Tu titulación de '{titulacion.nombre}' ha sido <strong>rechazada</strong> por RRHH. Motivo: {motivo_rechazo}",
                            tipo='danger',
                            url=reverse('formacion:detalle_titulacion', args=[titulacion.id]),
                            leida=False
                        )
                    # Registramos el éxito del rechazo.
                    logger.info(f"Titulación '{titulacion.nombre}' de '{titulacion.empleado.get_full_name()}' rechazada por '{request.user.username}'. Motivo: '{motivo_rechazo}'.")
                    messages.success(request, f"Titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) rechazada correctamente.")
                except Exception as e:
                    # Si falla la transacción, lo registramos y notificamos al usuario.
                    logger.error(f"Error en la transacción al rechazar la titulación con ID '{titulacion_id}': {e}", exc_info=True)
                    messages.error(request, 'Ocurrió un error al rechazar la titulación. Por favor, inténtalo de nuevo.')
            else:
                # Si se intenta rechazar una titulación que ya tiene otro estado, lo registramos.
                logger.warning(f"Intento de rechazar una titulación con estado '{titulacion.estado}' por el usuario '{request.user.username}'.")
                messages.info(request, f"La titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) ya ha sido '{titulacion.get_estado_display()}'. No se puede rechazar.")
        
        # Redirigimos con los mismos parámetros de la URL para mantener el estado de la paginación y orden.
        current_query_params = request.GET.urlencode()
        return redirect(f"{reverse('formacion:titulaciones_pendientes_rrhh')}?{current_query_params}")

    # --- Lógica para solicitudes GET ---
    try:
        # Obtenemos todas las titulaciones que están 'pendientes' de revisión.
        titulaciones_queryset = Titulacion.objects.filter(
            estado='pendiente'
        ).select_related('empleado', 'curso_relacionado')

        # Registramos el número de titulaciones encontradas para depuración.
        logger.debug(f"Se encontraron {titulaciones_queryset.count()} titulaciones pendientes de revisión.")

        # Configuramos los campos por los que se puede ordenar la tabla.
        sort_by = request.GET.get('sort_by', 'fecha_obtencion')
        direction = request.GET.get('direction', 'asc')

        ORDERABLE_FIELDS_MAP = {
            'empleado': 'empleado__last_name',
            'nombre': 'nombre',
            'tipo_titulacion': 'tipo_titulacion',
            'institucion_emisora': 'institucion_emisora',
            'fecha_obtencion': 'fecha_obtencion'
        }

        order_field = ORDERABLE_FIELDS_MAP.get(sort_by, 'fecha_obtencion')
        if direction == 'desc':
            order_field = '-' + order_field

        titulaciones_queryset = titulaciones_queryset.order_by(order_field)

        # Configuramos la paginación.
        items_per_page = 10
        paginator = Paginator(titulaciones_queryset, items_per_page)
        page_number = request.GET.get('page')


        # --- PAGINACIÓN ---
        
        try:
            # Se obtiene el tamaño de página de la URL, por defecto 10
            page_size = int(request.GET.get('page_size', 10))
        except ValueError:
            # En caso de que el valor no sea un entero válido
            page_size = 10

        # Se obtiene el número de página de la URL, por defecto 1
        page = request.GET.get('page', 1)

        # Se crea el objeto Paginator con el queryset y el tamaño de página
        paginator = Paginator(titulaciones_queryset, page_size)

        # Se obtiene el objeto de la página, manejando automáticamente los errores
        page_obj = paginator.get_page(page)

    except Exception as e:
        logger.error(f"Error al obtener la lista de titulaciones pendientes para el usuario '{request.user.username}': {e}", exc_info=True)
        messages.error(request, 'Ocurrió un error al cargar la lista de titulaciones pendientes.')
        return redirect('formacion:dashboard')

    # Se prepara el contexto con los mismos nombres de variable
    context = {
        'titulaciones': page_obj,
        'page_obj': page_obj,
        'page_size': page_size,
        'sort_by': sort_by,
        'direction': direction,
    }

    return render(request, 'formacion/titulaciones_pendientes_rrhh.html', context)


@login_required
def detalle_titulacion(request, titulacion_id):
    """
    Vista para mostrar los detalles de una titulación específica.

    Solo permite a los empleados ver sus propias titulaciones y a RRHH/Admin
    ver cualquier titulación. Se ha añadido un robusto sistema de logs para
    rastrear los accesos y los intentos no autorizados.
    """
    # Registramos el intento de acceso a la vista.
    logger.info(f"El usuario '{request.user.username}' intenta acceder a la titulación con ID '{titulacion_id}'.")

    try:
        # Intentamos obtener la titulación. get_object_or_404 maneja el caso
        # de que no se encuentre el objeto, devolviendo un 404.
        titulacion = get_object_or_404(Titulacion, id=titulacion_id)

        # Verificamos si el usuario tiene permiso. La lógica de permisos es la siguiente:
        # 1. El usuario es el dueño de la titulación.
        # 2. El usuario pertenece al grupo de RRHH.
        # 3. El usuario es un administrador.
        if request.user == titulacion.empleado or es_rrhh(request.user) or es_admin(request.user):
            # Registramos el acceso exitoso.
            logger.info(f"Acceso permitido a la titulación con ID '{titulacion_id}' para el usuario '{request.user.username}'.")
            
            context = {
                'titulacion': titulacion
            }
            return render(request, 'formacion/detalle_titulacion.html', context)
        else:
            # Si el usuario no tiene permisos, registramos el intento no autorizado.
            logger.warning(f"Acceso denegado a la titulación con ID '{titulacion_id}'. Usuario '{request.user.username}' no tiene permisos.")
            messages.error(request, "No tienes permiso para ver esta titulación.")
            return redirect('formacion:dashboard')

    except Exception as e:
        # Capturamos cualquier otro error inesperado, por ejemplo, un problema de base de datos.
        logger.error(f"Error inesperado al intentar acceder a la titulación con ID '{titulacion_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al cargar los detalles de la titulación.")
        return redirect('formacion:dashboard')
        

@login_required
@user_passes_test(es_coordinador, login_url='formacion:dashboard') 
def preseleccionar_empleado(request):
    """
    Vista para que los coordinadores de departamento preseleccionen a sus empleados
    para cursos. Permite crear, editar y eliminar preselecciones.
    """
    empleado_coordinador = request.user
    departamento = empleado_coordinador.departamento 

    # Registramos el acceso a la vista.
    logger.info(f"El coordinador '{empleado_coordinador.username}' ha accedido a la vista de preselección para el departamento '{departamento}'.")

    # --- Lógica para solicitudes GET ---
    editar_preseleccion = None
    if 'editar' in request.GET:
        try:
            editar_preseleccion = get_object_or_404(Preseleccion, id=request.GET.get('editar'))
            # Verificamos si el coordinador tiene permiso para editar esta preselección.
            if editar_preseleccion.empleado.departamento != departamento:
                logger.warning(f"Intento de edición no autorizado. Usuario '{empleado_coordinador.username}' intentó editar la preselección ID '{editar_preseleccion.id}' del departamento '{editar_preseleccion.empleado.departamento}'.")
                messages.error(request, "No tienes permiso para editar esta preselección.")
                return redirect('formacion:preseleccionar_empleado')
            
            form = PreseleccionForm(instance=editar_preseleccion, coordinador=empleado_coordinador)
        except Exception as e:
            logger.error(f"Error al obtener la preselección para editar con ID '{request.GET.get('editar')}': {e}", exc_info=True)
            messages.error(request, "Ocurrió un error al intentar editar la preselección.")
            return redirect('formacion:preseleccionar_empleado')
    else:
        form = PreseleccionForm(coordinador=empleado_coordinador)

    # --- Lógica para solicitudes POST ---
    if request.method == 'POST':
        # Manejo de la acción de ELIMINAR
        if 'eliminar' in request.POST:
            try:
                pre = get_object_or_404(Preseleccion, id=request.POST['eliminar'])
                if pre.empleado.departamento == departamento:
                    pre.delete()
                    logger.info(f"Preselección ID '{pre.id}' de '{pre.empleado.get_full_name()}' eliminada por el coordinador '{empleado_coordinador.username}'.")
                    messages.success(request, f"Preselección de {pre.empleado.get_full_name()} eliminada correctamente.")
                else:
                    logger.warning(f"Intento de eliminación no autorizado. Usuario '{empleado_coordinador.username}' intentó eliminar la preselección ID '{pre.id}' de otro departamento.")
                    messages.error(request, "No tienes permiso para eliminar esta preselección.")
            except Exception as e:
                logger.error(f"Error al intentar eliminar la preselección con ID '{request.POST.get('eliminar')}': {e}", exc_info=True)
                messages.error(request, "Ocurrió un error al eliminar la preselección.")
            
            return redirect('formacion:preseleccionar_empleado')
        
        # Manejo de las acciones de CREAR o ACTUALIZAR
        if 'crear' in request.POST or 'actualizar' in request.POST:
            form = PreseleccionForm(request.POST, coordinador=empleado_coordinador, instance=editar_preseleccion)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        if 'actualizar' in request.POST:
                            pre = form.save()
                            logger.info(f"Preselección ID '{pre.id}' de '{pre.empleado.get_full_name()}' actualizada por '{empleado_coordinador.username}'.")
                            messages.success(request, "Preselección actualizada correctamente.")
                        else: # Es una nueva preselección
                            nueva_preseleccion = form.save(commit=False)
                            nueva_preseleccion.creado_por = request.user
                            nueva_preseleccion.save()
                            logger.info(f"Nueva preselección ID '{nueva_preseleccion.id}' para '{nueva_preseleccion.empleado.get_full_name()}' creada por '{empleado_coordinador.username}'.")
                            messages.success(request, f"Preselección para {nueva_preseleccion.empleado.get_full_name()} creada correctamente.")

                            # Lógica de Notificación
                            mensaje_notificacion = f'Nueva preselección creada por "{empleado_coordinador.get_full_name()}" para el curso "{nueva_preseleccion.curso.nombre}" de "{nueva_preseleccion.empleado.get_full_name()}". Pendiente de validar.'

                            grupos_a_notificar = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]

                            # Obtener una lista única de todos los usuarios de los grupos de destino
                            usuarios_a_notificar = Empleado.objects.filter(
                                groups__name__in=grupos_a_notificar
                            ).distinct()

                            # Añadir a los superusuarios que no estén en los grupos anteriores
                            super_usuarios = Empleado.objects.filter(is_superuser=True).exclude(
                                id__in=usuarios_a_notificar.values_list('id', flat=True)
                            ).distinct()

                            todos_los_destinatarios = list(usuarios_a_notificar) + list(super_usuarios)
                            
                            # Eliminamos al coordinador actual de la lista de destinatarios
                            destinatarios_finales = [u for u in todos_los_destinatarios if u.id != empleado_coordinador.id]

                            # Creamos una única notificación para cada destinatario único
                            for usuario_notificacion in destinatarios_finales:
                                Notificacion.objects.create(
                                    usuario=usuario_notificacion,
                                    mensaje=mensaje_notificacion,
                                    tipo='info', 
                                    url=reverse('formacion:confirmar_preseleccionados_lista')
                                )
                except Exception as e:
                    logger.error(f"Error en la transacción al guardar la preselección. Usuario '{empleado_coordinador.username}': {e}", exc_info=True)
                    messages.error(request, "Ocurrió un error al guardar la preselección. Por favor, revisa los datos.")
                
                return redirect('formacion:preseleccionar_empleado')
            else:
                logger.warning(f"Error de validación en el formulario para el usuario '{empleado_coordinador.username}'. Errores: {form.errors}")
                messages.error(request, "Error en el formulario. Por favor, revisa los datos.")

    # --- Lógica para solicitudes GET (renderizar la página) ---
    try:
        preselecciones = Preseleccion.objects.filter(
            empleado__departamento=departamento
        ).order_by('curso__nombre', 'prioridad').select_related('empleado', 'curso', 'creado_por')
        
        logger.debug(f"Se encontraron {preselecciones.count()} preselecciones para el departamento '{departamento}'.")
    except Exception as e:
        logger.error(f"Error al obtener la lista de preselecciones para el departamento '{departamento}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al cargar la lista de preselecciones.")
        preselecciones = Preseleccion.objects.none() # Devuelve un QuerySet vacío para evitar errores en el template

    return render(request, 'formacion/preseleccionar_empleado.html', {
        'form': form,
        'preselecciones': preselecciones,
        'editar': editar_preseleccion,
        'departamento': departamento,
    })


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
def gestionar_preselecciones_curso(request, curso_id):
    """
    Vista para que los usuarios con permisos (Formación, RRHH, Dirección)
    gestionen las preselecciones de un curso, confirmando o rechazando
    participantes y enviando notificaciones.

    Se ha añadido un sistema de logs para auditar las acciones y un
    manejo de errores robusto.
    """
    try:
        curso = get_object_or_404(Curso, id=curso_id)
        logger.info(f"El usuario '{request.user.username}' ha accedido a la gestión de preselecciones para el curso '{curso.nombre}' (ID: {curso_id}).")
    except Exception as e:
        logger.error(f"Error al obtener el curso con ID '{curso_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder a los detalles del curso.")
        return redirect('formacion:dashboard')

    # Aunque el decorador user_passes_test ya maneja la mayoría, esta es una
    # capa de seguridad adicional y redundante para permisos basados en grupos.
    grupos_permitidos = [
        settings.GRUPO_FORMACION,
        settings.GRUPO_RRHH,
        settings.GRUPO_DIRECCION
    ]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        logger.warning(f"Intento de acceso no autorizado. Usuario '{request.user.username}' no tiene los permisos necesarios para gestionar el curso '{curso.nombre}'.")
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('formacion:dashboard')

    # --- Lógica de recuperación de datos para el template ---
    try:
        # Optimizamos las consultas de base de datos con Prefetch
        participaciones_prefetch = Prefetch(
            'empleado__participaciones',
            queryset=Participacion.objects.filter(curso=curso),
            to_attr='_participaciones_para_curso_en_empleado'
        )

        preselecciones = Preseleccion.objects.filter(curso=curso).order_by('prioridad').select_related(
            'empleado__departamento'
        ).prefetch_related(participaciones_prefetch)

        # Lógica para asociar la participación existente a cada preselección
        for preseleccion in preselecciones:
            participacion_existente = next((
                p for p in preseleccion.empleado._participaciones_para_curso_en_empleado if p.curso_id == curso.id), None
            )
            preseleccion.participacion = participacion_existente

    except Exception as e:
        logger.error(f"Error al cargar las preselecciones para el curso '{curso.nombre}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al cargar la lista de preselecciones.")
        return redirect('formacion:dashboard')

    # --- Lógica para solicitudes POST (Confirmar o Rechazar) ---
    if request.method == 'POST':
        # Manejo de la acción de CONFIRMAR MÚLTIPLES SELECCIONES
        if 'confirmar_seleccionados' in request.POST:
            empleados_seleccionados_ids_str = request.POST.getlist('empleados_seleccionados')
            logger.info(f"Usuario '{request.user.username}' inicia la confirmación masiva de {len(empleados_seleccionados_ids_str)} empleados para el curso '{curso.nombre}'.")
            
            try:
                empleados_seleccionados_ids = [int(emp_id) for emp_id in empleados_seleccionados_ids_str]
                confirmed_count = 0

                with transaction.atomic():
                    for emp_id in empleados_seleccionados_ids:
                        if curso.plazas_disponibles <= 0:
                            logger.warning(f"Plazas agotadas para el curso '{curso.nombre}'. Proceso de confirmación masiva detenido. {confirmed_count} participantes confirmados.")
                            messages.warning(request, f"Se agotaron las plazas disponibles para el curso '{curso.nombre}'. Se confirmaron {confirmed_count} participantes. Los restantes no pudieron ser aceptados.")
                            break

                        # Evita aceptar empleados que ya tienen participación activa
                        if Participacion.objects.filter(
                            empleado_id=emp_id,
                            curso=curso,
                            estado__in=['aceptado', 'asistido', 'completado']
                        ).exists():
                            logger.info(f"El empleado ID '{emp_id}' ya tiene una participación activa en el curso '{curso.nombre}'. Se omite.")
                            messages.info(request, f"Un empleado seleccionado ya tiene participación activa en el curso. No se procesa duplicado.")
                            continue

                        # Acepta al empleado y crea/actualiza la participación
                        empleado = get_object_or_404(Empleado, id=emp_id)
                        participacion, created = Participacion.objects.get_or_create(
                            curso=curso,
                            empleado=empleado,
                            defaults={'estado': 'aceptado'}
                        )
                        if not created:
                            participacion.estado = 'aceptado'
                            participacion.save()

                        # Actualiza las plazas disponibles
                        curso.plazas_disponibles -= 1
                        curso.save(update_fields=['plazas_disponibles'])
                        
                        # Elimina la preselección
                        Preseleccion.objects.filter(curso=curso, empleado=empleado).delete()
                        confirmed_count += 1
                        logger.info(f"Participación de '{empleado.get_full_name()}' aceptada en el curso '{curso.nombre}'. Plaza ocupada.")

                        # Notificaciones
                        Notificacion.objects.create(usuario=empleado, mensaje=f'Tu participación en el curso "{curso.nombre}" ha sido ACEPTADA.', tipo='success')
                        if empleado.departamento and empleado.departamento.coordinador:
                            coordinador = empleado.departamento.coordinador
                            Notificacion.objects.create(usuario=coordinador, mensaje=f'La participación de "{empleado.get_full_name()}" en el curso "{curso.nombre}" ha sido ACEPTADA.', tipo='info')

                if confirmed_count > 0:
                    messages.success(request, f"Se confirmaron {confirmed_count} participantes para el curso '{curso.nombre}'.")
                
                num_selected_initially = len(empleados_seleccionados_ids)
                if num_selected_initially > confirmed_count:
                    messages.info(request, f"De {num_selected_initially} empleados seleccionados inicialmente, solo {confirmed_count} fueron confirmados debido a plazas limitadas o porque ya tenían participación activa.")

            except Exception as e:
                logger.error(f"Error durante el proceso de confirmación masiva para el curso '{curso.nombre}': {e}", exc_info=True)
                messages.error(request, "Ocurrió un error al procesar las confirmaciones masivas. Por favor, inténtelo de nuevo.")

            return redirect('formacion:gestionar_preselecciones_curso', curso_id=curso.id)

        # Manejo de la acción de ACEPTAR o RECHAZAR (individualmente)
        elif 'accion' in request.POST and 'preseleccion_id' in request.POST:
            preseleccion_id = request.POST.get('preseleccion_id')
            accion = request.POST.get('accion')

            logger.info(f"El usuario '{request.user.username}' intenta '{accion}' la preselección ID '{preseleccion_id}'.")

            try:
                preseleccion = get_object_or_404(Preseleccion, id=preseleccion_id, curso=curso)
                
                with transaction.atomic():
                    if accion == 'aceptar':
                        if curso.plazas_disponibles <= 0:
                            logger.warning(f"Intento de aceptación individual de '{preseleccion.empleado.username}' fallido: no hay plazas disponibles para el curso '{curso.nombre}'.")
                            messages.error(request, f'No hay plazas disponibles para aceptar a {preseleccion.empleado.get_full_name()} en "{curso.nombre}".')
                            preseleccion.delete()
                        else:
                            participacion_existente = Participacion.objects.filter(
                                empleado=preseleccion.empleado,
                                curso=curso,
                                estado__in=['aceptado', 'asistido', 'completado']
                            ).exists()

                            if participacion_existente:
                                logger.info(f"El empleado '{preseleccion.empleado.username}' ya tiene una participación activa. Se omite la aceptación individual.")
                                messages.info(request, f'"{preseleccion.empleado.get_full_name()}" ya tiene una participación activa en "{curso.nombre}".')
                                preseleccion.delete() # Elimina la preselección redundante
                            else:
                                participacion, created = Participacion.objects.get_or_create(
                                    empleado=preseleccion.empleado,
                                    curso=curso,
                                    defaults={'estado': 'aceptado'}
                                )
                                if not created and participacion.estado != 'aceptado':
                                    participacion.estado = 'aceptado'
                                    participacion.save()

                                curso.plazas_disponibles -= 1
                                curso.save(update_fields=['plazas_disponibles'])

                                messages.success(request, f'Participación de "{preseleccion.empleado.get_full_name()}" en "{curso.nombre}" ha sido aceptada.')
                                logger.info(f"Participación de '{preseleccion.empleado.username}' aceptada individualmente para el curso '{curso.nombre}'.")
                                Notificacion.objects.create(usuario=preseleccion.empleado, mensaje=f'Tu participación en el curso "{curso.nombre}" ha sido ACEPTADA.', tipo='success')
                                
                                if preseleccion.empleado.departamento and preseleccion.empleado.departamento.coordinador and preseleccion.empleado.departamento.coordinador != preseleccion.empleado:
                                    coordinador = preseleccion.empleado.departamento.coordinador
                                    Notificacion.objects.create(usuario=coordinador, mensaje=f'La participación de "{preseleccion.empleado.get_full_name()}" en el curso "{curso.nombre}" ha sido ACEPTADA.', tipo='info')
                                preseleccion.delete()

                    elif accion == 'rechazar':
                        participacion_existente = Participacion.objects.filter(
                            empleado=preseleccion.empleado,
                            curso=curso,
                            estado__in=['aceptado', 'asistido', 'completado']
                        ).exists()
                        if participacion_existente:
                            logger.warning(f"Intento de rechazo individual de '{preseleccion.empleado.username}' fallido: ya tiene una participación activa en el curso '{curso.nombre}'.")
                            messages.error(request, f'"{preseleccion.empleado.get_full_name()}" ya está confirmado en "{curso.nombre}". No se puede rechazar.')
                        else:
                            participacion, created = Participacion.objects.get_or_create(
                                empleado=preseleccion.empleado,
                                curso=curso,
                                defaults={'estado': 'rechazado'}
                            )
                            if not created and participacion.estado != 'rechazado':
                                participacion.estado = 'rechazado'
                                participacion.save()

                            messages.info(request, f'Preselección de "{preseleccion.empleado.get_full_name()}" para "{curso.nombre}" ha sido rechazada.')
                            logger.info(f"Preselección de '{preseleccion.empleado.username}' rechazada individualmente para el curso '{curso.nombre}'.")
                            Notificacion.objects.create(usuario=preseleccion.empleado, mensaje=f'Tu preselección para el curso "{curso.nombre}" ha sido RECHAZADA.', tipo='warning')
                            
                            if preseleccion.empleado.departamento and preseleccion.empleado.departamento.coordinador:
                                coordinador = preseleccion.empleado.departamento.coordinador
                                Notificacion.objects.create(usuario=coordinador, mensaje=f'La preselección de "{preseleccion.empleado.get_full_name()}" para el curso "{curso.nombre}" ha sido RECHAZADA.', tipo='info')
                            preseleccion.delete()
                    
                    #messages.success(request, f'Preselección de "{preseleccion.empleado.get_full_name()}" eliminada de la lista.')

            except Exception as e:
                logger.error(f"Error durante la acción '{accion}' para la preselección ID '{preseleccion_id}': {e}", exc_info=True)
                messages.error(request, f"Ocurrió un error al procesar la acción '{accion}'.")

            return redirect('formacion:gestionar_preselecciones_curso', curso_id=curso.id)

    # Si es una solicitud GET
    context = {
        'curso': curso,
        'preselecciones': preselecciones,
    }
    return render(request, 'formacion/confirmar_preseleccionados.html', context)


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
def confirmar_preseleccionados_lista(request):
    """
    Vista que muestra una lista de cursos con preselecciones pendientes
    para que los usuarios con permisos (Formación, RRHH, Dirección)
    puedan gestionarlas.

    Se ha añadido un sistema de logs para auditar las acciones y un
    manejo de errores robusto.
    """
    logger.info(f"El usuario '{request.user.username}' ha accedido a la lista de cursos con preselecciones pendientes.")

    # Aunque el decorador user_passes_test ya maneja la mayoría, esta es una
    # capa de seguridad adicional y redundante para permisos basados en grupos.
    grupos_permitidos = [
        settings.GRUPO_FORMACION,
        settings.GRUPO_RRHH,
        settings.GRUPO_DIRECCION
    ]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        logger.warning(f"Intento de acceso no autorizado. Usuario '{request.user.username}' no tiene los permisos necesarios.")
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('formacion:dashboard')

    try:
        # Filtra cursos que tienen al menos una preselección y que son actuales o futuros.
        cursos_con_preselecciones = Curso.objects.filter(
            preseleccionados__isnull=False # Asegura que el curso tiene preselecciones
        ).filter(
            # Utiliza la lógica original con Q para ser más explícito
            Q(fecha_fin__gte=datetime.date.today()) | Q(fecha_fin__isnull=True)
        ).annotate(
            num_pendientes=Count('preseleccionados', distinct=True)
        ).distinct().order_by('nombre')
        
        logger.debug(f"Se encontraron {cursos_con_preselecciones.count()} cursos con preselecciones pendientes.")

    except Exception as e:
        logger.error(f"Error al obtener la lista de cursos con preselecciones: {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al cargar la lista de cursos con preselecciones. Por favor, inténtelo de nuevo.")
        cursos_con_preselecciones = Curso.objects.none() # Devuelve un QuerySet vacío para evitar errores en el template

    context = {
        'cursos': cursos_con_preselecciones,
        'has_preselecciones': cursos_con_preselecciones.exists(),
    }
    return render(request, 'formacion/confirmar_preseleccionados_lista.html', context)


@login_required
@user_passes_test(lambda u: es_formacion_o_direccion(u) or es_coordinador(u), login_url='formacion:dashboard')
def gestionar_preseleccion(request, preseleccion_id):
    """
    Gestiona una preselección individual, permitiendo a los usuarios con permisos
    (Formación, Dirección o un Coordinador del departamento del empleado)
    aceptarla o rechazarla.
    """
    usuario_actual = request.user
    
    try:
        preseleccion = get_object_or_404(Preseleccion, id=preseleccion_id)
        logger.info(f"El usuario '{usuario_actual.username}' ha accedido a gestionar la preselección ID: {preseleccion_id}.")
    except Exception as e:
        logger.error(f"Error al obtener la preselección con ID '{preseleccion_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder a la preselección. Es posible que ya no exista.")
        return redirect('formacion:dashboard')

    empleado_preseleccionado = preseleccion.empleado
    curso_preseleccionado = preseleccion.curso

    # --- Lógica de verificación de permisos ---
    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(
        name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]
    ).exists()
    es_admin = usuario_actual.is_superuser
    es_coordinador_del_departamento = es_coordinador(usuario_actual) and \
                                      empleado_preseleccionado.departamento and \
                                      empleado_preseleccionado.departamento.coordinador == usuario_actual

    if not (es_rrhh_o_formacion_o_direccion or es_admin or es_coordinador_del_departamento):
        logger.warning(f"Acceso no autorizado. El usuario '{usuario_actual.username}' intentó gestionar la preselección del empleado '{empleado_preseleccionado.username}' sin permisos.")
        messages.error(request, "No tienes permisos para gestionar esta preselección.")
        return redirect('formacion:dashboard')

    # --- Lógica para solicitudes POST (Aceptar o Rechazar) ---
    if request.method == 'POST':
        accion = request.POST.get('accion')
        next_url = request.POST.get('next', 'formacion:dashboard')

        if not accion:
            messages.error(request, 'No se especificó una acción válida.')
            logger.warning(f"El usuario '{usuario_actual.username}' intentó enviar una solicitud POST sin una acción definida.")
            return redirect(next_url)
        
        try:
            with transaction.atomic():
                if accion == 'aceptar':
                    logger.info(f"El usuario '{usuario_actual.username}' intenta ACEPTAR la preselección de '{empleado_preseleccionado.get_full_name()}' para el curso '{curso_preseleccionado.nombre}'.")

                    if curso_preseleccionado.plazas_disponibles <= 0:
                        messages.error(request, f"No hay plazas disponibles para el curso '{curso_preseleccionado.nombre}'. No se puede aceptar la preselección.")
                        preseleccion.delete() # La preselección se borra de todas formas, ya no es válida.
                        logger.warning(f"Acción de aceptar fallida: plazas agotadas para el curso '{curso_preseleccionado.nombre}'. Se elimina la preselección.")
                        return redirect(next_url)

                    participacion, created = Participacion.objects.get_or_create(
                        empleado=empleado_preseleccionado,
                        curso=curso_preseleccionado,
                        defaults={'estado': 'aceptado'}
                    )

                    if not created:
                        if participacion.estado != 'aceptado':
                            participacion.estado = 'aceptado'
                            participacion.save(update_fields=['estado'])
                            messages.info(request, f"La participación existente de {participacion.empleado.get_full_name()} se ha actualizado a 'aceptado'.")
                            logger.info(f"Participación existente de '{participacion.empleado.username}' actualizada a 'aceptada'.")
                        else:
                            messages.warning(request, f"La participación de {participacion.empleado.get_full_name()} para '{curso_preseleccionado.nombre}' ya estaba aceptada.")
                            preseleccion.delete()
                            logger.warning(f"Participación de '{participacion.empleado.username}' ya estaba aceptada. Se elimina la preselección redundante.")
                            return redirect(next_url)
                    
                    curso_preseleccionado.plazas_disponibles -= 1
                    curso_preseleccionado.save(update_fields=['plazas_disponibles'])
                    preseleccion.delete()

                    messages.success(request, f"Preselección de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' **ACEPTADA**. Plaza asignada.")
                    logger.info(f"Preselección de '{empleado_preseleccionado.username}' aceptada. Plaza asignada a '{curso_preseleccionado.nombre}'.")

                elif accion == 'rechazar':
                    logger.info(f"El usuario '{usuario_actual.username}' intenta RECHAZAR la preselección de '{empleado_preseleccionado.get_full_name()}' para el curso '{curso_preseleccionado.nombre}'.")

                    participacion, created = Participacion.objects.get_or_create(
                        empleado=empleado_preseleccionado,
                        curso=curso_preseleccionado,
                        defaults={'estado': 'rechazado'}
                    )

                    if not created:
                        if participacion.estado == 'aceptado':
                            curso_preseleccionado.plazas_disponibles += 1
                            curso_preseleccionado.save(update_fields=['plazas_disponibles'])
                            messages.info(request, f"Se ha liberado una plaza para el curso '{curso_preseleccionado.nombre}' al rechazar la participación de {empleado_preseleccionado.get_full_name()}.")
                            logger.info(f"Participación de '{empleado_preseleccionado.username}' previamente aceptada. Se ha liberado una plaza.")
                        
                        if participacion.estado != 'rechazado':
                            participacion.estado = 'rechazado'
                            participacion.save(update_fields=['estado'])
                            messages.info(request, f"La participación existente de {empleado_preseleccionado.get_full_name()} se ha actualizado a 'rechazado'.")
                            logger.info(f"Participación existente de '{empleado_preseleccionado.username}' actualizada a 'rechazada'.")
                        else:
                            messages.warning(request, f"La participación de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' ya estaba rechazada.")
                            logger.warning(f"La participación de '{empleado_preseleccionado.username}' ya estaba rechazada.")
                    
                    preseleccion.delete()
                    messages.success(request, f"Preselección de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' **RECHAZADA**.")
                    logger.info(f"Preselección de '{empleado_preseleccionado.username}' rechazada y eliminada.")
                
                # Lógica de Notificación, la hemos movido aquí para no duplicar código
                if accion in ['aceptar', 'rechazar']:
                    # Notificación al empleado
                    tipo_notificacion = 'success' if accion == 'aceptar' else 'warning'
                    mensaje_empleado = f"¡Enhorabuena! Tu preselección para el curso '{curso_preseleccionado.nombre}' ha sido **{accion.upper()}**." if accion == 'aceptar' else f"Tu preselección para el curso '{curso_preseleccionado.nombre}' ha sido **RECHAZADA**."
                    Notificacion.objects.create(usuario=empleado_preseleccionado, mensaje=mensaje_empleado, tipo=tipo_notificacion)
                    logger.info(f"Notificación enviada al empleado '{empleado_preseleccionado.username}'.")

                    # Notificación al coordinador del departamento
                    coordinador_empleado = getattr(empleado_preseleccionado.departamento, 'coordinador', None)
                    if coordinador_empleado and coordinador_empleado != usuario_actual:
                        mensaje_coordinador = f'La preselección de "{empleado_preseleccionado.get_full_name()}" para el curso "{curso_preseleccionado.nombre}" ha sido **{accion.upper()}**.'
                        Notificacion.objects.create(usuario=coordinador_empleado, mensaje=mensaje_coordinador, tipo='info')
                        logger.info(f"Notificación enviada al coordinador '{coordinador_empleado.username}'.")
            
            # Captura errores específicos de la base de datos dentro del bloque `atomic`
        except (OperationalError, DatabaseError) as db_error:
            logger.error(f"Error de base de datos durante la acción '{accion}': {db_error}", exc_info=True)
            messages.error(request, f"Ocurrió un error en la base de datos. Por favor, inténtelo de nuevo.")
        except Exception as e:
            logger.error(f"Ocurrió un error inesperado durante la acción '{accion}': {e}", exc_info=True)
            messages.error(request, "Ocurrió un error inesperado al procesar la solicitud.")
        
        return redirect(next_url)

    # Si la solicitud no es POST, simplemente se redirige.
    messages.error(request, 'Método no permitido.')
    return redirect('formacion:dashboard')


@login_required
@require_POST
def cancelar_participacion(request, participacion_id):
    """
    Permite cancelar una participación en un curso, con validaciones de permisos
    y del estado del curso.

    - Logs detallados para auditoría.
    - Manejo robusto de errores de base de datos.
    - Lógica de permisos clara y consolidada.
    """
    usuario_actual = request.user
    
    try:
        participacion = get_object_or_404(Participacion, id=participacion_id)
        logger.info(f"El usuario '{usuario_actual.username}' intenta cancelar la participación ID: {participacion_id}.")
    except Exception as e:
        logger.error(f"Error al obtener la participación con ID '{participacion_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder a la participación. Es posible que ya no exista.")
        return redirect('formacion:mis_cursos')
    
    curso_participacion = participacion.curso
    empleado_participacion = participacion.empleado

    # --- Lógica de verificación de permisos ---
    es_propio_empleado = (empleado_participacion == usuario_actual)
    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(
        name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]
    ).exists()
    es_admin = usuario_actual.is_superuser
    es_coordinador_departamento = es_coordinador(usuario_actual) and \
                                  empleado_participacion.departamento and \
                                  empleado_participacion.departamento.coordinador == usuario_actual
    
    puede_cancelar = es_propio_empleado or es_coordinador_departamento or es_rrhh_o_formacion_o_direccion or es_admin

    # --- Validaciones de estado del curso y permisos ---
    if participacion.estado in ['completado', 'asistido']:
        messages.error(request, f"No se puede cancelar la participación en el curso '{curso_participacion.nombre}' porque ya ha sido completado o asistido.")
        logger.warning(f"Intento de cancelar participación en curso completado/asistido por el usuario '{usuario_actual.username}'.")
        return redirect('formacion:mis_cursos')

    if curso_participacion.fecha_inicio <= date.today() and not (es_rrhh_o_formacion_o_direccion or es_admin):
        messages.error(request, "No se puede cancelar una participación una vez iniciado el curso, a menos que tengas permisos de RRHH/Formación/Dirección/Admin.")
        logger.warning(f"Intento de cancelar participación en curso ya iniciado sin permisos suficientes por el usuario '{usuario_actual.username}'.")
        return redirect('formacion:mis_cursos')
    
    if not puede_cancelar:
        messages.error(request, "No tienes permisos para cancelar esta participación.")
        logger.warning(f"Acceso no autorizado. El usuario '{usuario_actual.username}' intentó cancelar la participación de '{empleado_participacion.username}'.")
        return redirect('formacion:mis_cursos')

    # --- Lógica de la cancelación ---
    try:
        with transaction.atomic():
            participacion.estado = 'cancelado'
            participacion.save()

            curso_participacion.plazas_disponibles += 1
            curso_participacion.save(update_fields=['plazas_disponibles'])
            
            logger.info(f"Participación ID: {participacion.id} de '{empleado_participacion.username}' para el curso '{curso_participacion.nombre}' ha sido cancelada por '{usuario_actual.username}'.")
            messages.success(request, f"Participación en {curso_participacion.nombre} cancelada correctamente.")

            # --- Lógica de Notificaciones ---
            # Notificación al empleado que canceló o al empleado afectado
            Notificacion.objects.create(
                usuario=empleado_participacion,
                mensaje=f"Tu participación en el curso '{curso_participacion.nombre}' ha sido CANCELADA.",
                tipo='info'
            )
            logger.info(f"Notificación enviada al empleado '{empleado_participacion.username}'.")

            # Notificación al coordinador del empleado
            coordinador_empleado = getattr(empleado_participacion.departamento, 'coordinador', None)
            if coordinador_empleado and coordinador_empleado != usuario_actual:
                Notificacion.objects.create(
                    usuario=coordinador_empleado,
                    mensaje=f'La participación de "{empleado_participacion.get_full_name()}" en el curso "{curso_participacion.nombre}" ha sido CANCELADA.',
                    tipo='warning'
                )
                logger.info(f"Notificación enviada al coordinador '{coordinador_empleado.username}'.")
            
            # Notificación a los usuarios del grupo de Formación
            try:
                # Se obtienen los grupos de RRHH y Dirección también para evitar notificarles 
                # si ya están cubiertos por un rol superior.
                grupos_superiores = [settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]
                usuarios_formacion_a_notificar = Empleado.objects.filter(
                    groups__name=settings.GRUPO_FORMACION
                ).exclude(
                    groups__name__in=grupos_superiores
                ).exclude(
                    id=usuario_actual.id
                ).distinct()

                for usuario_formacion in usuarios_formacion_a_notificar:
                    Notificacion.objects.create(
                        usuario=usuario_formacion,
                        mensaje=f'La participación de "{empleado_participacion.get_full_name()}" en el curso "{curso_participacion.nombre}" ha sido CANCELADA.',
                        tipo='warning'
                    )
                logger.info(f"Notificación de cancelación enviada a los usuarios del grupo '{settings.GRUPO_FORMACION}'.")

            except Group.DoesNotExist:
                logger.error(f"El grupo '{settings.GRUPO_FORMACION}' no existe. Asegúrate de que está creado.")
            except Exception as e:
                logger.error(f"Error inesperado al notificar al grupo de Formación: {e}", exc_info=True)

    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al cancelar la participación: {db_error}", exc_info=True)
        messages.error(request, "Ocurrió un error en la base de datos al intentar cancelar la participación. Por favor, inténtelo de nuevo.")
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al cancelar la participación: {e}", exc_info=True)
        messages.error(request, "Ocurrió un error inesperado. Por favor, inténtelo de nuevo.")

    return redirect('formacion:mis_cursos')


@login_required
@require_POST
def rechazar_participacion(request, participacion_id):
    """
    Permite a un usuario con permisos (Coordinador del departamento,
    RRHH, Formación, Dirección o Admin) rechazar una participación.
    
    - Logs detallados para auditoría.
    - Manejo robusto de errores de base de datos.
    - Lógica de permisos clara y consolidada.
    """
    usuario_actual = request.user

    try:
        participacion = get_object_or_404(Participacion, id=participacion_id)
        logger.info(f"El usuario '{usuario_actual.username}' intenta rechazar la participación ID: {participacion_id}.")
    except Exception as e:
        logger.error(f"Error al obtener la participación con ID '{participacion_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder a la participación. Es posible que ya no exista.")
        return redirect('formacion:estado_cursos')

    curso_participacion = participacion.curso
    empleado_participacion = participacion.empleado

    # --- Lógica de verificación de permisos ---
    es_coordinador_departamento = es_coordinador(usuario_actual) and \
                                  empleado_participacion.departamento and \
                                  empleado_participacion.departamento.coordinador == usuario_actual
    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(
        name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]
    ).exists()
    es_admin = usuario_actual.is_superuser
    
    puede_rechazar = es_coordinador_departamento or es_rrhh_o_formacion_o_direccion or es_admin

    # --- Validaciones de estado del curso y permisos ---
    if not puede_rechazar:
        messages.error(request, "No tienes permisos para rechazar esta participación.")
        logger.warning(f"Acceso no autorizado. El usuario '{usuario_actual.username}' intentó rechazar la participación de '{empleado_participacion.username}'.")
        return redirect('formacion:dashboard')

    if participacion.estado in ['completado', 'asistido', 'cancelado', 'rechazado']:
        messages.error(request, f"No se puede rechazar la participación en el curso '{curso_participacion.nombre}' porque ya está en estado '{participacion.estado}'.")
        logger.warning(f"Intento de rechazar participación que ya tiene un estado final por '{usuario_actual.username}'.")
        return redirect('formacion:estado_cursos')

    if curso_participacion.fecha_inicio <= date.today() and not (es_rrhh_o_formacion_o_direccion or es_admin):
        messages.error(request, "No se puede rechazar una participación una vez iniciado el curso, a menos que tengas permisos de RRHH/Formación/Dirección/Admin.")
        logger.warning(f"Intento de rechazar participación en curso ya iniciado sin permisos suficientes por el usuario '{usuario_actual.username}'.")
        return redirect('formacion:estado_cursos')
        
    # --- Lógica del rechazo ---
    try:
        with transaction.atomic():
            if participacion.estado == 'aceptado':
                curso_participacion.plazas_disponibles += 1
                curso_participacion.save(update_fields=['plazas_disponibles'])
                messages.info(request, f"Se ha liberado una plaza para el curso '{curso_participacion.nombre}' tras el rechazo.")
                logger.info(f"Participación de '{empleado_participacion.username}' estaba aceptada, se libera una plaza del curso.")
            
            participacion.estado = 'rechazado'
            participacion.save()

            logger.info(f"Participación ID: {participacion.id} de '{empleado_participacion.username}' para el curso '{curso_participacion.nombre}' ha sido RECHAZADA por '{usuario_actual.username}'.")
            messages.success(request, f"Participación de {empleado_participacion.get_full_name()} en {curso_participacion.nombre} RECHAZADA correctamente.")

            # --- Lógica de Notificaciones ---
            # Notificación al empleado
            Notificacion.objects.create(
                usuario=empleado_participacion,
                mensaje=f"Tu participación en el curso '{curso_participacion.nombre}' ha sido RECHAZADA.",
                tipo='danger'
            )
            logger.info(f"Notificación de rechazo enviada al empleado '{empleado_participacion.username}'.")

            # Notificación al coordinador del empleado
            coordinador_empleado = getattr(empleado_participacion.departamento, 'coordinador', None)
            if coordinador_empleado and coordinador_empleado != usuario_actual:
                Notificacion.objects.create(
                    usuario=coordinador_empleado,
                    mensaje=f'La participación de "{empleado_participacion.get_full_name()}" en el curso "{curso_participacion.nombre}" ha sido RECHAZADA.',
                    tipo='warning'
                )
                logger.info(f"Notificación enviada al coordinador '{coordinador_empleado.username}'.")
            
            # Notificación a los usuarios del grupo de Formación
            try:
                # Se obtienen los grupos de RRHH y Dirección para evitar notificarles
                grupos_superiores = [settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]
                usuarios_formacion_a_notificar = Empleado.objects.filter(
                    groups__name=settings.GRUPO_FORMACION
                ).exclude(
                    groups__name__in=grupos_superiores
                ).exclude(
                    id=usuario_actual.id
                ).distinct()

                for usuario_formacion in usuarios_formacion_a_notificar:
                    Notificacion.objects.create(
                        usuario=usuario_formacion,
                        mensaje=f'La participación de "{empleado_participacion.get_full_name()}" en el curso "{curso_participacion.nombre}" ha sido RECHAZADA.',
                        tipo='warning'
                    )
                logger.info(f"Notificación de rechazo enviada a los usuarios del grupo '{settings.GRUPO_FORMACION}'.")

            except Group.DoesNotExist:
                logger.error(f"El grupo '{settings.GRUPO_FORMACION}' no existe. Asegúrate de que está creado.")
            except Exception as e:
                logger.error(f"Error inesperado al notificar al grupo de Formación: {e}", exc_info=True)

    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al rechazar la participación: {db_error}", exc_info=True)
        messages.error(request, "Ocurrió un error en la base de datos al intentar rechazar la participación. Por favor, inténtelo de nuevo.")
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al rechazar la participación: {e}", exc_info=True)
        messages.error(request, "Ocurrió un error inesperado. Por favor, inténtelo de nuevo.")

    return redirect('formacion:estado_cursos')


@login_required
def listar_participantes_curso(request, curso_id):
    """
    Muestra la lista de participantes de un curso, con permisos para ver la lista
    y permisos para ver los botones de acción sobre cada participante.
    
    - Lógica de permisos consolidada y más legible.
    - Logs detallados para auditoría y depuración.
    - Manejo de errores de base de datos.
    """
    usuario_actual = request.user
    
    try:
        curso = get_object_or_404(Curso, id=curso_id)
        logger.info(f"El usuario '{usuario_actual.username}' intenta ver los participantes del curso '{curso.nombre}' (ID: {curso_id}).")
    except Exception as e:
        logger.error(f"Error al obtener el curso con ID '{curso_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder al curso. Es posible que ya no exista.")
        return redirect('formacion:dashboard')

    # --- Lógica de verificación de permisos para VER la lista ---
    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(
        name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]
    ).exists()
    es_admin = usuario_actual.is_superuser
    es_coordinador = usuario_actual.groups.filter(name=settings.GRUPO_COORDINADOR).exists()
    
    #es_coordinador_curso_solicitante = es_coordinador(usuario_actual) and \
    #                                   curso.departamento_solicitante and \
    #                                   getattr(getattr(usuario_actual, 'departamento_coordinado', None), 'nombre', None) == curso.departamento_solicitante
    
    puede_ver_lista = es_rrhh_o_formacion_o_direccion or es_admin or es_coordinador

    if not puede_ver_lista:
        messages.error(request, "No tienes permisos para ver los participantes de este curso.")
        logger.warning(f"Acceso no autorizado. El usuario '{usuario_actual.username}' intentó ver la lista de participantes del curso '{curso.nombre}'.")
        return redirect('formacion:dashboard')

    # --- Lógica de verificación de permisos para RECHAZAR participantes (se precalcula una vez) ---
    tiene_permiso_por_rol_o_admin = es_rrhh_o_formacion_o_direccion or es_admin
    
    # --- Obtener y procesar las participaciones ---
    try:
        participaciones = Participacion.objects.filter(curso=curso).order_by(
            'empleado__last_name', 'empleado__first_name'
        ).select_related('empleado', 'curso', 'empleado__departamento', 'empleado__codigo_puesto')

        # Se añaden atributos a cada participación para la lógica del template
        estados_no_rechazables = ['rechazado', 'cancelado', 'completado', 'asistido']
        for participacion in participaciones:
            # Revisa si el usuario actual es el coordinador del departamento del empleado en la participación
            es_coordinador_del_empleado = es_coordinador and \
                                          participacion.empleado.departamento == usuario_actual.departamento

            # El usuario puede ver el botón de rechazar si tiene un rol superior O si es el coordinador del empleado
            participacion.puede_ver_boton_rechazar = tiene_permiso_por_rol_o_admin or es_coordinador_del_empleado
            
            # La participación puede ser rechazada si su estado actual no es final
            participacion.puede_ser_rechazada = participacion.estado not in estados_no_rechazables
            
            # El botón de rechazar estará activo si se cumplen ambas condiciones
            participacion.boton_rechazar_activo = participacion.puede_ver_boton_rechazar and participacion.puede_ser_rechazada

    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al listar participantes del curso '{curso.nombre}': {db_error}", exc_info=True)
        messages.error(request, "Ocurrió un error en la base de datos al obtener los participantes. Por favor, inténtelo de nuevo.")
        return redirect('formacion:dashboard')
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al listar participantes del curso '{curso.nombre}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error inesperado. Por favor, inténtelo de nuevo.")
        return redirect('formacion:dashboard')

    context = {
        'curso': curso,
        'participantes': participaciones,
        'usuario_actual': usuario_actual,
        'es_coordinador': es_coordinador,
        'tiene_permiso_por_rol_o_admin': tiene_permiso_por_rol_o_admin,
    }
    return render(request, 'formacion/listar_participantes_curso.html', context)


# --- Gestión de Usuarios/Empleados ---
@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u) or es_formacion_o_direccion(u), login_url='formacion:dashboard')
def empleados_con_formacion(request):
    """
    Vista que muestra una lista de empleados, permitiendo filtrar, buscar y ordenar
    por departamento, palabra clave y columnas.
    
    - Lógica de filtrado y ordenación clara y segura.
    - Logs detallados para auditar el acceso y los parámetros de búsqueda.
    - Manejo de errores para la base de datos.
    """
    usuario_actual = request.user
    logger.info(f"El usuario '{usuario_actual.username}' accedió a la vista de empleados con formación.")

    # Inicializamos el queryset principal.
    # empleados_qs = Empleado.objects.all()
    empleados_qs = Empleado.objects.filter(groups__name=settings.GRUPO_EMPLEADO)

    # --- Filtro por Departamento ---
    departamento_id = request.GET.get('departamento')
    selected_departamento = None
    if departamento_id:
        try:
            selected_departamento = int(departamento_id)
            empleados_qs = empleados_qs.filter(departamento_id=selected_departamento)
            logger.info(f"Filtrando por departamento ID: {selected_departamento}.")
        except (ValueError, TypeError):
            logger.warning(f"Intento de filtrar con un departamento_id no válido: '{departamento_id}'.")
            # El valor se ignora y no se aplica el filtro.

    # --- Filtro por Palabras Clave ---
    keyword = request.GET.get('keyword', '').strip()
    if keyword:
        empleados_qs = empleados_qs.filter(
            Q(first_name__icontains=keyword) |
            Q(last_name__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(participaciones__curso__nombre__icontains=keyword) |
            Q(titulaciones__nombre__icontains=keyword)
        ).distinct()
        logger.info(f"Aplicando filtro de palabra clave: '{keyword}'.")

    # --- Ordenación de Columnas ---
    sort_by = request.GET.get('sort_by', 'first_name')
    direction = request.GET.get('direction', 'asc')

    # Mapeo de los nombres de campo seguros para la ordenación
    allowed_sort_fields = {
        'username': 'username',
        'first_name': 'first_name',
        'departamento__nombre': 'departamento__nombre',
    }
    
    sort_field = allowed_sort_fields.get(sort_by, 'first_name')
    
    if direction == 'desc':
        sort_field = f'-{sort_field}'
    try:
        empleados_qs = empleados_qs.order_by(sort_field)
    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al intentar ordenar los empleados: {db_error}", exc_info=True)
        # Se ignora la ordenación y se continúa con el queryset sin ordenar.
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al ordenar los empleados: {e}", exc_info=True)
    
    # Anotar el número de formaciones y titulaciones para el resumen visual
    # Las anotaciones se aplican después de los filtros para reflejar el conjunto filtrado
    try:
        empleados_qs = empleados_qs.annotate(
            num_participaciones=Count('participaciones', distinct=True),
            num_titulaciones=Count('titulaciones', distinct=True)
        ).select_related('departamento')
    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al anotar el queryset de empleados: {db_error}", exc_info=True)
        messages.error(request, "Ocurrió un error en la base de datos al procesar los datos de los empleados.")
        return render(request, 'formacion/empleados_con_formacion.html', {})
    
    # Obtiene todos los departamentos para el filtro de la plantilla
    departamentos = Departamento.objects.all().order_by('nombre')

    tabla_columnas = {
        'Usuario': 'username',
        'Nombre Completo': 'first_name',
        'Departamento': 'departamento__nombre',
    }

    # --- PAGINACIÓN ---
    try:
        page_size = int(request.GET.get('page_size', 10))  # valor por defecto 10
    except ValueError:
        page_size = 10
    page = request.GET.get('page', 1)

    paginator = Paginator(empleados_qs, page_size)
    page_obj = paginator.get_page(page)

    context = {
        # 'empleados': empleados_qs,
        # 'empleados': page_obj.object_list,
        'page_obj': page_obj,  # Pasa el objeto de página completo
        'page_size': page_size,
        'departamentos': departamentos,
        'selected_departamento': selected_departamento,
        'sort_by': sort_by,
        'direction': direction,
        'keyword': keyword,
        'tabla_columnas': tabla_columnas,
    }
    return render(request, 'formacion/empleados_con_formacion.html', context)


@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u) or es_formacion_o_direccion(u), login_url='formacion:dashboard')
def empleado_formacion_detalle(request, empleado_id):
    """
    Vista que muestra el detalle de la formación de un empleado específico.
    
    - Logs detallados para auditar el acceso a los datos de los empleados.
    - Manejo de errores de base de datos robusto.
    - Uso de `select_related` para optimizar las consultas.
    """
    usuario_actual = request.user
    
    try:
        # Obtener el empleado o devolver 404 si no existe
        empleado = get_object_or_404(Empleado, id=empleado_id)
        logger.info(f"El usuario '{usuario_actual.username}' accedió al detalle de formación del empleado '{empleado.username}' (ID: {empleado_id}).")
    except Exception as e:
        logger.error(f"Error al intentar obtener el empleado con ID '{empleado_id}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error al intentar acceder al empleado. Es posible que ya no exista.")
        return redirect('formacion:dashboard')

    try:
        # Obtener todas las participaciones del empleado
        participaciones = Participacion.objects.filter(empleado=empleado).select_related('curso').order_by('-created_at')

        # Obtener todas las titulaciones del empleado
        titulaciones = Titulacion.objects.filter(empleado=empleado).select_related('curso_relacionado').order_by('-fecha_obtencion')

    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al obtener los datos de formación para el empleado '{empleado.username}': {db_error}", exc_info=True)
        messages.error(request, "Ocurrió un error en la base de datos al obtener los detalles de formación. Por favor, inténtelo de nuevo.")
        return redirect('formacion:dashboard')
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado al obtener los datos de formación del empleado '{empleado.username}': {e}", exc_info=True)
        messages.error(request, "Ocurrió un error inesperado. Por favor, inténtelo de nuevo.")
        return redirect('formacion:dashboard')

    context = {
        'empleado': empleado,
        'participaciones': participaciones,
        'titulaciones': titulaciones,
    }
    return render(request, 'formacion/empleado_formacion_detalle.html', context)


@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u) or es_formacion_o_direccion(u), login_url='formacion:dashboard')
def empleado_list_view(request):
    """
    Vista que lista todos los empleados con paginación y ordenación.
    
    - Refactorizada de una vista de clase a una función.
    - Manejo de paginación y ordenación.
    - Logs detallados para auditoría.
    """
    usuario_actual = request.user
    logger.info(f"El usuario '{usuario_actual.username}' accedió a la vista de lista de empleados.")

    try:
        # Obtener el queryset de empleados y ordenarlo por apellido y nombre
        empleados_list = Empleado.objects.all().order_by('last_name', 'first_name')
    except (OperationalError, DatabaseError) as db_error:
        logger.error(f"Error de base de datos al obtener la lista de empleados: {db_error}", exc_info=True)
        # En caso de error, se puede retornar una página de error o una lista vacía.
        empleados_list = []
        # messages.error(request, "Ocurrió un error en la base de datos.")

    # Paginación - 10 empleados por página
    paginator = Paginator(empleados_list, 10)
    page_number = request.GET.get('page', 1)
    
    try:
        empleados_page = paginator.page(page_number)
    except PageNotAnInteger:
        # Si la página no es un entero, entrega la primera página.
        empleados_page = paginator.page(1)
        logger.warning(f"Número de página no válido: '{page_number}'. Mostrando la primera página.")
    except EmptyPage:
        # Si la página está fuera de rango, entrega la última página de resultados.
        empleados_page = paginator.page(paginator.num_pages)
        logger.warning(f"Número de página fuera de rango: '{page_number}'. Mostrando la última página.")

    context = {
        'empleados': empleados_page,
    }
    return render(request, 'formacion/empleado_list.html', context)


@login_required
@user_passes_test(solo_superusuarios, login_url='formacion:dashboard')
def alta_usuario_empleado(request):
    """
    Vista para crear un nuevo usuario tipo Empleado.

    - Utiliza el decorador `@login_required` para garantizar que solo los
      usuarios autenticados puedan acceder a esta vista.
    - Utiliza `@user_passes_test` con la función `solo_superusuarios` para
      restringir el acceso únicamente a los superusuarios. Si el usuario
      no cumple esta condición, es redirigido a la URL 'formacion:dashboard'.
    - Maneja tanto peticiones GET (para mostrar el formulario) como POST
      (para procesar los datos del formulario).
    """
    logger.info(f"Acceso a la vista de alta de empleado por el usuario: {request.user.username}")

    if request.method == 'POST':
        # Esta rama se ejecuta cuando el formulario se envía.
        logger.info(f"Petición POST recibida para la creación de un nuevo empleado.")
        
        # Crea una instancia del formulario con los datos enviados en la petición.
        form = EmpleadoCreationForm(request.POST)
        
        # Verifica si los datos del formulario son válidos.
        if form.is_valid():
            # Si el formulario es válido, se guarda el nuevo usuario.
            empleado = form.save()
            logger.info(f"Empleado '{empleado.username}' creado exitosamente.")
            
            # Muestra un mensaje de éxito al usuario que se verá en la
            # siguiente página después de la redirección.
            messages.success(request, f"Empleado '{empleado.username}' creado exitosamente.")
            
            # Redirige al usuario a la página de listado de empleados en el admin
            # para que pueda ver el resultado.
            return redirect('admin:formacion_empleado_changelist')
        else:
            # Si el formulario no es válido, registra los errores para depuración.
            logger.warning(f"Intento fallido de creación de empleado. Errores: {form.errors}")
    else:
        # Esta rama se ejecuta en las peticiones GET, es decir, cuando se
        # visita la página por primera vez.
        logger.info("Petición GET, mostrando formulario vacío.")
        
        # Crea una instancia de un formulario vacío para ser renderizado.
        form = EmpleadoCreationForm()
    
    # Renderiza la plantilla HTML 'alta_usuario_empleado.html' pasando
    # el formulario (ya sea vacío o con errores) al contexto.
    return render(request, 'formacion/alta_usuario_empleado.html', {'form': form})


def editar_perfil_empleado(request):
    """
    Vista que permite a un empleado logeado ver sus propios datos personales.

    - El decorador `@login_required` asegura que solo los usuarios autenticados
      pueden acceder a esta función, protegiendo la información sensible.
    - Esta vista está diseñada exclusivamente para la visualización,
      no para la edición de datos.
    """
    logger.info(f"El usuario '{request.user.username}' está accediendo a su perfil para visualizarlo.")

    # Django automáticamente asocia el objeto del usuario autenticado a `request.user`.
    # Asignamos esta instancia a una variable para mayor claridad.
    empleado_instance = request.user 

    # Se crea un diccionario de contexto para pasar datos a la plantilla.
    # El objeto `empleado_instance` se pasa bajo la clave 'empleado'.
    context = {
        'empleado': empleado_instance,
    }
    
    # Renderiza la plantilla HTML 'formacion/perfil_empleado_visualizar.html',
    # pasando el diccionario de contexto.
    logger.info("Renderizando la plantilla 'perfil_empleado_visualizar.html'.")
    return render(request, 'formacion/perfil_empleado_visualizar.html', context)


# Vistas para la gestión de Titulaciones/Certificaciones (Auto-Servicio)
# --------------------------------------------------------------------------

class MisTitulacionesListView(LoginRequiredMixin, ListView):
    """
    Vista basada en clases (Class-Based View) para listar todas las
    titulaciones y certificaciones que pertenecen al empleado que ha
    iniciado sesión.

    Utiliza LoginRequiredMixin para restringir el acceso a usuarios
    autenticados, garantizando la seguridad de los datos.
    """
    # Define el modelo del cual se obtendrán los objetos para la lista.
    model = Titulacion
    
    # Especifica la plantilla HTML que se utilizará para renderizar
    # el resultado de la lista.
    template_name = 'formacion/mis_titulaciones_list.html'
    
    # Define el nombre de la variable que se pasará al contexto de la
    # plantilla. Se podrá acceder a la lista como 'titulaciones'.
    context_object_name = 'titulaciones'

    def get_queryset(self):
        """
        Sobrescribe el método `get_queryset` para personalizar la lista
        de objetos que se va a mostrar.

        Este método asegura que solo se retornen las titulaciones que
        pertenecen al usuario logeado, evitando que un usuario pueda
        ver las titulaciones de otro.
        """
        # Registra una entrada en el log para saber qué usuario está
        # intentando acceder a sus titulaciones. Esto es útil para
        # la depuración y para auditar el uso de la aplicación.
        logger.info(f"Buscando titulaciones para el empleado: {self.request.user.username}")

        # Filtra las titulaciones para que solo se incluyan aquellas
        # asociadas al usuario actual (self.request.user).
        # Además, las ordena de forma descendente por la fecha de obtención.
        queryset = Titulacion.objects.filter(empleado=self.request.user).order_by('-fecha_obtencion')

        # Registra la cantidad de titulaciones encontradas.
        logger.info(f"Se encontraron {queryset.count()} titulaciones.")
        
        return queryset

# Crea la vista utilizando el método `as_view()` para que pueda ser
# utilizada en los archivos de rutas (urls.py).
mis_titulaciones_list = MisTitulacionesListView.as_view()


class MiTitulacionCreateView(LoginRequiredMixin, CreateView):
    """
    Vista basada en clases (CBV) que permite a un empleado logeado
    crear una nueva titulación o certificación.

    Utiliza LoginRequiredMixin para garantizar que solo usuarios
    autenticados puedan acceder a esta funcionalidad.
    """
    # Especifica el modelo al que el formulario va a añadir una instancia.
    model = Titulacion
    
    # Asocia esta vista con la clase de formulario que define los campos
    # y las validaciones.
    form_class = TitulacionForm
    
    # Define la plantilla que se usará para renderizar el formulario.
    template_name = 'formacion/mi_titulacion_form.html'
    
    # Define la URL a la que el usuario será redirigido después de
    # que el formulario se envíe exitosamente. `reverse_lazy` se usa
    # para resolver la URL de forma perezosa.
    success_url = reverse_lazy('formacion:mis_titulaciones_list')

    def form_valid(self, form):
        """
        Este método se llama cuando el formulario ha sido validado correctamente.
        Aquí es donde se realizan acciones adicionales antes de guardar la instancia.
        """
        # 1. Asignar el empleado automáticamente
        # Se asigna el usuario que está actualmente logeado (self.request.user)
        # al campo 'empleado' del formulario antes de que se guarde el objeto.
        form.instance.empleado = self.request.user
        logger.info(f"Asignando la nueva titulación al empleado: {self.request.user.username}")

        # 2. Calcular y asignar el nivel_meces
        # Se obtiene el valor del campo 'tipo_titulacion' del formulario.
        tipo_titulacion_seleccionado = form.cleaned_data.get('tipo_titulacion')
        
        # Se busca el nivel MECES correspondiente en el mapa de constantes.
        # Si el tipo no se encuentra, se asigna el valor por defecto 'otro_meces'.
        meces_asignado = TIPO_TITULACION_MECES_MAP.get(tipo_titulacion_seleccionado, 'otro_meces')
        form.instance.nivel_meces = meces_asignado

        logger.info(f"Tipo de titulación seleccionado: {tipo_titulacion_seleccionado}. Nivel MECES asignado: {meces_asignado}")
        
        # 3. Añadir un mensaje de éxito
        # Se añade un mensaje flash para notificar al usuario que la operación
        # fue exitosa. Este mensaje se mostrará en la siguiente página.
        messages.success(self.request, '¡Tu nueva titulación ha sido añadida correctamente!')
        
        # 4. Finalizar el proceso
        # Llama al método `form_valid` de la clase padre (CreateView) para
        # guardar el objeto en la base de datos y redirigir al usuario.
        return super().form_valid(form)

# Crea la vista utilizable a través de su método as_view().
mi_titulacion_create = MiTitulacionCreateView.as_view()



class MiTitulacionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Vista de clase que permite a un empleado editar una titulación/certificación existente.

    - `LoginRequiredMixin`: Requiere que el usuario esté autenticado.
    - `UserPassesTestMixin`: Permite restringir el acceso basado en una prueba personalizada.
    - `UpdateView`: Proporciona la funcionalidad para actualizar una instancia del modelo.
    """
    model = Titulacion
    form_class = TitulacionForm
    template_name = 'formacion/mi_titulacion_form.html'
    success_url = reverse_lazy('formacion:mis_titulaciones_list')
    context_object_name = 'titulacion' # Nombre del objeto en la plantilla

    def get(self, request, *args, **kwargs):
        """
        Sobrescribe el método `get` para registrar el acceso.
        """
        logger.info(f"El usuario '{request.user.username}' está intentando editar la titulación con ID: {self.kwargs['pk']}.")
        return super().get(request, *args, **kwargs)

    def test_func(self):
        """
        Función de prueba para el mixin `UserPassesTestMixin`.
        
        Permite el acceso solo si:
        1. La titulación pertenece al usuario logeado.
        2. El estado de la titulación es 'pendiente' o 'rechazado'.
        """
        titulacion = self.get_object()
        
        # Comprobación de seguridad: asegura que el usuario solo puede editar sus propias titulaciones.
        es_propietario = titulacion.empleado == self.request.user
        
        # Comprobación de estado: solo se puede editar si el estado lo permite.
        estado_permitido = titulacion.estado in ['pendiente', 'rechazado']
        
        if not (es_propietario and estado_permitido):
            logger.warning(
                f"Acceso denegado. El usuario '{self.request.user.username}' intentó editar la titulación ID: {titulacion.id}. "
                f"Es propietario: {es_propietario}, Estado permitido: {estado_permitido}."
            )
        
        return es_propietario and estado_permitido

    def handle_no_permission(self):
        """
        Maneja el caso en que `test_func` devuelve `False`.
        
        Muestra un mensaje de error y redirige al usuario a la lista de titulaciones.
        """
        messages.error(self.request, "No tienes permiso para editar esta titulación.")
        return redirect(self.success_url)

    def form_valid(self, form):
        """
        Este método se llama cuando el formulario se ha validado correctamente.
        
        Contiene la lógica de negocio para actualizar el estado y el nivel de MECES.
        """
        logger.info(f"Formulario de edición de titulación válido para el usuario '{self.request.user.username}'.")
        
        # Captura el estado original antes de guardar para aplicar la lógica condicional.
        original_estado = self.get_object().estado

        # 1. Calcular y asignar el nivel MECES basado en el tipo de titulación.
        # Esto es crucial si el tipo de titulación se cambia durante la edición.
        tipo_titulacion_seleccionado = form.cleaned_data.get('tipo_titulacion')
        form.instance.nivel_meces = TIPO_TITULACION_MECES_MAP.get(tipo_titulacion_seleccionado, 'otro_meces')
        logger.info(f"Nivel MECES actualizado a: {form.instance.nivel_meces}.")
        
        # 2. Lógica condicional para el estado 'rechazado'.
        if original_estado == 'rechazado':
            # Si se edita una titulación rechazada, su estado vuelve a ser 'pendiente'
            # para que pueda ser re-validada por el administrador.
            form.instance.estado = 'pendiente'
            form.instance.motivo_rechazo = None # Limpiar el motivo de rechazo al reenviar.
            messages.success(self.request, '¡La titulación rechazada ha sido actualizada y enviada nuevamente para validación!')
            logger.info("El estado de la titulación rechazada se ha cambiado a 'pendiente'.")
        else:
            # Para los demás estados permitidos ('pendiente'), solo se actualiza la información.
            messages.success(self.request, '¡La titulación ha sido actualizada correctamente!')
        
        # 3. Llamar al método `form_valid` de la clase padre (`UpdateView`)
        # para guardar la instancia actualizada en la base de datos.
        return super().form_valid(form)

mi_titulacion_update = MiTitulacionUpdateView.as_view()


class MiTitulacionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Vista de clase que permite a un empleado eliminar una titulación/certificación.

    - `LoginRequiredMixin`: Garantiza que solo los usuarios autenticados puedan acceder.
    - `UserPassesTestMixin`: Restringe el acceso basándose en una prueba personalizada.
    - `DeleteView`: Proporciona la funcionalidad para confirmar y eliminar una instancia del modelo.
    """
    model = Titulacion
    template_name = 'formacion/mi_titulacion_confirm_delete.html'
    success_url = reverse_lazy('formacion:mis_titulaciones_list')
    context_object_name = 'titulacion' # Nombre del objeto en la plantilla

    def get(self, request, *args, **kwargs):
        """
        Sobrescribe el método `get` para registrar el intento de acceso a la vista de eliminación.
        """
        logger.info(f"El usuario '{request.user.username}' está intentando acceder a la vista para eliminar la titulación con ID: {self.kwargs['pk']}.")
        return super().get(request, *args, **kwargs)

    def test_func(self):
        """
        Función de prueba para el mixin `UserPassesTestMixin`.
        
        Permite el acceso solo si:
        1. La titulación pertenece al usuario logeado (`self.request.user`).
        2. El estado de la titulación es 'pendiente'. Esto evita la eliminación de titulaciones
           ya validadas o rechazadas, manteniendo la integridad de los datos.
        """
        titulacion = self.get_object()
        es_propietario = titulacion.empleado == self.request.user
        estado_valido = titulacion.estado == 'pendiente'
        
        if not (es_propietario and estado_valido):
            logger.warning(
                f"Acceso denegado. El usuario '{self.request.user.username}' intentó eliminar la titulación ID: {titulacion.id}. "
                f"Es propietario: {es_propietario}, Estado válido: {estado_valido}."
            )
        
        return es_propietario and estado_valido

    def handle_no_permission(self):
        """
        Maneja el caso en que `test_func` devuelve `False`.
        
        Muestra un mensaje de error claro y redirige al usuario.
        """
        messages.error(self.request, "No tienes permiso para eliminar esta titulación.")
        return redirect(self.success_url)

    def delete(self, request, *args, **kwargs):
        """
        Este método se llama al confirmar la eliminación.
        
        Registra la acción y muestra un mensaje de éxito antes de completar la eliminación.
        """
        logger.info(f"La titulación con ID: {self.get_object().id} ha sido eliminada por el usuario '{request.user.username}'.")
        messages.success(self.request, '¡La titulación ha sido eliminada correctamente!')
        return super().delete(request, *args, **kwargs)

mi_titulacion_delete = MiTitulacionDeleteView.as_view()

# --- Notificaciones y Dashboard ---

class NotificacionesListView(LoginRequiredMixin, ListView):
    """
    Vista de clase que muestra las notificaciones del usuario autenticado.

    - `LoginRequiredMixin`: Garantiza que solo los usuarios logeados puedan acceder.
    - `ListView`: Proporciona toda la lógica necesaria para mostrar una lista de objetos.
    """
    model = Notificacion
    template_name = 'formacion/notificaciones.html'
    context_object_name = 'notificaciones' # El nombre que se usará en la plantilla para la lista.
    paginate_by = 20 # Opcional: paginación para manejar muchas notificaciones.

    def get_queryset(self):
        """
        Sobrescribe este método para filtrar el queryset y devolver solo las notificaciones
        del usuario actual, ordenadas por fecha de forma descendente.
        """
        logger.info(f"El usuario '{self.request.user.username}' está consultando sus notificaciones.")
        return Notificacion.objects.filter(usuario=self.request.user).order_by('-fecha')

    def get(self, request, *args, **kwargs):
        """
        Sobrescribe el método `get` para realizar una acción antes de renderizar la plantilla:
        marcar todas las notificaciones no leídas como leídas.
        """
        # Se obtiene el queryset de notificaciones no leídas y se actualiza su estado.
        num_actualizadas = self.get_queryset().filter(leida=False).update(leida=True)
        logger.info(f"Se marcaron {num_actualizadas} notificaciones como leídas para el usuario '{request.user.username}'.")
        
        # Se llama al método `get` de la clase padre para manejar la renderización.
        return super().get(request, *args, **kwargs)

# --- Vista para el dashboard ---
class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vista de clase para el dashboard de usuarios.

    - `LoginRequiredMixin`: Garantiza que solo los usuarios logeados puedan acceder.
    - `TemplateView`: Muestra una plantilla con contexto sin necesidad de un modelo.
    """
    template_name = 'formacion/dashboard.html'

    def get_context_data(self, **kwargs):
        """
        Sobrescribe este método para añadir datos personalizados al contexto
        que se pasará a la plantilla.
        """
        # Llama a la implementación base para obtener el contexto por defecto.
        context = super().get_context_data(**kwargs)
        
        # Cuenta las notificaciones no leídas.
        num_no_leidas = Notificacion.objects.filter(usuario=self.request.user, leida=False).count()
        logger.info(f"El usuario '{self.request.user.username}' tiene {num_no_leidas} notificaciones no leídas.")
        
        # Añade las variables de contexto.
        context.update({
            'es_empleado': es_empleado(self.request.user),
            'es_coordinador': es_coordinador(self.request.user),
            'es_formacion': es_formacion(self.request.user),
            'es_rrhh': es_rrhh(self.request.user),
            'es_direccion': es_direccion(self.request.user),
            'es_admin': es_admin(self.request.user),
            'num_notificaciones': num_no_leidas
        })
        
        return context


# --- Gestión de Cursos ---

@login_required
#@user_passes_test(es_formacion_o_direccion_o_rrhh, login_url='formacion:dashboard')
@user_passes_test(lambda u: es_formacion_o_direccion_o_rrhh(u) or es_coordinador(u), login_url='formacion:dashboard')
def estado_cursos(request):
    """
    Vista que muestra el estado de todos los cursos.
    Permite filtrar, ordenar y paginar los resultados.
    """
    logger.info(f"El usuario '{request.user.username}' está intentando acceder a la vista de estado de cursos.")

    grupos_permitidos = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION, settings.GRUPO_COORDINADOR]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        logger.warning(f"Intento de acceso denegado a '{request.user.username}' por falta de permisos.")
        return redirect('formacion:dashboard')

    logger.info(f"Acceso concedido a '{request.user.username}'.")

    # --- Lógica de Filtrado, Ordenación y Paginación ---
    show_finished_courses = request.GET.get('show_finished', 'false').lower() == 'true'
    cursos_queryset = Curso.objects.all()

    if not show_finished_courses:
        cursos_queryset = cursos_queryset.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
        )
        logger.debug("Filtrando para mostrar solo cursos activos.")
    else:
        logger.debug("Mostrando todos los cursos, incluidos los finalizados.")

    # Mapeo de campos para la ordenación
    ORDERABLE_FIELDS = {
        'nombre': 'nombre',
        'fecha_inicio': 'fecha_inicio',
        'fecha_fin': 'fecha_fin',
        'plazas_totales': 'plazas_totales',
        'plazas_disponibles': 'plazas_disponibles',
        # Puedes añadir otros campos si es necesario
    }
    
    sort_by = request.GET.get('sort_by', 'fecha_inicio')
    direction = request.GET.get('direction', 'asc')
    order_field = ORDERABLE_FIELDS.get(sort_by, 'fecha_inicio')
    
    if direction == 'desc':
        order_field = f'-{order_field}'
    
    cursos_queryset = cursos_queryset.order_by(order_field)

    # Lógica de paginación
    try:
        page_size = int(request.GET.get('page_size', 10))
    except (ValueError, TypeError):
        page_size = 10
    
    page = request.GET.get('page', 1)
    paginator = Paginator(cursos_queryset, page_size)
    page_obj = paginator.get_page(page)

    # Procesar solo los cursos de la página actual
    datos_cursos_con_estado = []
    for curso in page_obj.object_list:
        aceptados = Participacion.objects.filter(curso=curso, estado='aceptado').count()
        asistidos = Participacion.objects.filter(curso=curso, estado='asistido').count()
        completados = Participacion.objects.filter(curso=curso, estado='completado').count()
        pendientes_validar = Preseleccion.objects.filter(curso=curso).count()

        participacion_resumen_parts = []
        if aceptados > 0: participacion_resumen_parts.append(f"Acept: {aceptados}")
        if asistidos > 0: participacion_resumen_parts.append(f"Asist: {asistidos}")
        if completados > 0: participacion_resumen_parts.append(f"Comp: {completados}")
        if pendientes_validar > 0: participacion_resumen_parts.append(f"Pend: {pendientes_validar}")

        if not participacion_resumen_parts:
            participacion_resumen = "Sin participación activa"
        else:
            participacion_resumen = ", ".join(participacion_resumen_parts)

        curso_data = {
            'id': curso.id,
            'nombre': curso.nombre,
            'fecha_inicio': curso.fecha_inicio,
            'fecha_fin': curso.fecha_fin,
            'plazas_totales': curso.plazas_totales,
            'plazas_disponibles': curso.plazas_disponibles,
            'num_pendientes_validar': pendientes_validar,
            'participacion_resumen': participacion_resumen,
        }
        datos_cursos_con_estado.append(curso_data)
    es_coordinador = request.user.groups.filter(name=settings.GRUPO_COORDINADOR).exists()

    context = {
        'page_obj': page_obj,
        'page_size': page_size,
        'datos_cursos': datos_cursos_con_estado, # La plantilla iterará sobre esta lista
        'show_finished_courses': show_finished_courses,
        'sort_by': sort_by,
        'direction': direction,
        'es_coordinador': es_coordinador,
    }

    logger.info(f"Renderizando la plantilla 'estado_cursos.html' con {len(datos_cursos_con_estado)} cursos en la página actual.")
    return render(request, 'formacion/estado_cursos.html', context)


@login_required
@user_passes_test(es_formacion_o_direccion_o_rrhh, login_url='formacion:dashboard')
def crear_editar_curso(request, curso_id=None):
    """
    Vista para crear o editar un curso.

    Si se proporciona un `curso_id`, se recupera un objeto Curso existente para editar.
    De lo contrario, se prepara la vista para la creación de un nuevo curso.
    """
    curso = None
    if curso_id:
        # Si se recibe un ID, intentamos obtener el curso. Si no existe, Django
        # mostrará un error 404.
        curso = get_object_or_404(Curso, id=curso_id)
        logger.info(f"El usuario '{request.user.username}' está editando el curso con ID {curso_id}.")
    else:
        logger.info(f"El usuario '{request.user.username}' está creando un nuevo curso.")

    if request.method == 'POST':
        # Si la solicitud es POST, el usuario está enviando los datos del formulario.
        # Creamos una instancia del formulario con los datos recibidos y, si existe,
        # con la instancia del curso a editar.
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            # Si el formulario es válido, guardamos los datos. form.save()
            # se encargará de crear un nuevo objeto o actualizar el existente.
            saved_curso = form.save()
            if curso_id:
                messages.success(request, f"El curso '{saved_curso.nombre}' ha sido actualizado correctamente.")
                logger.info(f"Curso '{saved_curso.nombre}' (ID: {saved_curso.id}) actualizado por '{request.user.username}'.")
            else:
                messages.success(request, f"El curso '{saved_curso.nombre}' ha sido creado correctamente.")
                logger.info(f"Curso '{saved_curso.nombre}' (ID: {saved_curso.id}) creado por '{request.user.username}'.")
            
            # Redirige a la lista de gestión de cursos tras el éxito.
            return redirect('formacion:gestion_cursos_list')
        else:
            # Si el formulario no es válido, se muestra un mensaje de error y
            # se renderiza de nuevo la página con los errores del formulario.
            messages.error(request, "Error al guardar el curso. Revisa los datos.")
            logger.warning(f"Error de validación del formulario al intentar guardar un curso por '{request.user.username}'. Errores: {form.errors}")
            return render(request, 'formacion/crear_editar_curso.html', {'form': form, 'curso': curso})
    else:
        # Si la solicitud es GET, se inicializa el formulario.
        # Si estamos editando, el formulario se precarga con los datos del curso.
        # Si estamos creando, el formulario estará vacío.
        form = CursoForm(instance=curso)
        logger.debug(f"Formulario de curso inicializado para '{request.user.username}'.")

    # Renderiza la plantilla con el formulario y, si existe, el objeto curso.
    context = {'form': form, 'curso': curso}
    return render(request, 'formacion/crear_editar_curso.html', context)


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
@require_POST
def eliminar_curso(request, curso_id):
    """
    Vista para eliminar un curso.

    Esta vista solo acepta solicitudes POST para prevenir la eliminación accidental
    a través de una solicitud GET. Solo los usuarios de los grupos "Formación" y
    "Dirección" tienen permiso para acceder.
    """
    # Registra el intento de eliminación por parte de un usuario
    logger.info(f"El usuario '{request.user.username}' está intentando eliminar el curso con ID {curso_id}.")
    
    try:
        # Intenta obtener el objeto Curso. Si no se encuentra, get_object_or_404
        # retornará una página 404.
        curso = get_object_or_404(Curso, id=curso_id)

        # Guarda el nombre del curso antes de eliminarlo para usarlo en el mensaje de éxito.
        nombre_curso = curso.nombre
        
        # Elimina el objeto de la base de datos
        curso.delete()
        
        # Envía un mensaje de éxito al usuario
        messages.success(request, f"El curso '{nombre_curso}' ha sido eliminado correctamente.")
        
        # Registra la eliminación exitosa
        logger.info(f"El curso '{nombre_curso}' (ID: {curso_id}) fue eliminado por '{request.user.username}'.")
        
    except Exception as e:
        # En caso de cualquier error inesperado durante la eliminación,
        # registra el error y muestra un mensaje de error genérico.
        messages.error(request, "Ocurrió un error al intentar eliminar el curso.")
        logger.error(f"Error al eliminar el curso con ID {curso_id} por '{request.user.username}': {e}")
        
    # Redirige al usuario a la lista de próximos cursos, independientemente
    # del éxito o fallo.
    return redirect('formacion:proximos_cursos')


class SolicitudCursoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Vista para crear una nueva solicitud de curso.
    
    Permite a los usuarios con rol de "Coordinador" (verificado por UserPassesTestMixin)
    enviar una solicitud de curso. La vista gestiona el formulario, asigna
    automáticamente el solicitante y su departamento, y envía notificaciones
    a los grupos de interés.
    """
    model = SolicitudCurso
    form_class = SolicitudCursoForm
    template_name = 'formacion/solicitud_curso_form.html'
    success_url = reverse_lazy('formacion:dashboard')

    def test_func(self):
        """
        Verifica que el usuario actual tenga los permisos de coordinador.
        """
        return es_coordinador(self.request.user)

    def handle_no_permission(self):
        """
        Maneja el caso en que el usuario no tiene los permisos necesarios.
        Redirige y muestra un mensaje de error.
        """
        messages.error(self.request, "No tienes permiso para solicitar cursos.")
        return redirect('formacion:dashboard')

    def get_form_kwargs(self):
        """
        Pasa el usuario actual al formulario como un argumento.
        Esto permite que el formulario pueda validar o filtrar datos
        basándose en el solicitante.
        """
        kwargs = super().get_form_kwargs()
        kwargs['solicitante'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        Método llamado cuando el formulario es válido.
        
        Asigna el solicitante y su departamento a la instancia del modelo antes
        de guardarla. Luego, invoca el método de notificación.
        """
        # Asigna el usuario que realiza la solicitud
        form.instance.solicitante = self.request.user
        
        # Intenta asignar el departamento del usuario si existe
        if hasattr(self.request.user, 'empleado') and self.request.user.empleado.departamento:
            form.instance.departamento_solicitante = self.request.user.empleado.departamento
        else:
            # Si no se puede determinar el departamento, se registra un error
            error_message = "No se pudo determinar el departamento del solicitante."
            form.add_error(None, error_message)
            logger.warning(f"No se pudo determinar el departamento para el usuario '{self.request.user.username}'.")
            return self.form_invalid(form)

        # La llamada a super().form_valid(form) es la que guarda el objeto en la base de datos
        response = super().form_valid(form) 
        
        # Enviar notificación después de guardar la solicitud
        try:
            self.enviar_notificacion_solicitud_curso(form.instance)
        except transaction.TransactionManagementError as e:
            # Captura un error específico de la transacción de la base de datos
            error_msg = f"Error en la transacción de notificaciones. Por favor, inténtalo de nuevo. ({e})"
            messages.error(self.request, error_msg)
            logger.error(error_msg, exc_info=True)
        except Exception as e:
            # Captura cualquier otro error inesperado
            error_msg = f"Ocurrió un error inesperado al enviar notificaciones. ({e})"
            messages.error(self.request, error_msg)
            logger.error(error_msg, exc_info=True)
        
        messages.success(self.request, '¡Tu solicitud de curso ha sido enviada correctamente y está pendiente de revisión!')
        
        return response

    def enviar_notificacion_solicitud_curso(self, solicitud_curso):
        """
        Envía notificaciones a los usuarios de RRHH, Formación y Dirección
        cuando se crea una nueva solicitud de curso.
        """
        mensaje = (
            f'Nueva solicitud de curso de "{solicitud_curso.solicitante.get_full_name()}" '
            f'para el curso: "{solicitud_curso.titulo_curso_solicitado}". '
            f'Pendiente de revisión.'
        )
        tipo_notificacion = 'info'

        grupos_a_notificar = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]
        usuarios_notificados_ids = set() # Para evitar duplicados si un usuario está en varios grupos

        with transaction.atomic():
            for group_name in grupos_a_notificar:
                try:
                    group = Group.objects.get(name=group_name)
                    # Busca a los usuarios en el grupo que no son el solicitante original
                    # y que aún no han sido notificados.
                    usuarios_del_grupo = Empleado.objects.filter(
                        groups=group
                    ).exclude(
                        id=solicitud_curso.solicitante.id
                    ).exclude(
                        id__in=usuarios_notificados_ids
                    ).select_related('user') # Optimiza la consulta

                    for usuario_grupo in usuarios_del_grupo:
                        Notificacion.objects.create(
                            usuario=usuario_grupo,
                            mensaje=mensaje,
                            tipo=tipo_notificacion,
                            url=reverse_lazy('formacion:solicitudes_curso_pendientes_rrhh')
                        )
                        usuarios_notificados_ids.add(usuario_grupo.id)
                    
                    logger.info(f"Notificaciones enviadas al grupo '{group_name}'.")

                except Group.DoesNotExist:
                    # Registra una advertencia si el grupo no existe, pero la transacción continúa
                    logger.warning(f"El grupo '{group_name}' no existe. No se enviaron notificaciones a este grupo.")
                    continue
                except Exception as e:
                    # Captura otros errores inesperados durante la notificación por grupo
                    logger.error(f"Error al enviar notificación al grupo '{group_name}': {e}", exc_info=True)
                    continue

            # Notificar a superusuarios que no estén ya en los grupos anteriores
            super_usuarios = Empleado.objects.filter(is_superuser=True).exclude(
                id__in=usuarios_notificados_ids
            ).exclude(
                id=solicitud_curso.solicitante.id
            ).distinct().select_related('user')

            for admin_user in super_usuarios:
                Notificacion.objects.create(
                    usuario=admin_user,
                    mensaje=mensaje,
                    tipo=tipo_notificacion,
                    url=reverse_lazy('formacion:solicitudes_curso_pendientes_rrhh')
                )
                usuarios_notificados_ids.add(admin_user.id)
            
            logger.info("Notificaciones enviadas a superusuarios.")

# Convierte la clase en una vista para usar en urls.py
solicitud_curso_create = SolicitudCursoCreateView.as_view()



class SolicitudesCursoGestionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Vista que lista las solicitudes de cursos activas para que RRHH, Formación
    y Dirección puedan gestionarlas.
    
    Esta vista utiliza mixins para garantizar que solo usuarios autenticados
    y con permisos específicos puedan acceder.
    """
    model = SolicitudCurso
    template_name = 'formacion/solicitudes_curso_gestion_list.html'
    context_object_name = 'solicitudes'
    paginate_by = 15  # Opcional: para paginar los resultados si hay muchas solicitudes

    def test_func(self):
        """
        Verifica si el usuario pertenece a los grupos de 'Formación' o 'Dirección'.
        """
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        """
        Maneja el caso en que el usuario no tiene los permisos necesarios,
        redirigiendo y mostrando un mensaje de error.
        """
        messages.error(self.request, "No tienes permiso para ver las solicitudes de cursos.")
        logger.warning(f"Intento de acceso no autorizado a SolicitudesCursoGestionListView por '{self.request.user.username}'.")
        return redirect('formacion:dashboard')

    def get_queryset(self):
        """
        Obtiene el conjunto de solicitudes a mostrar.
        
        Filtra las solicitudes por los estados 'pendiente', 'aprobada' o 'en_proceso'
        y las ordena por fecha de solicitud descendente.
        """
        try:
            queryset = SolicitudCurso.objects.filter(
                estado__in=['pendiente', 'aprobada', 'en_proceso']
            ).order_by('-fecha_solicitud')
            logger.info(f"Mostrando {queryset.count()} solicitudes de curso activas para el usuario '{self.request.user.username}'.")
            return queryset
        except Exception as e:
            logger.error(f"Error al obtener el queryset de solicitudes para '{self.request.user.username}': {e}", exc_info=True)
            # En caso de error, retorna un queryset vacío para evitar que la vista falle
            messages.error(self.request, "Ocurrió un error al cargar las solicitudes.")
            return SolicitudCurso.objects.none()

# Convierte la clase en una vista para usar en urls.py
solicitudes_curso_gestion_list = SolicitudesCursoGestionListView.as_view()


class SolicitudCursoDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Vista que muestra el detalle completo de una solicitud de curso específica.
    
    Solo los usuarios con permisos de 'Formación' o 'Dirección' pueden acceder
    a esta vista.
    """
    model = SolicitudCurso
    template_name = 'formacion/solicitud_curso_detail.html'
    context_object_name = 'solicitud'

    def test_func(self):
        """
        Verifica que el usuario pertenezca al grupo de 'Formación' o 'Dirección'.
        """
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        """
        Maneja el caso en que un usuario sin permisos intenta acceder a la vista.
        
        Registra el intento en los logs, muestra un mensaje de error y redirige
        al usuario al dashboard.
        """
        messages.error(self.request, "No tienes permiso para ver el detalle de esta solicitud.")
        logger.warning(f"Intento de acceso no autorizado a SolicitudCursoDetailView por '{self.request.user.username}'.")
        return redirect('formacion:dashboard')

# Convierte la clase en una vista para usar en urls.py
solicitud_curso_detail = SolicitudCursoDetailView.as_view()


# --- Vistas de Acción sobre Solicitudes (para RRHH/Formación/Dirección) ---

class MotivoRechazoForm(forms.Form):
    """
    Formulario simple para capturar el motivo del rechazo de una solicitud de curso.
    """
    motivo = forms.CharField(
        # Utiliza un widget de Textarea para un campo de texto multilinea
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Motivo del Rechazo",
        help_text="Por favor, explica por qué se ha rechazado esta solicitud."
    )

class SolicitudCursoAccionBase(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Clase base para vistas de acción sobre Solicitudes de Curso.

    Centraliza la gestión de permisos de usuario, la definición del modelo
    y la URL de redirección en caso de éxito.
    """
    model = SolicitudCurso
    fields = []  # No se necesitan campos del formulario, solo se actualiza el objeto
    success_url = reverse_lazy('formacion:solicitudes_curso_gestion')

    def test_func(self):
        """
        Verifica que el usuario pertenezca al grupo de 'Formación' o 'Dirección'.
        """
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        """
        Maneja el caso en que un usuario sin permisos intenta acceder a la vista.
        """
        messages.error(self.request, "No tienes permiso para realizar esta acción.")
        return redirect('formacion:dashboard')
    
class NotificacionMixin:
    """
    Mixin para enviar notificaciones por correo electrónico.
    Proporciona un método reusable para las vistas.
    """

    def enviar_notificacion_a_solicitante(self, solicitud, asunto, mensaje_html_template, contexto_extra=None):
        """
        Envía una notificación por email al solicitante de un curso.
        """
        if not solicitud.solicitante.email:
            # En un entorno de producción, es mejor registrar este evento
            print(f"El solicitante {solicitud.solicitante.username} no tiene un email para notificar.")
            return

        context = {
            'solicitud': solicitud,
            'dominio': self.request.get_host(),
            'solicitud_url': self.request.build_absolute_uri(
                reverse_lazy('formacion:dashboard')
            ),
        }
        if contexto_extra:
            context.update(contexto_extra)

        html_message = render_to_string(mensaje_html_template, context)
        plain_message = strip_tags(html_message)

        try:
            send_mail(
                asunto,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [solicitud.solicitante.email],
                html_message=html_message,
                fail_silently=False,
            )
            print(f"Notificación '{asunto}' enviada a {solicitud.solicitante.email}")
        except Exception as e:
            # Es vital registrar los errores en un log para poder monitorearlos
            print(f"Error al enviar la notificación por email: {e}")


class AceptarSolicitudView(SolicitudCursoAccionBase, NotificacionMixin):
    """
    Vista que maneja la aceptación de una solicitud de curso.
    
    Cambia el estado de una solicitud a 'aprobada' y notifica al solicitante.
    """
    def form_valid(self, form):
        """
        Se ejecuta cuando el formulario es válido.
        
        Actualiza el estado de la solicitud y envía la notificación.
        """
        solicitud = self.get_object()
        
        # Validación para evitar procesar solicitudes ya finalizadas
        if solicitud.estado in ['aprobada', 'rechazada']:
            messages.error(self.request, "Esta solicitud ya ha sido procesada y no se puede aprobar.")
            logger.warning(f"Intento de aprobar solicitud '{solicitud.pk}' ya procesada por '{self.request.user.username}'.")
            return redirect(self.get_success_url())

        # Actualiza el estado de la solicitud
        solicitud.estado = 'aprobada'
        solicitud.save()

        # Envia la notificación usando el método del Mixin
        self.enviar_notificacion_a_solicitante(
            solicitud,
            f"Tu Solicitud de Curso '{solicitud.titulo_curso_solicitado}' ha sido Aprobada",
            'formacion/email/solicitud_aprobada.html',
        )

        messages.success(self.request, f"Solicitud '{solicitud.titulo_curso_solicitado}' aceptada correctamente.")
        logger.info(f"Solicitud '{solicitud.pk}' aceptada por el usuario '{self.request.user.username}'.")
        
        # Redirige a la URL de éxito definida en la clase base
        return super().form_valid(form)

# Convierte la clase en una vista para usar en urls.py
aceptar_solicitud = AceptarSolicitudView.as_view()


class RechazarSolicitudView(SolicitudCursoAccionBase, NotificacionMixin):
    """
    Vista que maneja el rechazo de una solicitud de curso.
    
    Utiliza un formulario para capturar el motivo, actualiza el estado de la
    solicitud a 'rechazada' y guarda el motivo en la base de datos.
    """
    model = SolicitudCurso
    form_class = MotivoRechazoForm
    template_name = 'formacion/solicitud_rechazar_confirm.html'
    context_object_name = 'solicitud'

    def form_valid(self, form):
        """
        Se ejecuta cuando el formulario de rechazo es válido.
        
        Actualiza el estado de la solicitud, guarda el motivo del rechazo y
        envía la notificación.
        """
        solicitud = self.get_object()
        
        # Validación para evitar procesar solicitudes ya finalizadas
        if solicitud.estado in ['aprobada', 'rechazada']:
            messages.error(self.request, "Esta solicitud ya ha sido procesada y no se puede rechazar.")
            logger.warning(f"Intento de rechazar solicitud '{solicitud.pk}' ya procesada por '{self.request.user.username}'.")
            return redirect(self.get_success_url())

        # Actualiza el estado y el motivo con los datos del formulario
        solicitud.estado = 'rechazada'
        solicitud.motivo_rechazo = form.cleaned_data['motivo']
        solicitud.save()

        # Envía la notificación al solicitante usando el Mixin.
        # Se incluye el motivo del rechazo como contexto adicional.
        self.enviar_notificacion_a_solicitante(
            solicitud,
            f"Tu Solicitud de Curso '{solicitud.titulo_curso_solicitado}' ha sido Rechazada",
            'formacion/email/solicitud_rechazada.html',
            contexto_extra={'motivo_rechazo': solicitud.motivo_rechazo}
        )
        
        messages.success(self.request, f"Solicitud '{solicitud.titulo_curso_solicitado}' rechazada correctamente.")
        logger.info(f"Solicitud '{solicitud.pk}' rechazada por el usuario '{self.request.user.username}'.")
        
        # Redirige a la URL de éxito definida en la clase base
        return redirect(self.get_success_url())

# Convierte la clase en una vista para usar en urls.py
rechazar_solicitud = RechazarSolicitudView.as_view()


class ProcesarSolicitudView(SolicitudCursoAccionBase):
    """
    Cambia el estado de una solicitud a 'completada' (asumiendo que se convierte en curso formal).
    No envía notificación al coordinador.
    """
    def perform_action(self, solicitud):
        # Registramos el inicio del procesamiento de la solicitud
        logger.info(f"Iniciando el procesamiento de la solicitud '{solicitud.pk}' del curso '{solicitud.titulo_curso_solicitado}' para cambiar su estado a 'completada'.")

        solicitud.estado = 'completada'
        solicitud.save()
        
        # Registramos que el procesamiento ha sido completado con éxito
        logger.info(f"Solicitud '{solicitud.pk}' del curso '{solicitud.titulo_curso_solicitado}' cambiada a 'completada' con éxito.")
        
        # NO se envía notificación al coordinador para esta acción

    def get_success_message(self, solicitud):
        return f"Solicitud '{solicitud.titulo_curso_solicitado}' procesada, asumiendo que se convertirá en curso formal."

# Convierte la clase en una vista para usar en urls.py
procesar_solicitud = ProcesarSolicitudView.as_view()


@login_required
def cursos_obligatorios_lista(request):
    """
    Vista para listar todos los cursos obligatorios, indicando la obligatoriedad
    y el estado de la solicitud del usuario actual.
    """
    try:
        # Registramos el acceso a la vista
        logger.info(f"Acceso a la vista de cursos obligatorios por el usuario '{request.user.username}'.")

        # 1. Recuperar todos los Cursos y pre-cargar sus requisitos obligatorios
        cursos = Curso.objects.prefetch_related(
            Prefetch(
                'requisitos_puesto',
                queryset=RequisitoPuestoFormacion.objects.filter(tipo_requisito='obligatorio').select_related('puesto').order_by('puesto__nombre'),
                to_attr='puestos_obligatorios_cache'
            )
        ).order_by('nombre')

        # 2. Pre-cargar las participaciones del usuario actual para una comprobación eficiente
        user_participations_map = {
            p.curso.id: p for p in Participacion.objects.filter(empleado=request.user).select_related('curso')
        }

        cursos_con_obligatoriedad_y_estado = []
        for curso in cursos:
            # Registramos el procesamiento de cada curso
            logger.info(f"Procesando curso: '{curso.nombre}' (ID: {curso.id}).")
            
            puestos_obligatorios_nombres = []
            if hasattr(curso, 'puestos_obligatorios_cache'):
                puestos_obligatorios_nombres = [req.puesto.nombre for req in curso.puestos_obligatorios_cache]
            es_obligatorio_general = curso.es_obligatorio

            if es_obligatorio_general or puestos_obligatorios_nombres:
                estado_usuario = None
                participacion_existente = user_participations_map.get(curso.id)
                if participacion_existente:
                    estado_usuario = participacion_existente.get_estado_display()

                puede_solicitar = True
                motivo_no_solicitar = ""

                if participacion_existente:
                    puede_solicitar = False
                    motivo_no_solicitar = f"Ya estás {estado_usuario.lower()} en este curso."
                elif curso.plazas_totales is not None and curso.plazas_totales > 0 and curso.plazas_disponibles <= 0:
                    puede_solicitar = False
                    motivo_no_solicitar = "No quedan plazas disponibles."
                elif curso.fecha_fin and curso.fecha_fin < timezone.now().date():
                    puede_solicitar = False
                    motivo_no_solicitar = "El curso ya ha finalizado."
                
                # Registramos si el usuario no puede solicitar el curso y el motivo
                if not puede_solicitar:
                    logger.info(f"El usuario '{request.user.username}' no puede solicitar el curso '{curso.nombre}'. Motivo: {motivo_no_solicitar}.")

                cursos_con_obligatoriedad_y_estado.append({
                    'curso': curso,
                    'es_obligatorio_general': es_obligatorio_general,
                    'puestos_obligatorios': puestos_obligatorios_nombres,
                    'estado_usuario': estado_usuario,
                    'puede_solicitar': puede_solicitar,
                    'motivo_no_solicitar': motivo_no_solicitar,
                })

        context = {
            'cursos_con_obligatoriedad': cursos_con_obligatoriedad_y_estado,
            'has_obligatory_courses': bool(cursos_con_obligatoriedad_y_estado),
        }
        
        # Registramos que la plantilla se va a renderizar
        logger.info("Renderizando la plantilla de cursos obligatorios.")
        return render(request, 'formacion/cursos_obligatorios_lista.html', context)

    except Exception as e:
        # En caso de error inesperado, lo registramos
        logger.error(f"Ocurrió un error inesperado en 'cursos_obligatorios_lista': {e}")
        # Considera cómo manejar el error, por ejemplo, redirigiendo a una página de error
        raise # Opcional: relanzar la excepción para una gestión de errores superior


@login_required
def solicitar_inscripcion_curso(request, curso_id):
    """
    Permite a un empleado solicitar la inscripción en un curso existente.
    Crea una Participacion con estado 'pendiente'.
    """
    if request.method == 'POST':
        # Registramos el intento de solicitud
        logger.info(f"Usuario '{request.user.username}' intentando solicitar inscripción para el curso con ID '{curso_id}'.")
        
        curso = get_object_or_404(Curso, pk=curso_id)

        # Validaciones antes de crear la participación
        if Participacion.objects.filter(empleado=request.user, curso=curso).exists():
            messages.warning(request, f'Ya tienes una solicitud o participación existente para "{curso.nombre}".')
            logger.warning(f"Solicitud rechazada para '{request.user.username}'. Ya existe una participación para el curso '{curso.nombre}'.")
            return redirect('formacion:cursos_obligatorios_lista')
        
        if curso.plazas_totales is not None and curso.plazas_totales > 0 and curso.plazas_disponibles <= 0:
            messages.error(request, f'Lo sentimos, el curso "{curso.nombre}" no tiene plazas disponibles.')
            logger.error(f"Solicitud rechazada para '{request.user.username}'. No hay plazas disponibles en el curso '{curso.nombre}'.")
            return redirect('formacion:cursos_obligatorios_lista')
        
        if curso.fecha_fin and curso.fecha_fin < timezone.now().date():
            messages.error(request, f'Lo sentimos, el curso "{curso.nombre}" ya ha finalizado y no se puede solicitar.')
            logger.error(f"Solicitud rechazada para '{request.user.username}'. El curso '{curso.nombre}' ya ha finalizado.")
            return redirect('formacion:cursos_obligatorios_lista')

        try:
            # Registramos que la creación de la participación está a punto de ocurrir
            logger.info(f"Creando una nueva participación para el usuario '{request.user.username}' en el curso '{curso.nombre}'.")
            
            # Crear la nueva participación con estado 'pendiente'
            participacion = Participacion.objects.create(
                empleado=request.user,
                curso=curso,
                estado='pendiente'
            )
            
            # Opcional: Reducir plazas disponibles si el curso las gestiona
            if curso.plazas_totales is not None and curso.plazas_totales > 0:
                curso.plazas_disponibles -= 1
                curso.save()
            
            messages.success(request, f'Tu solicitud de inscripción para "{curso.nombre}" ha sido enviada con éxito. Está pendiente de confirmación.')
            
            # Registramos el éxito de la solicitud
            logger.info(f"Solicitud de inscripción exitosa para '{request.user.username}' en el curso '{curso.nombre}'. ID de participación: {participacion.pk}.")
            
            return redirect('formacion:cursos_obligatorios_lista')

        except Exception as e:
            messages.error(request, f'Ocurrió un error al procesar tu solicitud: {e}')
            logger.error(f"Error inesperado al solicitar la inscripción al curso '{curso.nombre}' por el usuario '{request.user.username}': {e}", exc_info=True)
            return redirect('formacion:cursos_obligatorios_lista')
    
    messages.error(request, 'Método de solicitud no válido.')
    logger.warning(f"Solicitud no válida (método incorrecto) por el usuario '{request.user.username}'.")
    return redirect('formacion:cursos_obligatorios_lista')


@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def gestionar_solicitudes_obligatorias_rrhh(request):
    """
    Vista para que RRHH gestione las solicitudes de inscripción a cursos
    obligatorios (participaciones pendientes).
    """
    try:
        # Registramos el acceso a la vista por parte de RRHH
        logger.info(f"Acceso a la vista de gestión de solicitudes obligatorias por el usuario '{request.user.username}'.")
        
        solicitudes_pendientes = Participacion.objects.filter(estado='pendiente').order_by('created_at')

        # Registramos cuántas solicitudes pendientes se encontraron
        logger.info(f"Recuperadas {solicitudes_pendientes.count()} solicitudes pendientes para revisión.")
        
        context = {
            'solicitudes_pendientes': solicitudes_pendientes,
            'has_pendientes': bool(solicitudes_pendientes),
            'page_title': 'Gestión de Solicitudes de Cursos Obligatorios',
            'page_description': 'Revisa y gestiona las solicitudes de inscripción de los empleados a cursos marcados como obligatorios.',
            'form': AprobarParticipacionForm(),
        }
        
        # Registramos que la plantilla se va a renderizar
        logger.info("Renderizando la plantilla de gestión de solicitudes.")
        return render(request, 'formacion/gestionar_solicitudes_obligatorias_rrhh.html', context)
        
    except Exception as e:
        # En caso de error inesperado, lo registramos
        logger.error(f"Ocurrió un error inesperado en 'gestionar_solicitudes_obligatorias_rrhh': {e}", exc_info=True)
        # Opcional: Considera redirigir a una página de error o mostrar un mensaje
        raise # Relanzar la excepción para una gestión de errores superior si es necesario

@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def aprobar_solicitud_obligatoria(request, participacion_id):
    """
    RRHH aprueba una solicitud de inscripción a curso obligatorio (cambia estado de Participacion a 'confirmada').
    Ahora requiere una fecha de inicio real y crea una notificación detallada.
    """
    try:
        participacion = get_object_or_404(Participacion, pk=participacion_id)
        logger.info(f"Usuario '{request.user.username}' intentando aprobar la solicitud '{participacion_id}' de '{participacion.empleado.username}'.")

        if request.method == 'POST':
            form = AprobarParticipacionForm(request.POST)
            if form.is_valid():
                if participacion.estado == 'pendiente':
                    try:
                        participacion.estado = 'confirmada'
                        participacion.fecha_confirmacion = timezone.now().date()
                        participacion.fecha_inicio_real = form.cleaned_data['fecha_inicio_real']
                        participacion.certificado_obtenido = True
                        participacion.save()

                        Notificacion.objects.create(
                            usuario=participacion.empleado,
                            mensaje=f'¡Tu solicitud para el curso "{participacion.curso.nombre}" ha sido APROBADA! La fecha de inicio es el {participacion.fecha_inicio_real.strftime("%d/%m/%Y")}.',
                            tipo='success'
                        )

                        messages.success(request, f'La solicitud de {participacion.empleado.first_name} para "{participacion.curso.nombre}" ha sido APROBADA y el curso comenzará el {participacion.fecha_inicio_real.strftime("%d/%m/%Y")}.')
                        logger.info(f"Solicitud '{participacion_id}' de '{participacion.empleado.username}' aprobada con éxito. Fecha de inicio: {participacion.fecha_inicio_real}.")
                    
                    except Exception as e:
                        # Error inesperado durante el guardado
                        messages.error(request, f'Ocurrió un error inesperado al aprobar la solicitud: {e}')
                        logger.error(f"Error inesperado al guardar la aprobación de la solicitud '{participacion_id}': {e}", exc_info=True)
                    
                else:
                    messages.warning(request, 'Esta solicitud ya no está en estado pendiente.')
                    logger.warning(f"Intento de aprobar la solicitud '{participacion_id}' fallido. El estado actual es '{participacion.estado}', no 'pendiente'.")
                
                return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
            else:
                # El formulario no es válido, se registran los errores
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        field_name = form.fields[field].label if field in form.fields and form.fields[field].label else field
                        error_messages.append(f"Error en '{field_name}': {error}")
                
                error_message_combined = " ".join(error_messages)
                messages.error(request, error_message_combined or 'Error al aprobar: La fecha de inicio no es válida. Por favor, asegúrate de introducir una fecha válida.')
                logger.warning(f"Intento de aprobar la solicitud '{participacion_id}' fallido debido a errores de validación del formulario: {error_message_combined}")
                return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')

        messages.error(request, 'Método de solicitud no válido.')
        logger.warning(f"Intento de aprobar la solicitud '{participacion_id}' con un método no válido.")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
        
    except Participacion.DoesNotExist:
        messages.error(request, 'La solicitud especificada no existe.')
        logger.error(f"Intento de aprobar una solicitud inexistente con ID '{participacion_id}'.")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
    except Exception as e:
        # En caso de error inesperado, lo registramos
        logger.error(f"Ocurrió un error inesperado en 'aprobar_solicitud_obligatoria': {e}", exc_info=True)
        messages.error(request, f"Ocurrió un error inesperado: {e}")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')


@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def rechazar_solicitud_obligatoria(request, participacion_id):
    """
    RRHH rechaza una solicitud de inscripción a curso obligatorio (cambia estado de Participacion a 'rechazada').
    """
    try:
        participacion = get_object_or_404(Participacion, pk=participacion_id)
        logger.info(f"Usuario '{request.user.username}' intentando rechazar la solicitud '{participacion_id}' de '{participacion.empleado.username}'.")

        if request.method == 'POST':
            if participacion.estado == 'pendiente':
                try:
                    participacion.estado = 'rechazada'
                    participacion.fecha_confirmacion = timezone.now().date()
                    participacion.save()

                    # Opcional: Crear una notificación para el empleado
                    Notificacion.objects.create(
                        usuario=participacion.empleado,
                        mensaje=f'Lamentablemente, tu solicitud para el curso "{participacion.curso.nombre}" ha sido RECHAZADA. Por favor, contacta con RRHH para más detalles.',
                        tipo='danger'
                    )

                    messages.warning(request, f'La solicitud de {participacion.empleado.first_name} para "{participacion.curso.nombre}" ha sido RECHAZADA.')
                    logger.info(f"Solicitud '{participacion_id}' de '{participacion.empleado.username}' rechazada con éxito.")

                except Exception as e:
                    messages.error(request, f'Ocurrió un error inesperado al rechazar la solicitud: {e}')
                    logger.error(f"Error inesperado al guardar el rechazo de la solicitud '{participacion_id}': {e}", exc_info=True)

            else:
                messages.info(request, 'Esta solicitud ya no está en estado pendiente.')
                logger.warning(f"Intento de rechazar la solicitud '{participacion_id}' fallido. El estado actual es '{participacion.estado}', no 'pendiente'.")

            return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')

        messages.error(request, 'Método de solicitud no válido.')
        logger.warning(f"Intento de rechazar la solicitud '{participacion_id}' con un método no válido.")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')

    except Participacion.DoesNotExist:
        messages.error(request, 'La solicitud especificada no existe.')
        logger.error(f"Intento de rechazar una solicitud inexistente con ID '{participacion_id}'.")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado en 'rechazar_solicitud_obligatoria': {e}", exc_info=True)
        messages.error(request, f"Ocurrió un error inesperado: {e}")
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')


@login_required
@user_passes_test(es_rrhh)
def marcar_asistido(request, participacion_id):
    """
    RRHH marca una participación como 'asistido'.
    """
    try:
        participacion = get_object_or_404(Participacion, pk=participacion_id)
        logger.info(f"Usuario '{request.user.username}' intentando marcar como asistido la participación '{participacion_id}' de '{participacion.empleado.username}'.")

        if request.method == 'POST':
            # Solo permitir marcar como asistido si el estado actual lo permite
            if participacion.estado in ['confirmada', 'aceptado']:
                try:
                    participacion.estado = 'asistido'
                    participacion.save()

                    Notificacion.objects.create(
                        usuario=participacion.empleado,
                        mensaje=f'Tu asistencia para el curso "{participacion.curso.nombre}" ha sido registrada.',
                        tipo='info'
                    )
                    messages.success(request, f'Participación de {participacion.empleado.get_full_name()} en "{participacion.curso.nombre}" marcada como ASISTIDO.')
                    logger.info(f"Participación '{participacion_id}' de '{participacion.empleado.username}' marcada como 'asistido' con éxito.")
                except Exception as e:
                    messages.error(request, f'Ocurrió un error inesperado al marcar la asistencia: {e}')
                    logger.error(f"Error inesperado al guardar la asistencia para la participación '{participacion_id}': {e}", exc_info=True)
            else:
                messages.warning(request, f'No se puede marcar como asistido la participación de {participacion.empleado.get_full_name()} en su estado actual ({participacion.get_estado_display()}).')
                logger.warning(f"Intento de marcar como asistido la participación '{participacion_id}' fallido. El estado actual es '{participacion.estado}', no 'confirmada' o 'aceptado'.")
        else:
            messages.error(request, 'Método de solicitud no válido.')
            logger.warning(f"Intento de marcar como asistido la participación '{participacion_id}' con un método no válido.")

        # Redirigir de vuelta a la lista de participantes del curso o a otra página de gestión
        return redirect('formacion:listar_participantes_curso', curso_id=participacion.curso.id)

    except Participacion.DoesNotExist:
        messages.error(request, 'La participación especificada no existe.')
        logger.error(f"Intento de marcar como asistido una participación inexistente con ID '{participacion_id}'.")
        return redirect('formacion:gestionar_cursos_rrhh') # Redirigimos a una vista genérica de RRHH
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado en 'marcar_asistido': {e}", exc_info=True)
        messages.error(request, f"Ocurrió un error inesperado: {e}")
        return redirect('formacion:gestionar_cursos_rrhh') # Redirigimos a una vista genérica de RRHH
    


@login_required
@user_passes_test(es_rrhh)
def marcar_completado(request, participacion_id):
    """
    RRHH marca una participación como 'completado' y asigna una calificación.
    """
    try:
        participacion = get_object_or_404(Participacion, pk=participacion_id)
        logger.info(f"Usuario '{request.user.username}' intentando marcar como completado la participación '{participacion_id}' de '{participacion.empleado.username}'.")
        
        if request.method == 'POST':
            form = MarcarCompletadoForm(request.POST, instance=participacion)
            if form.is_valid():
                if participacion.estado in ['asistido', 'confirmada', 'aceptado']:
                    try:
                        with transaction.atomic():
                            participacion.estado = 'completado'
                            form.save()
                            
                            url_encuesta = reverse('formacion:encuesta_satisfaccion', args=[participacion.id])
                            
                            Notificacion.objects.create(
                                usuario=participacion.empleado,
                                mensaje=f'El curso "{participacion.curso.nombre}" ha sido marcado como COMPLETADO. ¡Felicidades!',
                                tipo='success', 
                                url=url_encuesta, 
                                leida=False
                            )
                            
                            messages.success(request, f'Participación de {participacion.empleado.get_full_name()} en "{participacion.curso.nombre}" marcada como COMPLETADO.')
                            logger.info(f"Participación '{participacion_id}' de '{participacion.empleado.username}' marcada como 'completado' con éxito.")
                            
                    except Exception as e:
                        messages.error(request, f'Ocurrió un error inesperado al marcar como completado: {e}')
                        logger.error(f"Error inesperado al guardar el completado de la participación '{participacion_id}': {e}", exc_info=True)
                else:
                    messages.warning(request, f'No se puede marcar como completado la participación de {participacion.empleado.get_full_name()} en su estado actual ({participacion.get_estado_display()}).')
                    logger.warning(f"Intento de marcar como completado la participación '{participacion_id}' fallido. El estado actual es '{participacion.estado}'.")
            else:
                error_messages = [f"Error en '{form.fields[field].label}': {error}" for field, errors in form.errors.items() for error in errors]
                messages.error(request, f'Errores al marcar como completado: {" ".join(error_messages)}')
                logger.warning(f"Error de validación del formulario al intentar marcar como completado la participación '{participacion_id}': {form.errors}")
        else:
            messages.error(request, 'Método de solicitud no válido.')
            logger.warning(f"Intento de marcar como completado la participación '{participacion_id}' con un método no válido.")
        
        return redirect('formacion:listar_participantes_curso', curso_id=participacion.curso.id)

    except Participacion.DoesNotExist:
        messages.error(request, 'La participación especificada no existe.')
        logger.error(f"Intento de marcar como completado una participación inexistente con ID '{participacion_id}'.")
        return redirect('formacion:gestionar_cursos_rrhh')
    except Exception as e:
        logger.error(f"Ocurrió un error inesperado en 'marcar_completado': {e}", exc_info=True)
        messages.error(request, f"Ocurrió un error inesperado: {e}")
        return redirect('formacion:gestionar_cursos_rrhh')
    

@login_required
@user_passes_test(es_rrhh, login_url='formacion:dashboard')
def gestion_cursos_list(request):
    """
    Vista para que RRHH liste todos los cursos para su gestión.
    Con opciones de filtrado, ordenación y paginación.
    """
    # Lógica de filtrado de cursos terminados
    show_finished_courses = request.GET.get('show_finished', 'false').lower() == 'true'

    # Lógica de ordenación
    sort_by = request.GET.get('sort_by', 'created_at') # 'created_at' como campo por defecto
    direction = request.GET.get('direction', 'desc') # 'desc' por defecto para 'created_at'

    # Lógica de paginación
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)

    cursos_queryset = Curso.objects.all()

    # Filtramos si no se piden cursos terminados
    if not show_finished_courses:
        cursos_queryset = cursos_queryset.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
        )

    # Aplicamos la ordenación a la queryset
    valid_sort_fields = ['nombre', 'tipo', 'proveedor', 'fecha_inicio', 'fecha_fin', 'duracion_horas', 'created_at']
    if sort_by in valid_sort_fields:
        if direction == 'desc':
            cursos_queryset = cursos_queryset.order_by(f'-{sort_by}')
        else:
            cursos_queryset = cursos_queryset.order_by(sort_by)
    else:
        # Si el campo no es válido, volvemos a la ordenación por defecto
        cursos_queryset = cursos_queryset.order_by('-created_at')

    # Aplicamos la paginación a la queryset ordenada
    paginator = Paginator(cursos_queryset, page_size)
    page_obj = paginator.get_page(page_number)

    # Lógica para determinar la dirección del siguiente clic en la plantilla
    ordenacion_siguiente = {
        'nombre': 'asc' if sort_by != 'nombre' or direction == 'desc' else 'desc',
        'tipo': 'asc' if sort_by != 'tipo' or direction == 'desc' else 'desc',
        'proveedor': 'asc' if sort_by != 'proveedor' or direction == 'desc' else 'desc',
        'fecha_inicio': 'asc' if sort_by != 'fecha_inicio' or direction == 'desc' else 'desc',
        'fecha_fin': 'asc' if sort_by != 'fecha_fin' or direction == 'desc' else 'desc',
        'duracion_horas': 'asc' if sort_by != 'duracion_horas' or direction == 'desc' else 'desc',
    }

    context = {
        'page_obj': page_obj,
        'is_rrhh': True,
        'show_finished_courses': show_finished_courses,
        'sort_by': sort_by,
        'direction': direction,
        'page_size': int(page_size),
        'ordenacion_siguiente': ordenacion_siguiente,
    }

    # Registro de la acción de acceso a la vista
    logger.info(f"El usuario '{request.user.username}' (RRHH) ha accedido a la lista de gestión de cursos. Mostrar cursos terminados: {show_finished_courses}.")

    return render(request, 'formacion/gestion_cursos_list.html', context)


@login_required
def encuesta_satisfaccion(request, participacion_id):
    """
    Vista para que un empleado rellene la encuesta de satisfacción de un curso.
    """
    try:
        participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)
        logger.info(f"El usuario '{request.user.username}' ha accedido a la encuesta de satisfacción para la participación '{participacion_id}'.")
    except Participacion.DoesNotExist:
        messages.error(request, 'La participación especificada no existe.')
        logger.error(f"Intento de acceso a encuesta de satisfacción de una participación inexistente con ID '{participacion_id}' por '{request.user.username}'.")
        return redirect('formacion:mis_cursos')

    # Verificar si la encuesta ya ha sido rellenada para esta participación
    if EncuestaSatisfaccion.objects.filter(participacion=participacion).exists():
        messages.info(request, "Ya has completado la encuesta de satisfacción para este curso.")
        logger.warning(f"El usuario '{request.user.username}' intentó acceder a la encuesta '{participacion_id}' que ya había completado.")
        return redirect('formacion:mis_cursos')

    # Asegurarse de que el curso está completado antes de permitir la encuesta
    if participacion.estado != 'completado':
        messages.error(request, "Solo puedes rellenar la encuesta para cursos marcados como completados.")
        logger.warning(f"El usuario '{request.user.username}' intentó acceder a la encuesta '{participacion_id}' con un curso en estado '{participacion.estado}'.")
        return redirect('formacion:mis_cursos')

    if request.method == 'POST':
        form = EncuestaSatisfaccionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    encuesta = form.save(commit=False)
                    encuesta.participacion = participacion
                    encuesta.empleado = request.user
                    encuesta.fecha_encuesta = date.today()
                    encuesta.nombre_curso_encuesta = participacion.curso.nombre
                    encuesta.save()

                messages.success(request, "¡Gracias! Tu encuesta de satisfacción ha sido enviada.")
                logger.info(f"El usuario '{request.user.username}' ha enviado con éxito la encuesta para la participación '{participacion_id}'.")
                return redirect('formacion:mis_cursos')
            except Exception as e:
                messages.error(request, f'Ocurrió un error inesperado al guardar la encuesta: {e}')
                logger.error(f"Error inesperado al guardar la encuesta para la participación '{participacion_id}': {e}", exc_info=True)
                return redirect('formacion:mis_cursos')
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
            logger.warning(f"Error de validación del formulario al enviar la encuesta para la participación '{participacion_id}': {form.errors}")
    else:
        form = EncuestaSatisfaccionForm()

    context = {
        'form': form,
        'participacion': participacion,
        'curso': participacion.curso,
        'fecha_actual': date.today(),
    }
    return render(request, 'formacion/encuesta_satisfaccion.html', context)


@login_required
def marcar_participacion_completada(request, participacion_id):
    """
    Vista para que un empleado marque su participación en un curso como completada.
    """
    try:
        participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)
        logger.info(f"El usuario '{request.user.username}' intenta marcar como completada la participación '{participacion_id}' del curso '{participacion.curso.nombre}'.")
    except Participacion.DoesNotExist:
        messages.error(request, "La participación especificada no existe o no te pertenece.")
        logger.error(f"Intento de acceso no autorizado o a una participación inexistente por el usuario '{request.user.username}' para el ID '{participacion_id}'.")
        return redirect('formacion:mis_cursos')

    if request.method == 'POST':
        # Definimos los estados que NO deben permitir al empleado marcar como "completado"
        estados_no_completables = ['completado', 'cancelado', 'abandonado', 'rechazado']
        
        if participacion.estado not in estados_no_completables:
            try:
                # Usamos una transacción atómica para asegurar que el estado se guarda
                # y la notificación se crea, o ninguna de las dos cosas.
                with transaction.atomic():
                    participacion.estado = 'completado'
                    participacion.save()
                    messages.success(request, f"¡Has marcado tu participación en '{participacion.curso.nombre}' como completada!")
                    logger.info(f"El usuario '{request.user.username}' ha marcado la participación '{participacion_id}' como completada.")
                    
                    # --- Lógica para la notificación interna ---
                    notificacion_mensaje = (
                        f"Has marcado '{participacion.curso.nombre}' como completado. "
                        "¡Ayúdanos a mejorar rellenando nuestra encuesta de satisfacción!"
                    )
                    url_encuesta = reverse('formacion:encuesta_satisfaccion', args=[participacion.id])
                    
                    Notificacion.objects.create(
                        usuario=request.user,
                        mensaje=notificacion_mensaje,
                        tipo='info',
                        url=url_encuesta,
                        leida=False
                    )
                    logger.info(f"Notificación para la encuesta de satisfacción creada para el usuario '{request.user.username}' y la participación '{participacion_id}'.")
                    # --- Fin Lógica para la notificación interna ---

                # Redirige a la encuesta de satisfacción
                return redirect('formacion:encuesta_satisfaccion', participacion_id=participacion.id)
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado al marcar la participación como completada: {e}")
                logger.error(f"Error al marcar la participación '{participacion_id}' como completada para el usuario '{request.user.username}': {e}", exc_info=True)
                return redirect('formacion:mis_cursos')
        else:
            messages.warning(request, f"La participación en '{participacion.curso.nombre}' ya está en un estado final ({participacion.get_estado_display()}).")
            logger.warning(f"El usuario '{request.user.username}' intentó marcar la participación '{participacion_id}' que ya estaba en estado '{participacion.estado}'.")
            return redirect('formacion:detalle_participacion', participacion_id=participacion.id)
    else:
        messages.error(request, "Método no permitido para esta acción.")
        logger.warning(f"El usuario '{request.user.username}' intentó usar un método no permitido ({request.method}) para la participación '{participacion_id}'.")
        return redirect('formacion:mis_cursos')
    

@login_required
def detalle_participacion(request, participacion_id):
    """
    Vista para ver el detalle de una participación específica en un curso.
    """
    try:
        participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)
        logger.info(f"El usuario '{request.user.username}' ha accedido al detalle de la participación '{participacion_id}'.")
    except Participacion.DoesNotExist:
        messages.error(request, 'La participación especificada no existe o no te pertenece.')
        logger.error(f"Intento de acceso no autorizado o a una participación inexistente por el usuario '{request.user.username}' para el ID '{participacion_id}'.")
        return redirect('formacion:mis_cursos')
        
    estados_finales_participacion = ['completado', 'cancelado', 'abandonado', 'rechazado']

    context = {
        'participacion': participacion,
        'curso': participacion.curso,
        'estados_finales_participacion': estados_finales_participacion,
    }
    return render(request, 'formacion/detalle_participacion.html', context)

@login_required
def serve_protected_titulacion(request, filename):
    """
    Vista para servir un archivo de titulación de forma segura.
    Verifica que el usuario está autenticado y que el archivo le pertenece.
    """
    try:
        # Busca la titulación en la base de datos por el nombre del archivo.
        # Asume que el campo 'archivo' en el modelo ya contiene la ruta relativa
        # 'titulaciones/nombre_del_archivo.pdf'.
        # Busca la titulación por el nombre de archivo en el campo 'documento_adjunto'.
        titulacion = get_object_or_404(Titulacion, documento_adjunto__endswith=filename)
    except Http404:
        # Si la titulación no existe en la base de datos, devuelve un 404
        # (El log en este caso ya ha sido gestionado por el manejador de excepciones de Django)
        logger.error(f"Intento de acceso a un archivo no registrado: {filename}")
        raise Http404("El archivo solicitado no existe o no está registrado.")

    # Verifica si el empleado asociado a la titulación es el usuario actual.
    if titulacion.empleado != request.user:
        # Si el usuario no es el propietario, niega el acceso.
        logger.error(f"Intento de acceso no autorizado al archivo {filename} por el usuario {request.user.username}.")
        return HttpResponseForbidden("No tienes permiso para ver este archivo.")

    # Utiliza la ruta del archivo del campo del modelo para garantizar que es correcta.
    file_path = titulacion.documento_adjunto.path

    if os.path.exists(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
            
        response = FileResponse(open(file_path, 'rb'), content_type=mime_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response
    else:
        # El archivo no se encontró físicamente, lo que es un problema serio.
        logger.error(f"Archivo físico no encontrado para la titulación '{titulacion.id}': {file_path}")
        raise Http404("El archivo físico no existe en el servidor.")
    