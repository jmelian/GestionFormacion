# formacion/views.py
import datetime
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
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.template.loader import render_to_string # Para renderizar el contenido del email
from django.utils.html import strip_tags
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.transaction import TransactionManagementError



# --- Funciones de Comprobación de Roles ---
def is_in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()

def es_empleado(user):
    # Un empleado es cualquier usuario autenticado que pertenece al grupo 'Empleados'
    return is_in_group(user, settings.GRUPO_EMPLEADO)

def es_coordinador(user):
    if not user.is_authenticated:
        return False

    is_in_coord_group = is_in_group(user, settings.GRUPO_COORDINADOR)

    # Nuevo chequeo: El usuario pertenece a un departamento, Y ese departamento lo tiene como coordinador.
    is_coordinator_of_own_department = False
    if hasattr(user, 'departamento') and user.departamento is not None:
        # Aquí verificamos si el coordinador del departamento al que pertenece el usuario ES el propio usuario.
        # El related_name de ForeignKey es 'coordinador' en Departamento, así que user.departamento.coordinador
        # ya apunta al Empleado (AUTH_USER_MODEL)
        if hasattr(user.departamento, 'coordinador') and user.departamento.coordinador == user:
            is_coordinator_of_own_department = True
            
    final_result = is_in_coord_group and is_coordinator_of_own_department

    return final_result

def es_formacion(user):
    return is_in_group(user, settings.GRUPO_FORMACION)

def es_formacion_o_direccion(user):
    return es_formacion(user) or es_direccion(user)

def es_formacion_o_direccion_o_rrhh(user):
    return es_formacion(user) or es_direccion(user) or es_rrhh(user)


def es_rrhh(user):
    return is_in_group(user, settings.GRUPO_RRHH)

def es_direccion(user):
    return is_in_group(user, settings.GRUPO_DIRECCION)

def es_admin(user):
    return user.is_authenticated and user.is_superuser

def custom_logout(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('formacion:login')

def solo_superusuarios(user):
    return user.is_superuser


# --- Vistas Generales ---

from django.views.generic import ListView


@login_required
def proximos_cursos(request):
    cursos = Curso.objects.filter(fecha_inicio__gte=date.today()).order_by('fecha_inicio')
    return render(request, 'formacion/proximos_cursos.html', {'cursos': cursos})

@login_required
def mis_cursos(request):
    participaciones_qs = Participacion.objects.filter(
        empleado=request.user,
        estado__in=['aceptado', 'asistido', 'completado', 'pendiente', 'solicitado', 'confirmada']
    ).select_related('curso')

    participaciones_with_flags = []
    for p in participaciones_qs:
        p.can_cancel = (
            p.estado not in ['completado', 'asistido', 'cancelado', 'rechazado'] and
            p.curso.fecha_fin and p.curso.fecha_fin >= date.today()
        )
        participaciones_with_flags.append(p)

    return render(request, 'formacion/mis_cursos.html', {'participaciones': participaciones_with_flags})

@login_required
@user_passes_test(es_coordinador, login_url='formacion:dashboard') 
def equipo_departamento(request):
    empleado_coordinador = request.user
    departamento = empleado_coordinador.departamento

    if not departamento:
        messages.error(request, 'No estás asignado como coordinador de ningún departamento.')
        return redirect('formacion:dashboard')

    equipo = Empleado.objects.filter(departamento=departamento).order_by('last_name', 'first_name')
    
    return render(request, 'formacion/equipo_departamento.html', {
        'departamento': departamento,
        'equipo': equipo
    })

@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u), login_url='formacion:dashboard')
def certificados_pendientes_rrhh(request):
    if request.method == 'POST':
        participacion_id = request.POST.get('participacion_id')
        participacion = get_object_or_404(Participacion, id=participacion_id)
        if not participacion.validado:
            participacion.validado = True
            participacion.save()
            messages.success(request, f"Certificado de {participacion.empleado.get_full_name()} validado correctamente.")
        else:
            messages.info(request, "Este certificado ya estaba validado.")
        # Ojo: 'certificados_pendientes_rrhh' necesita ser el nombre de la URL, no de la vista.
        # Asumiendo que tu url conf tiene un 'name'='certificados_pendientes_rrhh'
        return redirect('formacion:certificados_pendientes_rrhh')

    participaciones = Participacion.objects.filter(
        validado=False,
        estado__in=['completado', 'asistido'],
        nota_final__isnull=False
    ).exclude(nota_final="").select_related('empleado__departamento', 'curso')

    return render(request, 'formacion/certificados_pendientes_rrhh.html', {'participaciones': participaciones})

@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u), login_url='formacion:dashboard')
def titulaciones_pendientes_rrhh(request):
    if request.method == 'POST':
        titulacion_id = request.POST.get('titulacion_id')
        action = request.POST.get('action') # 'validar' o 'rechazar'
        titulacion = get_object_or_404(Titulacion, id=titulacion_id)

        if action == 'validar':
            # Solo validar si está pendiente de revisión
            if titulacion.estado == 'pendiente':
                with transaction.atomic():
                    # Eliminamos titulacion.validado_rrhh = True
                    titulacion.estado = 'aprobado'   # Establece el estado a 'aprobado'
                    titulacion.save()

                    Notificacion.objects.create(
                        usuario=titulacion.empleado,
                        mensaje=f"Tu titulación de '{titulacion.nombre}' ha sido **validada** por RRHH.",
                        tipo='success',
                        url=reverse('formacion:detalle_titulacion', args=[titulacion.id]),
                        leida=False
                    )
                    messages.success(request, f"Titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) validada correctamente.")
            else:
                messages.info(request, f"Esta titulación ya estaba '{titulacion.get_estado_display()}'. No se puede validar.")
        
        elif action == 'rechazar':
            motivo_rechazo = request.POST.get('motivo_rechazo', '').strip()
            if not motivo_rechazo:
                messages.error(request, "El motivo del rechazo no puede estar vacío.")
                current_query_params = request.GET.urlencode()
                return redirect(f"{reverse('formacion:titulaciones_pendientes_rrhh')}?{current_query_params}")

            # Solo rechazar si está pendiente de revisión
            if titulacion.estado == 'pendiente':
                with transaction.atomic():
                    titulacion.estado = 'rechazado' # Establece el estado a 'rechazado'
                    titulacion.motivo_rechazo = motivo_rechazo # Guarda el motivo del rechazo
                    # Eliminamos titulacion.validado_rrhh = False (ya no es necesario)
                    titulacion.save()

                    Notificacion.objects.create(
                        usuario=titulacion.empleado,
                        mensaje=f"Tu titulación de '{titulacion.nombre}' ha sido **rechazada** por RRHH. Motivo: {motivo_rechazo}",
                        tipo='danger',
                        url=reverse('formacion:detalle_titulacion', args=[titulacion.id]),
                        leida=False
                    )
                    messages.success(request, f"Titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) rechazada correctamente.")
            else:
                messages.info(request, f"La titulación de {titulacion.empleado.get_full_name()} ({titulacion.nombre}) ya ha sido '{titulacion.get_estado_display()}'. No se puede rechazar.")
        
        current_query_params = request.GET.urlencode()
        return redirect(f"{reverse('formacion:titulaciones_pendientes_rrhh')}?{current_query_params}")

    # --- Lógica para solicitudes GET ---
    # Ahora filtramos SOLO por estado='pendiente'
    titulaciones_queryset = Titulacion.objects.filter(
        estado='pendiente' # Solo muestra las titulaciones que están pendientes de revisión por RRHH
    ).select_related('empleado', 'curso_relacionado')

    # ... (el resto de tu lógica de ordenación y paginación es la misma) ...
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

    items_per_page = 10
    paginator = Paginator(titulaciones_queryset, items_per_page)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']

    context = {
        'titulaciones': page_obj,
        'page_obj': page_obj,
        'query_params': query_params,
        'sort_by': sort_by,
        'direction': direction,
    }
    return render(request, 'formacion/titulaciones_pendientes_rrhh.html', context)


@login_required
def detalle_titulacion(request, titulacion_id):
    """
    Vista para mostrar los detalles de una titulación específica.
    Permite a los empleados ver sus propias titulaciones
    y a RRHH/Admin ver cualquier titulación.
    """
    titulacion = get_object_or_404(Titulacion, id=titulacion_id)

    # Asegurarse de que solo el empleado dueño o RRHH/Admin pueden ver la titulación
    if request.user == titulacion.empleado or es_rrhh(request.user) or es_admin(request.user):
        context = {
            'titulacion': titulacion
        }
        return render(request, 'formacion/detalle_titulacion.html', context)
    else:
        messages.error(request, "No tienes permiso para ver esta titulación.")
        return redirect('formacion:dashboard')
    

@login_required
@user_passes_test(es_coordinador, login_url='formacion:dashboard') 
def preseleccionar_empleado(request):
    empleado_coordinador = request.user
    departamento = empleado_coordinador.departamento 

    empleados_del_departamento = Empleado.objects.filter(departamento=departamento).order_by('last_name', 'first_name')

    editar_preseleccion = None
    if 'editar' in request.GET:
        editar_preseleccion = get_object_or_404(Preseleccion, id=request.GET.get('editar'))
        if editar_preseleccion.empleado.departamento != departamento:
            messages.error(request, "No tienes permiso para editar esta preselección.")
            return redirect('formacion:preseleccionar_empleado')

        form = PreseleccionForm(instance=editar_preseleccion, coordinador=empleado_coordinador)
    else:
        form = PreseleccionForm(coordinador=empleado_coordinador)

    if request.method == 'POST':
        if 'eliminar' in request.POST:
            pre = get_object_or_404(Preseleccion, id=request.POST['eliminar'])
            if pre.empleado.departamento == departamento:
                pre.delete()
                messages.success(request, f"Preselección de {pre.empleado.get_full_name()} eliminada.")
            else:
                messages.error(request, "No tienes permiso para eliminar esta preselección.")
            return redirect('formacion:preseleccionar_empleado')

        if 'crear' in request.POST or 'actualizar' in request.POST:
            form = PreseleccionForm(request.POST, coordinador=empleado_coordinador)
            if form.is_valid():
                with transaction.atomic():
                    if 'actualizar' in request.POST:
                        pre_id = request.POST.get('editar_id')
                        pre = get_object_or_404(Preseleccion, id=pre_id)
                        if pre.empleado.departamento != departamento:
                            messages.error(request, "Acción no permitida.")
                            return redirect('formacion:preseleccionar_empleado')

                        form = PreseleccionForm(request.POST, instance=pre, coordinador=empleado_coordinador)
                        form.save()
                        messages.success(request, "Preselección actualizada correctamente.")
                    else:
                        nueva_preseleccion = form.save(commit=False)
                        nueva_preseleccion.creado_por = request.user
                        nueva_preseleccion.save()
                        messages.success(request, f"Preselección para {nueva_preseleccion.empleado.get_full_name()} creada.")

                        mensaje_notificacion = f'Nueva preselección creada por "{empleado_coordinador.get_full_name()}" para el curso "{nueva_preseleccion.curso.nombre}" de "{nueva_preseleccion.empleado.get_full_name()}". Pendiente de validar.'

                        grupos_a_notificar = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]

                        try:
                            for group_name in grupos_a_notificar:
                                group = Group.objects.get(name=group_name)
                                usuarios_del_grupo = Empleado.objects.filter(groups=group)
                                for usuario_grupo in usuarios_del_grupo:
                                    if usuario_grupo != empleado_coordinador:
                                        Notificacion.objects.create(
                                            usuario=usuario_grupo,
                                            mensaje=mensaje_notificacion,
                                            tipo='info'
                                        )
                            super_usuarios = Empleado.objects.filter(is_superuser=True).exclude(groups__name__in=grupos_a_notificar).distinct()
                            for admin_user in super_usuarios:
                                if admin_user != empleado_coordinador:
                                    Notificacion.objects.create(
                                        usuario=admin_user,
                                        mensaje=mensaje_notificacion,
                                        tipo='info'
                                    )
                        except Group.DoesNotExist as e:
                            print(f"ERROR: Uno de los grupos de notificación no existe: {e}")
                            messages.warning(request, "Advertencia: Algunos grupos de validación no pudieron ser notificados porque no existen.")
                        except Exception as e:
                            print(f"ERROR inesperado al notificar por preselección: {e}")
                            messages.error(request, "Ocurrió un error al enviar algunas notificaciones.")

                return redirect('formacion:preseleccionar_empleado')
            else:
                messages.error(request, "Error en el formulario. Por favor, revisa los datos.")

    preselecciones = Preseleccion.objects.filter(empleado__departamento=departamento).order_by('curso__nombre', 'prioridad').select_related('empleado', 'curso', 'creado_por')
    return render(request, 'formacion/preseleccionar_empleado.html', {
        'form': form,
        'preselecciones': preselecciones,
        'editar': editar_preseleccion,
        'departamento': departamento,
    })


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
def gestionar_preselecciones_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    grupos_permitidos = [
        settings.GRUPO_FORMACION,
        settings.GRUPO_RRHH,
        settings.GRUPO_DIRECCION
    ]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('formacion:dashboard')

    participaciones_activas_ids = Participacion.objects.filter(
        curso=curso,
        estado__in=['aceptado', 'asistido', 'completado']
    ).values_list('empleado_id', flat=True)

    participaciones_prefetch = Prefetch(
        'empleado__participaciones',
        queryset=Participacion.objects.filter(curso=curso),
        to_attr='_participaciones_para_curso_en_empleado'
    )

    #preselecciones = Preseleccion.objects.filter(curso=curso).exclude(
    #    empleado_id__in=participaciones_activas_ids
    #).order_by('prioridad').select_related('empleado__departamento').prefetch_related(participaciones_prefetch)

    preselecciones = Preseleccion.objects.filter(curso=curso).order_by('prioridad').select_related('empleado__departamento').prefetch_related(participaciones_prefetch)


    for preseleccion in preselecciones:
        if hasattr(preseleccion.empleado, '_participaciones_para_curso_en_empleado') and preseleccion.empleado._participaciones_para_curso_en_empleado:
            preseleccion.participacion = next((p for p in preseleccion.empleado._participaciones_para_curso_en_empleado if p.curso_id == curso.id), None)
        else:
            preseleccion.participacion = None

    if request.method == 'POST':
        if 'confirmar_seleccionados' in request.POST:
            empleados_seleccionados_ids = request.POST.getlist('empleados_seleccionados')

            empleados_ya_activos = set(
                Participacion.objects.filter(
                    curso=curso,
                    empleado_id__in=empleados_seleccionados_ids,
                    estado__in=['aceptado', 'asistido', 'completado']
                ).values_list('empleado_id', flat=True)
            )

            empleados_a_procesar_final = [
                int(emp_id_str) for emp_id_str in empleados_seleccionados_ids
                if int(emp_id_str) not in empleados_ya_activos
            ]

            confirmed_count = 0

            with transaction.atomic():
                for emp_id in empleados_a_procesar_final:
                    if curso.plazas_disponibles <= 0:
                        messages.warning(request, f"Se agotaron las plazas disponibles para el curso '{curso.nombre}'. Se confirmaron {confirmed_count} participantes. Los restantes no pudieron ser aceptados.")
                        break

                    empleado = get_object_or_404(Empleado, id=emp_id)

                    participacion, created = Participacion.objects.get_or_create(
                        curso=curso,
                        empleado=empleado,
                        defaults={'estado': 'aceptado'}
                    )
                    if not created:
                        if participacion.estado not in ['aceptado', 'asistido', 'completado']:
                            participacion.estado = 'aceptado'
                            participacion.save()
                        else:
                            messages.info(request, f"{empleado.get_full_name()} ya está activo en {curso.nombre}. No se procesa duplicado.")
                            continue

                    curso.plazas_disponibles -= 1
                    curso.save(update_fields=['plazas_disponibles'])

                    Preseleccion.objects.filter(curso=curso, empleado=empleado).delete()

                    confirmed_count += 1

                    Notificacion.objects.create(
                        usuario=empleado,
                        mensaje=f'Tu participación en el curso "{curso.nombre}" ha sido ACEPTADA.',
                        tipo='success'
                    )

                    coordinador_empleado = None
                    if empleado.departamento and empleado.departamento.coordinador:
                        coordinador_empleado = empleado.departamento.coordinador
                    if coordinador_empleado:
                        Notificacion.objects.create(
                            usuario=coordinador_empleado,
                            mensaje=f'La participación de "{empleado.get_full_name()}" en el curso "{curso.nombre}" ha sido ACEPTADA.',
                            tipo='info'
                        )

                if confirmed_count > 0:
                    messages.success(request, f"Se confirmaron {confirmed_count} participantes para el curso '{curso.nombre}'.")

                num_selected_initially = len(empleados_seleccionados_ids)
                if num_selected_initially > confirmed_count:
                    messages.info(request, f"De {num_selected_initially} empleados seleccionados inicialmente, solo {confirmed_count} fueron confirmados debido a plazas limitadas o porque ya tenían participación activa.")

                return redirect('formacion:gestionar_preselecciones_curso', curso_id=curso.id)

        elif 'accion' in request.POST and 'preseleccion_id' in request.POST:
            preseleccion_id = request.POST.get('preseleccion_id')
            accion = request.POST.get('accion')

            preseleccion = get_object_or_404(Preseleccion, id=preseleccion_id, curso=curso)

            with transaction.atomic():
                if accion == 'aceptar':
                    if curso.plazas_disponibles <= 0:
                        messages.error(request, f'No hay plazas disponibles para aceptar a {preseleccion.empleado.get_full_name()} en "{curso.nombre}".')
                        preseleccion.delete() # Eliminar preselección aunque no haya plazas
                        return redirect('formacion:gestionar_preselecciones_curso', curso_id=curso.id)

                    participacion_existente = Participacion.objects.filter(
                        empleado=preseleccion.empleado,
                        curso=curso,
                        estado__in=['aceptado', 'asistido', 'completado']
                    ).first()

                    if participacion_existente:
                        messages.info(request, f'"{preseleccion.empleado.get_full_name()}" ya tiene una participación activa en "{curso.nombre}".')
                    else:
                        participacion, created = Participacion.objects.get_or_create(
                            empleado=preseleccion.empleado,
                            curso=curso,
                            defaults={'estado': 'aceptado'}
                        )
                        if not created:
                            if participacion.estado in ['rechazado', 'cancelado', 'pendiente', 'solicitado']:
                                participacion.estado = 'aceptado'
                                participacion.save()

                        curso.plazas_disponibles -= 1
                        curso.save(update_fields=['plazas_disponibles'])

                        messages.success(request, f'Participación de "{preseleccion.empleado.get_full_name()}" en "{curso.nombre}" ha sido aceptada.')
                        Notificacion.objects.create(
                            usuario=preseleccion.empleado,
                            mensaje=f'Tu participación en el curso "{curso.nombre}" ha sido ACEPTADA.',
                            tipo='success'
                        )
                        coordinador_empleado = None
                        if preseleccion.empleado.departamento and preseleccion.empleado.departamento.coordinador:
                            coordinador_empleado = preseleccion.empleado.departamento.coordinador

                        # Notificación para el coordinador del departamento del empleado
                        # Solo si el coordinador existe Y NO ES EL MISMO EMPLEADO que acaba de ser aceptado!
                        if coordinador_empleado and coordinador_empleado != preseleccion.empleado:
                            Notificacion.objects.create(
                                usuario=coordinador_empleado,
                                mensaje=f'La participación de "{preseleccion.empleado.get_full_name()}" en el curso "{curso.nombre}" ha sido ACEPTADA.',
                                tipo='info'
                            )
                        preseleccion.delete()

                elif accion == 'rechazar':
                    participacion_existente = Participacion.objects.filter(
                        empleado=preseleccion.empleado,
                        curso=curso,
                        estado__in=['aceptado', 'asistido', 'completado']
                    ).first()

                    if participacion_existente:
                        messages.error(request, f'"{preseleccion.empleado.get_full_name()}" ya está confirmado en "{curso.nombre}". No se puede rechazar directamente desde aquí. Considere una acción de cancelación si es necesario.')
                    else:
                        participacion, created = Participacion.objects.get_or_create(
                            empleado=preseleccion.empleado,
                            curso=curso,
                            defaults={'estado': 'rechazado'}
                        )
                        if not created:
                            if participacion.estado != 'rechazado':
                                participacion.estado = 'rechazado'
                                participacion.save()

                        messages.info(request, f'Preselección de "{preseleccion.empleado.get_full_name()}" para "{curso.nombre}" ha sido rechazada.')
                        Notificacion.objects.create(
                            usuario=preseleccion.empleado,
                            mensaje=f'Tu preselección para el curso "{curso.nombre}" ha sido RECHAZADA.',
                            tipo='warning'
                        )
                        coordinador_empleado = None
                        if preseleccion.empleado.departamento and preseleccion.empleado.departamento.coordinador:
                            coordinador_empleado = preseleccion.empleado.departamento.coordinador
                        if coordinador_empleado:
                            Notificacion.objects.create(
                                usuario=coordinador_empleado,
                                mensaje=f'La preselección de "{preseleccion.empleado.get_full_name()}" para el curso "{curso.nombre}" ha sido RECHAZADA.',
                                tipo='info'
                            )
                        preseleccion.delete()

                messages.success(request, f'Preselección de "{preseleccion.empleado.get_full_name()}" eliminada de la lista.')
            return redirect('formacion:gestionar_preselecciones_curso', curso_id=curso.id)

    context = {
        'curso': curso,
        'preselecciones': preselecciones,
    }
    return render(request, 'formacion/confirmar_preseleccionados.html', context)


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
def confirmar_preseleccionados_lista(request):
    grupos_permitidos = [
        settings.GRUPO_FORMACION,
        settings.GRUPO_RRHH,
        settings.GRUPO_DIRECCION
    ]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('formacion:dashboard')

    # Filtra cursos que tienen al menos una preselección
    # Y cuya fecha de fin es hoy o en el futuro, O cuya fecha de fin es nula (cursos continuos)
    cursos_con_preselecciones = Curso.objects.filter(
        preseleccionados__isnull=False # Asegura que el curso tiene preselecciones
    ).filter(
        Q(fecha_fin__gte=datetime.date.today()) | Q(fecha_fin__isnull=True) # Incluye cursos futuros/actuales o sin fecha de fin
    ).distinct().annotate(
        num_pendientes=Count('preseleccionados', distinct=True) # Cuenta las preselecciones para cada curso
    ).order_by('nombre')

    context = {
        'cursos': cursos_con_preselecciones,
        'has_preselecciones': cursos_con_preselecciones.exists(),
    }
    return render(request, 'formacion/confirmar_preseleccionados_lista.html', context)



@login_required
@user_passes_test(lambda u: es_formacion_o_direccion(u) or es_coordinador(u), login_url='formacion:dashboard') # CAMBIADO AQUÍ
def gestionar_preseleccion(request, preseleccion_id):
    preseleccion = get_object_or_404(Preseleccion, id=preseleccion_id)

    empleado_preseleccionado = preseleccion.empleado
    curso_preseleccionado = preseleccion.curso
    usuario_actual = request.user

    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]).exists()
    es_admin = usuario_actual.is_superuser

    es_coordinador_del_departamento_de_la_preseleccion = False
    if es_coordinador(usuario_actual) and empleado_preseleccionado.departamento == getattr(usuario_actual, 'departamento_coordinado', None):
        es_coordinador_del_departamento_de_la_preseleccion = True

    if not (es_rrhh_o_formacion_o_direccion or es_admin or es_coordinador_del_departamento_de_la_preseleccion):
        messages.error(request, "No tienes permisos para gestionar esta preselección.")
        return redirect('formacion:dashboard')

    accion = request.POST.get('accion')
    next_url = request.POST.get('next', 'formacion:confirmar_preseleccionados_lista')


    with transaction.atomic():
        if accion == 'aceptar':
            if curso_preseleccionado.plazas_disponibles <= 0:
                messages.error(request, f"No hay plazas disponibles para el curso '{curso_preseleccionado.nombre}'. No se puede aceptar la preselección.")
                preseleccion.delete()
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
                else:
                    messages.warning(request, f"La participación de {participacion.empleado.get_full_name()} para '{curso_preseleccionado.nombre}' ya estaba aceptada.")
                    preseleccion.delete()
                    return redirect(next_url)

            curso_preseleccionado.plazas_disponibles -= 1
            curso_preseleccionado.save(update_fields=['plazas_disponibles'])

            preseleccion.delete()

            messages.success(request, f"Preselección de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' **ACEPTADA**. Plaza asignada.")

            Notificacion.objects.create(
                usuario=empleado_preseleccionado,
                mensaje=f"¡Enhorabuena! Tu preselección para el curso '{curso_preseleccionado.nombre}' ha sido **ACEPTADA** y se ha creado tu participación.",
                tipo='success'
            )

            coordinador_empleado = None
            if empleado_preseleccionado.departamento and empleado_preseleccionado.departamento.coordinador:
                coordinador_empleado = empleado_preseleccionado.departamento.coordinador

            if coordinador_empleado and coordinador_empleado != usuario_actual:
                Notificacion.objects.create(
                    usuario=coordinador_empleado,
                    mensaje=f'La preselección de "{empleado_preseleccionado.get_full_name()}" para el curso "{curso_preseleccionado.nombre}" ha sido **ACEPTADA**.',
                    tipo='info'
                )

        elif accion == 'rechazar':
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

                if participacion.estado != 'rechazado':
                    participacion.estado = 'rechazado'
                    participacion.save(update_fields=['estado'])
                    messages.info(request, f"La participación existente de {empleado_preseleccionado.get_full_name()} se ha actualizado a 'rechazado'.")
                else:
                    messages.warning(request, f"La participación de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' ya estaba rechazada.")

            preseleccion.delete()

            messages.success(request, f"Preselección de {empleado_preseleccionado.get_full_name()} para '{curso_preseleccionado.nombre}' **RECHAZADA**.")

            coordinador_empleado = None
            if empleado_preseleccionado.departamento and empleado_preseleccionado.departamento.coordinador:
                coordinador_empleado = empleado_preseleccionado.departamento.coordinador

            if coordinador_empleado and coordinador_empleado != usuario_actual:
                Notificacion.objects.create(
                    usuario=coordinador_empleado,
                    mensaje=f'La preselección de "{empleado_preseleccionado.get_full_name()}" para el curso "{curso_preseleccionado.nombre}" ha sido **RECHAZADA**.',
                    tipo='warning'
                )

        else:
            messages.error(request, 'Acción no válida.')

    return redirect(next_url)

@login_required
@require_POST
def cancelar_participacion(request, participacion_id):
    participacion = get_object_or_404(Participacion, id=participacion_id)
    usuario_actual = request.user

    es_propio_empleado = (participacion.empleado == usuario_actual)

    es_coordinador_departamento = False
    if es_coordinador(usuario_actual) and participacion.empleado.departamento == getattr(usuario_actual, 'departamento_coordinado', None):
        es_coordinador_departamento = True

    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]).exists()
    es_admin = usuario_actual.is_superuser

    puede_cancelar = es_propio_empleado or es_coordinador_departamento or es_rrhh_o_formacion_o_direccion or es_admin

    if participacion.curso.fecha_inicio <= date.today() and not (es_rrhh_o_formacion_o_direccion or es_admin):
        messages.error(request, "No se puede cancelar una participación una vez iniciado el curso, a menos que tengas permisos de RRHH/Formación/Dirección/Admin.")
        return redirect('formacion:mis_cursos')

    if participacion.estado in ['completado', 'asistido']:
        messages.error(request, f"No se puede cancelar la participación en el curso '{participacion.curso.nombre}' porque ya ha sido completado o asistido.")
        return redirect('formacion:mis_cursos')

    if not puede_cancelar:
        messages.error(request, "No tienes permisos para cancelar esta participación.")
        return redirect('formacion:mis_cursos')

    with transaction.atomic():
        participacion.estado = 'cancelado'
        participacion.save()

        participacion.curso.plazas_disponibles += 1
        participacion.curso.save(update_fields=['plazas_disponibles'])

        messages.success(request, f"Participación en {participacion.curso.nombre} cancelada correctamente.")

        Notificacion.objects.create(
            usuario=usuario_actual,
            mensaje=f"Tu participación en el curso '{participacion.curso.nombre}' ha sido CANCELADA.",
            tipo='info'
        )

        coordinador_del_empleado_participacion = None
        if participacion.empleado.departamento and participacion.empleado.departamento.coordinador:
            coordinador_del_empleado_participacion = participacion.empleado.departamento.coordinador

        if coordinador_del_empleado_participacion:
            Notificacion.objects.create(
                usuario=coordinador_del_empleado_participacion,
                mensaje=f'La participación de "{participacion.empleado.get_full_name()}" en el curso "{participacion.curso.nombre}" ha sido CANCELADA.',
                tipo='warning'
            )

        try:
            formacion_group = Group.objects.get(name=settings.GRUPO_FORMACION)
            usuarios_formacion_a_notificar = Empleado.objects.filter(
                groups=formacion_group
            ).exclude(
                groups__name=settings.GRUPO_DIRECCION
            ).exclude(
                id=usuario_actual.id
            ).distinct()

            for usuario_formacion in usuarios_formacion_a_notificar:
                Notificacion.objects.create(
                    usuario=usuario_formacion,
                    mensaje=f'La participación de "{participacion.empleado.get_full_name()}" en el curso "{participacion.curso.nombre}" ha sido CANCELADA.',
                    tipo='warning'
                )

        except Group.DoesNotExist:
            print("ERROR: El grupo settings.GRUPO_FORMACION NO existe en la base de datos. Asegúrate de crearlo en el admin de Django.")
        except Exception as e:
            print(f"ERROR inesperado al notificar al grupo Formación: {e}")

    return redirect('formacion:mis_cursos')

@login_required
@require_POST
def rechazar_participacion(request, participacion_id):
    participacion = get_object_or_404(Participacion, id=participacion_id)
    usuario_actual = request.user

    es_coordinador_departamento = False
    if es_coordinador(usuario_actual) and participacion.empleado.departamento == getattr(usuario_actual, 'departamento_coordinado', None):
        es_coordinador_departamento = True

    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]).exists()
    es_admin = usuario_actual.is_superuser

    puede_rechazar = es_coordinador_departamento or es_rrhh_o_formacion_o_direccion or es_admin

    if not puede_rechazar:
        messages.error(request, "No tienes permisos para rechazar esta participación.")
        return redirect('formacion:dashboard')

    if participacion.estado in ['completado', 'asistido', 'cancelado', 'rechazado']:
        messages.error(request, f"No se puede rechazar la participación en el curso '{participacion.curso.nombre}' porque ya está en estado '{participacion.estado}'.")
        return redirect('formacion:estado_cursos')

    if participacion.curso.fecha_inicio <= date.today() and not (es_rrhh_o_formacion_o_direccion or es_admin):
        messages.error(request, "No se puede rechazar una participación una vez iniciado el curso, a menos que tengas permisos de RRHH/Formación/Dirección/Admin.")
        return redirect('formacion:estado_cursos')

    with transaction.atomic():
        if participacion.estado == 'aceptado':
            participacion.curso.plazas_disponibles += 1
            participacion.curso.save(update_fields=['plazas_disponibles'])
            messages.info(request, f"Se ha liberado una plaza para el curso '{participacion.curso.nombre}' tras el rechazo.")

        participacion.estado = 'rechazado'
        participacion.save()

        messages.success(request, f"Participación de {participacion.empleado.get_full_name()} en {participacion.curso.nombre} RECHAZADA correctamente.")

        Notificacion.objects.create(
            usuario=participacion.empleado,
            mensaje=f"Tu participación en el curso '{participacion.curso.nombre}' ha sido RECHAZADA.",
            tipo='danger'
        )

        coordinador_del_empleado_participacion = None
        if participacion.empleado.departamento and participacion.empleado.departamento.coordinador:
            coordinador_del_empleado_participacion = participacion.empleado.departamento.coordinador

        if coordinador_del_empleado_participacion and coordinador_del_empleado_participacion != usuario_actual:
            Notificacion.objects.create(
                usuario=coordinador_del_empleado_participacion,
                mensaje=f'La participación de "{participacion.empleado.get_full_name()}" en el curso "{participacion.curso.nombre}" ha sido RECHAZADA.',
                tipo='warning'
            )

        try:
            formacion_group = Group.objects.get(name=settings.GRUPO_FORMACION)
            usuarios_formacion_a_notificar = Empleado.objects.filter(
                groups=formacion_group
            ).exclude(
                groups__name=settings.GRUPO_DIRECCION
            ).exclude(
                id=usuario_actual.id
            ).distinct()

            for usuario_formacion in usuarios_formacion_a_notificar:
                Notificacion.objects.create(
                    usuario=usuario_formacion,
                    mensaje=f'La participación de "{participacion.empleado.get_full_name()}" en el curso "{participacion.curso.nombre}" ha sido RECHAZADA.',
                    tipo='warning'
                )

        except Group.DoesNotExist:
            print("ERROR: El grupo settings.GRUPO_FORMACION NO existe en la base de datos. Asegúrate de crearlo en el admin de Django.")
        except Exception as e:
            print(f"ERROR inesperado al notificar al grupo Formación en rechazo: {e}")

    return redirect('formacion:estado_cursos')


def listar_participantes_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    participaciones = Participacion.objects.filter(curso=curso).order_by(
        'empleado__last_name', 'empleado__first_name'
    ).select_related('empleado', 'curso', 'empleado__departamento', 'empleado__codigo_puesto')

    usuario_actual = request.user
    es_rrhh_o_formacion_o_direccion = usuario_actual.groups.filter(name__in=[settings.GRUPO_FORMACION, settings.GRUPO_DIRECCION, settings.GRUPO_RRHH]).exists()
    es_admin = usuario_actual.is_superuser

    es_coordinador_curso_solicitante = False
    if es_coordinador(usuario_actual) and curso.departamento_solicitante:
        if getattr(getattr(usuario_actual, 'departamento_coordinado', None), 'nombre', None) == curso.departamento_solicitante:
            es_coordinador_curso_solicitante = True

    if not (es_rrhh_o_formacion_o_direccion or es_admin or es_coordinador_curso_solicitante):
        messages.error(request, "No tienes permisos para ver los participantes de este curso.")
        return redirect('formacion:dashboard') # CAMBIADO AQUÍ

    estados_no_rechazables = ['rechazado', 'cancelado', 'completado', 'asistido']
    for participacion in participaciones:
        tiene_permiso_por_rol = (es_rrhh_o_formacion_o_direccion or es_admin)
        
        tiene_permiso_por_coordinacion = False
        if es_coordinador(usuario_actual) and participacion.empleado.departamento == getattr(usuario_actual, 'departamento_coordinado', None):
            tiene_permiso_por_coordinacion = True
        
        participacion.puede_ver_boton_rechazar = tiene_permiso_por_rol or tiene_permiso_por_coordinacion

        participacion.puede_ser_rechazada = participacion.estado not in estados_no_rechazables
        
        participacion.boton_rechazar_activo = participacion.puede_ver_boton_rechazar and participacion.puede_ser_rechazada


    context = {
        'curso': curso,
        'participantes': participaciones,
        'usuario_actual': usuario_actual,
    }
    return render(request, 'formacion/listar_participantes_curso.html', context)


# --- Gestión de Usuarios/Empleados ---
@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u) or es_formacion_o_direccion(u), login_url='formacion:dashboard')
def empleados_con_formacion(request):
    empleados_qs = Empleado.objects.all()

    # --- Filtro por Departamento ---
    departamento_id = request.GET.get('departamento')
    selected_departamento = None # Inicializa para el contexto
    if departamento_id:
        try:
            selected_departamento = int(departamento_id)
            empleados_qs = empleados_qs.filter(departamento_id=selected_departamento)
        except ValueError:
            # Manejar el caso donde departamento_id no es un entero válido
            pass

    # --- Filtro por Palabras Clave ---
    keyword = request.GET.get('keyword', '').strip() # .strip() para limpiar espacios en blanco
    if keyword:
        # CORRECCIÓN CLAVE: Nombres de relación y acceso al campo 'nombre' de Titulacion
        # Asumo que Empleado tiene related_name='participaciones' y related_name='titulaciones'
        # Si no, deberías usar 'participacion_set' y 'titulacionempleado_set'
        # Y para titulaciones, necesitas ir a través del modelo intermedio 'TitulacionEmpleado'
        # hasta la Titulacion real para buscar por su nombre.
        empleados_qs = empleados_qs.filter(
            Q(first_name__icontains=keyword) |
            Q(last_name__icontains=keyword) |
            Q(email__icontains=keyword) |
            Q(participaciones__curso__nombre__icontains=keyword) | # Busca en nombre del curso de Participacion
            Q(titulaciones__nombre__icontains=keyword) # <-- ¡CORREGIDO AQUÍ!
        ).distinct() # Usa distinct() para evitar empleados duplicados si tienen múltiples coincidencias # Usa distinct() para evitar empleados duplicados si tienen múltiples coincidencias

    # --- Ordenación de Columnas ---
    # Los valores de 'sort_by' deben coincidir con las 'field_name' de la plantilla
    sort_by = request.GET.get('sort_by', 'first_name') # Valor por defecto 'first_name' si no se especifica
    direction = request.GET.get('direction', 'asc') # Valor por defecto 'asc'

    # Mapeo de los nombres de campo seguros para la ordenación
    allowed_sort_fields = {
        'username': 'username',
        'first_name': 'first_name',         # Coincide con el 'field_name' del template para 'Nombre Completo'
        'departamento__nombre': 'departamento__nombre', # Coincide con el 'field_name' del template para 'Departamento'
    }

    # Obtiene el nombre del campo real en la base de datos para ordenar
    sort_field = allowed_sort_fields.get(sort_by, 'first_name') # Si sort_by no es válido, usa 'first_name'

    if direction == 'desc':
        sort_field = '-' + sort_field
    
    empleados_qs = empleados_qs.order_by(sort_field)

    # Anotar el número de formaciones y titulaciones para el resumen visual
    # Las anotaciones se aplican *después* de los filtros para reflejar el conjunto filtrado
    empleados_qs = empleados_qs.annotate(
        # Asegúrate que 'participaciones' y 'titulaciones' son los related_name correctos
        # de los ForeignKey en Participacion y TitulacionEmpleado hacia Empleado.
        # Si no, usa 'participacion_set' y 'titulacionempleado_set'
        num_participaciones=Count('participaciones', distinct=True),
        num_titulaciones=Count('titulaciones', distinct=True)
    ).select_related('departamento') # Para evitar consultas N+1 al acceder a empleado.departamento.nombre

    # Obtiene todos los departamentos para el filtro de la plantilla
    departamentos = Departamento.objects.all().order_by('nombre')

    # DEFINE Y PASA tabla_columnas AL CONTEXTO (¡Crucial para que tu plantilla funcione!)
    tabla_columnas = {
        'Usuario': 'username',
        'Nombre Completo': 'first_name',
        'Departamento': 'departamento__nombre'
    }

    context = {
        'empleados': empleados_qs,
        'departamentos': departamentos,
        'selected_departamento': selected_departamento, # Usa la variable casteada
        'sort_by': sort_by,
        'direction': direction,
        'keyword': keyword, # Pasa la palabra clave al template para que se mantenga en el input
        'tabla_columnas': tabla_columnas, # ¡IMPORTANTE! Pasa esto a la plantilla
    }
    return render(request, 'formacion/empleados_con_formacion.html', context)

@login_required
@user_passes_test(lambda u: es_rrhh(u) or es_admin(u) or es_formacion_o_direccion(u), login_url='formacion:dashboard')
def empleado_formacion_detalle(request, empleado_id):
    # Obtener el empleado o devolver 404 si no existe
    empleado = get_object_or_404(Empleado, id=empleado_id)

    # Obtener todas las participaciones del empleado
    participaciones = Participacion.objects.filter(empleado=empleado).select_related('curso').order_by('-created_at')

    # Obtener todas las titulaciones del empleado
    titulaciones = Titulacion.objects.filter(empleado=empleado).select_related('curso_relacionado').order_by('-fecha_obtencion')

    context = {
        'empleado': empleado,
        'participaciones': participaciones,
        'titulaciones': titulaciones,
    }
    return render(request, 'formacion/empleado_formacion_detalle.html', context)


class EmpleadoListView(ListView):
    model = Empleado
    template_name = 'formacion/empleado_list.html'
    context_object_name = 'empleados'
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().order_by('last_name', 'first_name')

@user_passes_test(solo_superusuarios, login_url='formacion:dashboard')
def alta_usuario_empleado(request):
    if request.method == 'POST':
        form = EmpleadoCreationForm(request.POST)
        if form.is_valid():
            empleado = form.save()
            messages.success(request, f"Empleado '{empleado.username}' creado exitosamente.")
            return redirect('admin:formacion_empleado_changelist')
    else:
        form = EmpleadoCreationForm()
    return render(request, 'formacion/alta_usuario_empleado.html', {'form': form})

@login_required
def editar_perfil_empleado(request):
    """
    Permite al empleado visualizar su información personal.
    Esta vista NO permite la edición de los datos personales.
    """
    empleado_instance = request.user # El usuario logeado es la instancia del empleado

    context = {
        'empleado': empleado_instance,
    }
    return render(request, 'formacion/perfil_empleado_visualizar.html', context) # Cambia el nombre de la plantilla

# Vistas para la gestión de Titulaciones/Certificaciones (Auto-Servicio)
# --------------------------------------------------------------------------

class MisTitulacionesListView(LoginRequiredMixin, ListView):
    """
    Lista todas las titulaciones/certificaciones del empleado logeado.
    """
    model = Titulacion
    template_name = 'formacion/mis_titulaciones_list.html'
    context_object_name = 'titulaciones'

    def get_queryset(self):
        # Asegura que solo se muestren las titulaciones del usuario logeado
        return Titulacion.objects.filter(empleado=self.request.user).order_by('-fecha_obtencion')

mis_titulaciones_list = MisTitulacionesListView.as_view()


class MiTitulacionCreateView(LoginRequiredMixin, CreateView):
    """
    Permite al empleado añadir una nueva titulación/certificación.
    """
    model = Titulacion
    form_class = TitulacionForm
    template_name = 'formacion/mi_titulacion_form.html'
    success_url = reverse_lazy('formacion:mis_titulaciones_list')

    def form_valid(self, form):
        # Asigna el empleado automáticamente al usuario logeado antes de guardar
        form.instance.empleado = self.request.user
        # Calcular y asignar el nivel_meces basado en el tipo_titulacion
        tipo_titulacion_seleccionado = form.cleaned_data.get('tipo_titulacion')
        # Asigna el Nivel MECES usando el mapa de constantes.
        # Si el tipo de titulación no está en el mapa, asigna un valor por defecto.
        form.instance.nivel_meces = TIPO_TITULACION_MECES_MAP.get(tipo_titulacion_seleccionado, 'otro_meces') # 'otro_meces' es un ejemplo, usa el valor por defecto que te convenga
        
        messages.success(self.request, '¡Tu nueva titulación ha sido añadida correctamente!')
        return super().form_valid(form)

mi_titulacion_create = MiTitulacionCreateView.as_view()


class MiTitulacionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Permite al empleado editar una titulación/certificación existente.
    """
    model = Titulacion
    form_class = TitulacionForm
    template_name = 'formacion/mi_titulacion_form.html'
    success_url = reverse_lazy('formacion:mis_titulaciones_list')
    context_object_name = 'titulacion' # Nombre del objeto en la plantilla

    def test_func(self):
        # Asegura que el usuario solo pueda editar sus propias titulaciones
        titulacion = self.get_object()
        return titulacion.empleado == self.request.user and titulacion.estado in ['pendiente', 'rechazado']

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para editar esta titulación.")
        return redirect('formacion:mis_titulaciones_list')

    def form_valid(self, form):
        # Captura el estado original antes de guardar para aplicar la lógica condicional
        original_estado = self.get_object().estado
        # Calcular y asignar el nivel_meces basado en el tipo_titulacion
        # Esto es importante para el caso de que el tipo de titulación se cambie durante la edición.
        tipo_titulacion_seleccionado = form.cleaned_data.get('tipo_titulacion')
        form.instance.nivel_meces = TIPO_TITULACION_MECES_MAP.get(tipo_titulacion_seleccionado, 'otro_meces')
        
        # Si la titulación estaba en estado 'rechazado' y se está editando,
        # su estado vuelve a 'pendiente' y se limpia el motivo de rechazo.
        if original_estado == 'rechazado':
            form.instance.estado = 'pendiente'
            form.instance.motivo_rechazo = None # Limpiar el motivo de rechazo al reenviar
            messages.success(self.request, '¡La titulación rechazada ha sido actualizada y enviada nuevamente para validación!')
        else:
            # Para el caso 'pendiente' o cualquier otro estado permitido, solo se actualiza
            messages.success(self.request, '¡La titulación ha sido actualizada correctamente!')
        
        return super().form_valid(form) # Guardar la instancia con el nivel_meces y el estado/motivo actualizado


mi_titulacion_update = MiTitulacionUpdateView.as_view()


class MiTitulacionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Permite al empleado eliminar una titulación/certificación.
    """
    model = Titulacion
    template_name = 'formacion/mi_titulacion_confirm_delete.html'
    success_url = reverse_lazy('formacion:mis_titulaciones_list')
    context_object_name = 'titulacion' # Nombre del objeto en la plantilla

    def test_func(self):
        # Asegura que el usuario solo pueda eliminar sus propias titulaciones
        titulacion = self.get_object()
        return titulacion.empleado == self.request.user and titulacion.estado == 'pendiente'

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para eliminar esta titulación.")
        return redirect('formacion:mis_titulaciones_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, '¡La titulación ha sido eliminada correctamente!')
        return super().delete(request, *args, **kwargs)

mi_titulacion_delete = MiTitulacionDeleteView.as_view()

# --- Notificaciones y Dashboard ---

@login_required
def ver_notificaciones(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')
    notificaciones.filter(leida=False).update(leida=True)
    return render(request, 'formacion/notificaciones.html', {'notificaciones': notificaciones})

@login_required
def dashboard(request):
    grupos_usuario = request.user.groups.values_list('name', flat=True)
    num_no_leidas = Notificacion.objects.filter(usuario=request.user, leida=False).count()

    is_coordinador_val = es_coordinador(request.user)
   
    context = {
        'es_empleado': es_empleado(request.user),
        'es_coordinador': es_coordinador(request.user),
        'es_formacion': es_formacion(request.user),
        'es_rrhh': es_rrhh(request.user),
        'es_direccion': es_direccion(request.user),
        'es_admin': es_admin(request.user),
        'num_notificaciones': num_no_leidas
    }
    return render(request, 'formacion/dashboard.html', context)


# --- Gestión de Cursos ---

@login_required
@user_passes_test(es_formacion_o_direccion_o_rrhh, login_url='formacion:dashboard')
def estado_cursos(request):
    grupos_permitidos = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]
    if not request.user.groups.filter(name__in=grupos_permitidos).exists() and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder a esta página.")
        return redirect('formacion:dashboard')

    # --- Lógica de filtrado de cursos terminados ---
    show_finished_courses = request.GET.get('show_finished', 'false').lower() == 'true'

    cursos_queryset = Curso.objects.all()

    # Si NO se pide mostrar los terminados, filtramos los que hayan terminado antes de hoy
    if not show_finished_courses:
        # Un curso se considera "no terminado" si su fecha_fin es nula O si su fecha_fin es hoy o en el futuro.
        cursos_queryset = cursos_queryset.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
        )

    cursos = cursos_queryset.order_by('fecha_inicio', 'nombre')
    # --- Fin Lógica de filtrado ---

    datos_cursos_con_estado = []
    for curso in cursos:
        aceptados = Participacion.objects.filter(curso=curso, estado='aceptado').count()
        asistidos = Participacion.objects.filter(curso=curso, estado='asistido').count()
        completados = Participacion.objects.filter(curso=curso, estado='completado').count()
        cancelados = Participacion.objects.filter(curso=curso, estado='cancelado').count()
        rechazados = Participacion.objects.filter(curso=curso, estado='rechazado').count()

        pendientes_validar = Preseleccion.objects.filter(curso=curso).count()

        num_postulados = aceptados + rechazados + pendientes_validar

        # Consolidación de datos de participación para la nueva columna
        participacion_resumen_parts = []
        if aceptados > 0:
            participacion_resumen_parts.append(f"Acept: {aceptados}")
        if asistidos > 0:
            participacion_resumen_parts.append(f"Asist: {asistidos}")
        if completados > 0:
            participacion_resumen_parts.append(f"Comp: {completados}")
        if pendientes_validar > 0:
            participacion_resumen_parts.append(f"Pend: {pendientes_validar}")
        
        # Si no hay ninguna participación, o las demás son 0, podemos indicar "No hay participaciones activas"
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
            # 'num_postulados': num_postulados, # Este ya no se muestra directamente en tabla
            # 'num_aceptados': aceptados,      # Estos ya no se muestran directamente en tabla
            # 'num_asistidos': asistidos,
            # 'num_completados': completados,
            # 'num_cancelados': cancelados,
            # 'num_rechazados': rechazados,
            'num_pendientes_validar': pendientes_validar, # Se mantiene para la lógica del botón de acciones
            'participacion_resumen': participacion_resumen, # La nueva columna resumida
        }
        datos_cursos_con_estado.append(curso_data)

    context = {
        'datos_cursos': datos_cursos_con_estado,
        'show_finished_courses': show_finished_courses, # Pasar el estado del checkbox al template
    }
    return render(request, 'formacion/estado_cursos.html', context)


@login_required
@user_passes_test(es_formacion_o_direccion_o_rrhh, login_url='formacion:dashboard')
def crear_editar_curso(request, curso_id=None):
    curso = None
    if curso_id:
        curso = get_object_or_404(Curso, id=curso_id)

    if request.method == 'POST':
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            form.save()
            # Determine success message based on whether it was a creation or an edit
            if curso_id:
                messages.success(request, f"El curso '{curso.nombre}' ha sido actualizado correctamente.")
            else:
                messages.success(request, f"El curso '{form.instance.nombre}' ha sido creado correctamente.")
            
            # Redirect to the HR course management list
            return redirect('formacion:gestion_cursos') 
        else:
            messages.error(request, "Error al guardar el curso. Revisa los datos.")
            # If form is invalid, re-render the form with errors
            return render(request, 'formacion/crear_editar_curso.html', {'form': form, 'curso': curso})
    else:
        form = CursoForm(instance=curso)

    return render(request, 'formacion/crear_editar_curso.html', {'form': form, 'curso': curso})


@login_required
@user_passes_test(es_formacion_o_direccion, login_url='formacion:dashboard')
@require_POST
def eliminar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    curso.delete()
    messages.success(request, f"Curso '{curso.nombre}' eliminado correctamente.")
    return redirect('formacion:proximos_cursos')


# --- Vista para Crear Solicitudes (para Coordinadores) ---
class SolicitudCursoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = SolicitudCurso
    form_class = SolicitudCursoForm
    template_name = 'formacion/solicitud_curso_form.html'
    success_url = reverse_lazy('formacion:dashboard') # <-- ¡CORREGIDO AQUÍ!

    def test_func(self):
        # Solo permite a usuarios que sean coordinadores (o roles con ese permiso) acceder a esto
        return es_coordinador(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para solicitar cursos.")
        return redirect('formacion:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['solicitante'] = self.request.user # Pasa el usuario solicitante al formulario
        return kwargs

    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        
        # Asumiendo que el usuario tiene un objeto Empleado relacionado con un departamento
        # Ajusta esta lógica a cómo tu modelo de Usuario se relaciona con el departamento
        if hasattr(self.request.user, 'empleado') and self.request.user.empleado.departamento:
            form.instance.departamento_solicitante = self.request.user.empleado.departamento
        else:
            # Si el departamento no se puede determinar, se asigna None (si el campo es null=True)
            form.add_error(None, "No se pudo determinar el departamento del solicitante.")
            return self.form_invalid(form) # Si el departamento es obligatorio, se devuelve form_invalid

        response = super().form_valid(form) 
        
        # Enviar notificación después de guardar la solicitud (crea Notificacion en BD)
        # La llamada a este método debe estar dentro del bloque try-except
        # si queremos manejar errores de transacción aquí.
        try:
            self.enviar_notificacion_solicitud_curso(form.instance)
        except TransactionManagementError as e:
            messages.error(self.request, f"Error en la transacción de notificaciones. Por favor, inténtalo de nuevo. ({e})")
            # Podrías querer hacer algo más aquí, como registrar el error
        except Exception as e:
            messages.error(self.request, f"Ocurrió un error inesperado al enviar notificaciones. ({e})")
        
        messages.success(self.request, '¡Tu solicitud de curso ha sido enviada correctamente y está pendiente de revisión!')
        return response

    def enviar_notificacion_solicitud_curso(self, solicitud_curso):
        """
        Envía notificaciones a los usuarios de RRHH, Formación y Dirección
        cuando se crea una nueva solicitud de curso. Estas notificaciones se almacenan en la BD.
        """
        mensaje = (
            f'Nueva solicitud de curso de "{solicitud_curso.solicitante.get_full_name()}" '
            f'para el curso: "{solicitud_curso.titulo_curso_solicitado}". '
            f'Pendiente de revisión.'
        )
        tipo_notificacion = 'info' # O 'new_request' si tienes un tipo específico

        grupos_a_notificar = [settings.GRUPO_FORMACION, settings.GRUPO_RRHH, settings.GRUPO_DIRECCION]
        usuarios_notificados_ids = set() # Para evitar duplicados si un usuario está en varios grupos

        # El bloque transaction.atomic() debe envolver TODAS las operaciones de BD
        # relacionadas con la transacción, incluyendo las consultas de grupos y empleados.
        with transaction.atomic():
            for group_name in grupos_a_notificar:
                try:
                    group = Group.objects.get(name=group_name)
                    # Filtra usuarios que pertenecen al grupo y no son el solicitante original
                    # y que no han sido notificados ya
                    usuarios_del_grupo = Empleado.objects.filter(
                        groups=group
                    ).exclude(
                        id=solicitud_curso.solicitante.id
                    ).exclude(
                        id__in=usuarios_notificados_ids
                    )
                    
                    for usuario_grupo in usuarios_del_grupo:
                        Notificacion.objects.create(
                            usuario=usuario_grupo,
                            mensaje=mensaje,
                            tipo=tipo_notificacion,
                            url=reverse_lazy('formacion:solicitudes_curso_pendientes_rrhh')
                        )
                        usuarios_notificados_ids.add(usuario_grupo.id)

                except Group.DoesNotExist:
                    print(f"Advertencia: El grupo '{group_name}' no existe. No se enviaron notificaciones a este grupo.")
                    # Continúa con el siguiente grupo, no levanta TransactionManagementError
                    continue # <--- ¡IMPORTANTE! Continúa con el siguiente elemento del bucle
                except Exception as e:
                    print(f"Error al enviar notificación al grupo '{group_name}': {e}")
                    # Si ocurre otro error, también continúa para no bloquear la transacción
                    continue # <--- ¡IMPORTANTE! Continúa con el siguiente elemento del bucle
            
            # Notificar a superusuarios que no estén ya en los grupos anteriores
            super_usuarios = Empleado.objects.filter(is_superuser=True).exclude(
                id__in=usuarios_notificados_ids
            ).exclude(
                id=solicitud_curso.solicitante.id
            ).distinct()

            for admin_user in super_usuarios:
                Notificacion.objects.create(
                    usuario=admin_user,
                    mensaje=mensaje,
                    tipo=tipo_notificacion,
                    url=reverse_lazy('formacion:solicitudes_curso_pendientes_rrhh')
                )
                usuarios_notificados_ids.add(admin_user.id)

# Convierte la clase en una vista que puedas usar en urls.py
solicitud_curso_create = SolicitudCursoCreateView.as_view()


# --- Vistas de Gestión de Solicitudes (para RRHH/Formación/Dirección) ---

class SolicitudesCursoGestionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Lista las solicitudes de cursos activas (pendientes, aprobadas, en proceso)
    para que RRHH, Formación y Dirección las gestionen.
    """
    model = SolicitudCurso
    template_name = 'formacion/solicitudes_curso_gestion_list.html'
    context_object_name = 'solicitudes'
    paginate_by = 15 # Opcional: para paginar los resultados si hay muchas solicitudes

    def test_func(self):
        # Solo permite el acceso a usuarios que sean de RRHH, Formación o Dirección
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para ver las solicitudes de cursos.")
        return redirect('formacion:dashboard')

    def get_queryset(self):
        # Filtra para mostrar solo las solicitudes en estado 'pendiente', 'aprobada' o 'en_proceso'
        return SolicitudCurso.objects.filter(
            estado__in=['pendiente', 'aprobada', 'en_proceso']
        ).order_by('-fecha_solicitud')

# Convierte la clase en una vista que puedas usar en urls.py
solicitudes_curso_gestion_list = SolicitudesCursoGestionListView.as_view()


class SolicitudCursoDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Muestra el detalle completo de una solicitud de curso.
    """
    model = SolicitudCurso
    template_name = 'formacion/solicitud_curso_detail.html'
    context_object_name = 'solicitud'

    def test_func(self):
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para ver el detalle de esta solicitud.")
        return redirect('formacion:dashboard')

# Convierte la clase en una vista que puedas usar en urls.py
solicitud_curso_detail = SolicitudCursoDetailView.as_view()


# --- Vistas de Acción sobre Solicitudes (para RRHH/Formación/Dirección) ---

# Formulario simple para el motivo de rechazo (usado en RechazarSolicitudView)
class MotivoRechazoForm(forms.Form):
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Motivo del Rechazo",
        help_text="Por favor, explica por qué se ha rechazado esta solicitud."
    )

class SolicitudCursoAccionBase(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Clase base para las acciones de Aceptar, Rechazar y Procesar solicitudes.
    Maneja permisos y redirecciones comunes.
    """
    model = SolicitudCurso
    fields = [] # No necesitamos campos del formulario en la base, solo actualizamos el estado
    success_url = reverse_lazy('formacion:solicitudes_curso_gestion') # Redirige a la lista de gestión

    def test_func(self):
        return es_formacion_o_direccion(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "No tienes permiso para realizar esta acción.")
        return redirect('formacion:dashboard')

    def form_valid(self, form):
        solicitud = form.instance
        self.perform_action(solicitud) # Llama al método específico de la subclase
        messages.success(self.request, self.get_success_message(solicitud))
        return super().form_valid(form)
    
    # Este método es necesario para UpdateView, aunque no se use directamente para renderizar en POST
    def get_template_names(self):
        return ['formacion/solicitud_curso_detail.html'] 

    def perform_action(self, solicitud):
        """
        Método a ser implementado por las subclases para definir la lógica de la acción.
        """
        raise NotImplementedError("Subclases deben implementar perform_action.")

    def get_success_message(self, solicitud):
        """
        Método a ser implementado por las subclases para definir el mensaje de éxito.
        """
        return "Acción realizada con éxito."
    '''
    def enviar_notificacion_a_coordinador(self, solicitud, asunto, mensaje_html_template, contexto_extra=None):
        """
        Envía una notificación por email al coordinador solicitante.
        """
        if not solicitud.solicitante.email:
            print(f"El solicitante {solicitud.solicitante.username} no tiene email para notificación.")
            return

        context = {
            'solicitud': solicitud,
            'dominio': self.request.get_host(),
            'solicitud_url': self.request.build_absolute_uri(
                reverse_lazy('formacion:dashboard') # Enlace al dashboard del coordinador
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
            print(f"Notificación de solicitud '{asunto}' enviada a {solicitud.solicitante.email}")
        except Exception as e:
            print(f"Error al enviar la notificación de solicitud: {e}")
    '''

class AceptarSolicitudView(SolicitudCursoAccionBase):
    """
    Cambia el estado de una solicitud a 'aprobada' y notifica al coordinador.
    """
    def perform_action(self, solicitud):
        solicitud.estado = 'aprobada'
        solicitud.save()
        '''
        self.enviar_notificacion_a_coordinador(
            solicitud,
            f"Tu Solicitud de Curso '{solicitud.titulo_curso_solicitado}' ha sido Aprobada",
            'formacion/email/solicitud_aprobada.html'
        )
        '''

    def get_success_message(self, solicitud):
        return f"Solicitud '{solicitud.titulo_curso_solicitado}' aceptada y en planificación."

# Convierte la clase en una vista que puedas usar en urls.py
aceptar_solicitud = AceptarSolicitudView.as_view()


class RechazarSolicitudView(SolicitudCursoAccionBase):
    """
    Cambia el estado de una solicitud a 'rechazada', guarda el motivo y notifica al coordinador.
    Requiere un formulario para el motivo.
    """
    # Para el método GET, renderizamos un formulario para obtener el motivo de rechazo
    def get(self, request, *args, **kwargs):
        solicitud = self.get_object()
        form = MotivoRechazoForm()
        return render(request, 'formacion/solicitud_rechazar_confirm.html', {'solicitud': solicitud, 'form': form})

    # Para el método POST, procesamos el formulario y actualizamos la solicitud
    def post(self, request, *args, **kwargs):
        self.object = self.get_object() # Necesario para UpdateView
        form = MotivoRechazoForm(request.POST)
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            self.object.estado = 'rechazada'
            self.object.motivo_rechazo = motivo # Guardamos el motivo de rechazo
            self.object.save()
            '''
            self.enviar_notificacion_a_coordinador(
                self.object,
                f"Tu Solicitud de Curso '{self.object.titulo_curso_solicitado}' ha sido Rechazada",
                'formacion/email/solicitud_rechazada.html',
                {'motivo_rechazo': motivo} # Pasamos el motivo al contexto del email
            )
            '''
            messages.success(request, f"Solicitud '{self.object.titulo_curso_solicitado}' rechazada y eliminada de la lista activa.")
            return redirect(self.get_success_url())
        else:
            # Si el formulario no es válido, volvemos a renderizar la página de confirmación con errores
            return render(request, 'formacion/solicitud_rechazar_confirm.html', {'solicitud': self.object, 'form': form})

# Convierte la clase en una vista que puedas usar en urls.py
rechazar_solicitud = RechazarSolicitudView.as_view()


class ProcesarSolicitudView(SolicitudCursoAccionBase):
    """
    Cambia el estado de una solicitud a 'completada' (asumiendo que se convierte en curso formal).
    No envía notificación al coordinador.
    """
    def perform_action(self, solicitud):
        solicitud.estado = 'completada' # Cambiamos a 'completada' según tu modelo
        # Opcional: Aquí podrías añadir lógica para crear una instancia de tu modelo Curso
        # Por ejemplo:
        # from tu_app_de_cursos.models import Curso # Asegúrate de importar tu modelo Curso
        # Curso.objects.create(
        #     nombre=solicitud.titulo_curso_solicitado,
        #     descripcion=solicitud.objetivo_curso,
        #     # ... mapear otros campos de SolicitudCurso a Curso ...
        #     # Puedes usar solicitud.comentarios_procesamiento si quieres guardar notas internas
        # )
        solicitud.save()
        # NO se envía notificación al coordinador para esta acción

    def get_success_message(self, solicitud):
        return f"Solicitud '{solicitud.titulo_curso_solicitado}' procesada, asumiendo que se convertirá en curso formal."

# Convierte la clase en una vista que puedas usar en urls.py
procesar_solicitud = ProcesarSolicitudView.as_view()

@login_required
def cursos_obligatorios_lista(request):
    """
    Vista para listar todos los cursos, indicando si son generalmente obligatorios
    o si son obligatorios para puestos de trabajo específicos.
    Ahora permite al empleado solicitar inscripción en estos cursos.
    """
    # 1. Recuperar todos los Cursos y pre-cargar sus requisitos obligatorios
    # Filtrar solo por cursos que son 'es_obligatorio' o están en algún RequisitoPuestoFormacion obligatorio
    cursos = Curso.objects.prefetch_related(
        Prefetch(
            'requisitos_puesto', # related_name en RequisitoPuestoFormacion que apunta a Curso
            queryset=RequisitoPuestoFormacion.objects.filter(tipo_requisito='obligatorio').select_related('puesto').order_by('puesto__nombre'),
            to_attr='puestos_obligatorios_cache' # Almacena los requisitos pre-cargados
        )
    ).order_by('nombre')

    # 2. Pre-cargar las participaciones del usuario actual para una comprobación eficiente
    user_participations_map = {
        p.curso.id: p for p in Participacion.objects.filter(empleado=request.user).select_related('curso')
    }

    cursos_con_obligatoriedad_y_estado = []
    for curso in cursos:
        # Información de obligatoriedad (general o por puesto)
        puestos_obligatorios_nombres = []
        if hasattr(curso, 'puestos_obligatorios_cache'):
            puestos_obligatorios_nombres = [req.puesto.nombre for req in curso.puestos_obligatorios_cache]
        es_obligatorio_general = curso.es_obligatorio

        # Incluimos el curso en la lista si es obligatorio de alguna forma
        if es_obligatorio_general or puestos_obligatorios_nombres:
            # Información de participación del usuario y elegibilidad para solicitar
            estado_usuario = None
            participacion_existente = user_participations_map.get(curso.id)
            if participacion_existente:
                estado_usuario = participacion_existente.get_estado_display() # Obtiene el texto legible del estado

            puede_solicitar = True
            motivo_no_solicitar = ""

            # Validaciones para determinar si el botón de solicitud debe estar activo
            if participacion_existente:
                puede_solicitar = False
                motivo_no_solicitar = f"Ya estás {estado_usuario.lower()} en este curso."
            elif curso.plazas_totales is not None and curso.plazas_totales > 0 and curso.plazas_disponibles <= 0:
                puede_solicitar = False
                motivo_no_solicitar = "No quedan plazas disponibles."
            elif curso.fecha_fin and curso.fecha_fin < timezone.now().date():
                puede_solicitar = False
                motivo_no_solicitar = "El curso ya ha finalizado."
            
            cursos_con_obligatoriedad_y_estado.append({
                'curso': curso,
                'es_obligatorio_general': es_obligatorio_general,
                'puestos_obligatorios': puestos_obligatorios_nombres,
                'estado_usuario': estado_usuario, # Nuevo: estado del usuario en este curso
                'puede_solicitar': puede_solicitar, # Nuevo: si puede solicitarlo
                'motivo_no_solicitar': motivo_no_solicitar, # Nuevo: motivo si no puede solicitarlo
            })

    context = {
        'cursos_con_obligatoriedad': cursos_con_obligatoriedad_y_estado,
        'has_obligatory_courses': bool(cursos_con_obligatoriedad_y_estado),
    }
    return render(request, 'formacion/cursos_obligatorios_lista.html', context)


# La vista `solicitar_inscripcion_curso` debe seguir presente en tu formacion/views.py
# Asegúrate de que las redirecciones en esta vista apunten a 'formacion:cursos_obligatorios_lista'
@login_required
def solicitar_inscripcion_curso(request, curso_id):
    """
    Permite a un empleado solicitar la inscripción en un curso existente.
    Crea una Participacion con estado 'pendiente'.
    """
    if request.method == 'POST':
        curso = get_object_or_404(Curso, pk=curso_id)

        # Validaciones antes de crear la participación
        if Participacion.objects.filter(empleado=request.user, curso=curso).exists():
            messages.warning(request, f'Ya tienes una solicitud o participación existente para "{curso.nombre}".')
            return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal
        
        if curso.plazas_totales is not None and curso.plazas_totales > 0 and curso.plazas_disponibles <= 0:
            messages.error(request, f'Lo sentimos, el curso "{curso.nombre}" no tiene plazas disponibles.')
            return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal
        
        if curso.fecha_fin and curso.fecha_fin < timezone.now().date():
            messages.error(request, f'Lo sentimos, el curso "{curso.nombre}" ya ha finalizado y no se puede solicitar.')
            return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal

        try:
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
            
            return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal

        except Exception as e:
            messages.error(request, f'Ocurrió un error al procesar tu solicitud: {e}')
            return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal
    
    messages.error(request, 'Método de solicitud no válido.')
    return redirect('formacion:cursos_obligatorios_lista') # Redirige a la vista principal

@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def gestionar_solicitudes_obligatorias_rrhh(request):
    """
    Vista para que RRHH gestione las solicitudes de inscripción a cursos obligatorios (participaciones pendientes).
    """
    solicitudes_pendientes = Participacion.objects.filter(estado='pendiente').order_by('created_at')

    context = {
        'solicitudes_pendientes': solicitudes_pendientes,
        'has_pendientes': bool(solicitudes_pendientes),
        'page_title': 'Gestión de Solicitudes de Cursos Obligatorios',
        'page_description': 'Revisa y gestiona las solicitudes de inscripción de los empleados a cursos marcados como obligatorios.',
        'form': AprobarParticipacionForm(),
    }
    return render(request, 'formacion/gestionar_solicitudes_obligatorias_rrhh.html', context)


@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def aprobar_solicitud_obligatoria(request, participacion_id):
    """
    RRHH aprueba una solicitud de inscripción a curso obligatorio (cambia estado de Participacion a 'confirmada').
    Ahora requiere una fecha de inicio real y crea una notificación detallada.
    """
    participacion = get_object_or_404(Participacion, pk=participacion_id)

    if request.method == 'POST':
        form = AprobarParticipacionForm(request.POST)
        if form.is_valid():
            if participacion.estado == 'pendiente':
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
            else:
                messages.warning(request, 'Esta solicitud ya no está en estado pendiente.')
            return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    # Si el error es sobre un campo, lo indicamos
                    if field == '__all__': # Errores no asociados a un campo específico
                        error_messages.append(f"Error general: {error}")
                    else:
                        # Django a veces cambia el nombre del campo a su 'label' si lo tienes definido.
                        # Para depurar, es útil ver el nombre del campo real.
                        field_name = form.fields[field].label if field in form.fields and form.fields[field].label else field
                        error_messages.append(f"Error en '{field_name}': {error}")

            # Unir todos los errores en un solo mensaje o mostrarlos individualmente
            if error_messages:
                messages.error(request, " ".join(error_messages))
            else:
                messages.error(request, 'Error al aprobar: La fecha de inicio no es válida. Por favor, asegúrate de introducir una fecha válida.')
            return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')

    messages.error(request, 'Método de solicitud no válido.')
    return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')


@login_required
@user_passes_test(es_rrhh, login_url='/formacion/login/')
def rechazar_solicitud_obligatoria(request, participacion_id):
    """
    RRHH rechaza una solicitud de inscripción a curso obligatorio (cambia estado de Participacion a 'rechazada').
    """
    participacion = get_object_or_404(Participacion, pk=participacion_id)
    if request.method == 'POST':
        if participacion.estado == 'pendiente':
            participacion.estado = 'rechazada'
            participacion.fecha_confirmacion = timezone.now().date() # Puedes usar fecha_confirmacion o añadir fecha_rechazo
            participacion.save()
            messages.warning(request, f'La solicitud de {participacion.empleado.first_name} para "{participacion.curso.nombre}" ha sido RECHAZADA.')
            # Aquí podrías añadir lógica para enviar una notificación al empleado
        else:
            messages.info(request, 'Esta solicitud ya no está en estado pendiente.')
        return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')
    messages.error(request, 'Método de solicitud no válido.')
    return redirect('formacion:gestionar_solicitudes_obligatorias_rrhh')


@login_required
@user_passes_test(es_rrhh)
def marcar_asistido(request, participacion_id):
    participacion = get_object_or_404(Participacion, pk=participacion_id)

    if request.method == 'POST':
        # Solo permitir marcar como asistido si el estado actual lo permite (ej. confirmada, aceptado)
        if participacion.estado in ['confirmada', 'aceptado']:
            participacion.estado = 'asistido'
            participacion.save()

            Notificacion.objects.create(
                usuario=participacion.empleado,
                mensaje=f'Tu asistencia para el curso "{participacion.curso.nombre}" ha sido registrada.',
                tipo='info'
            )
            messages.success(request, f'Participación de {participacion.empleado.get_full_name()} en "{participacion.curso.nombre}" marcada como ASISTIDO.')
        else:
            messages.warning(request, f'No se puede marcar como asistido la participación de {participacion.empleado.get_full_name()} en su estado actual ({participacion.get_estado_display()}).')
    else:
        messages.error(request, 'Método de solicitud no válido.')

    # Redirigir de vuelta a la lista de participantes del curso o a otra página de gestión
    return redirect('formacion:listar_participantes_curso', curso_id=participacion.curso.id)

@login_required
@user_passes_test(es_rrhh)
def marcar_completado(request, participacion_id):
    participacion = get_object_or_404(Participacion, pk=participacion_id)

    if request.method == 'POST':
        form = MarcarCompletadoForm(request.POST, instance=participacion)
        if form.is_valid():
            if participacion.estado in ['asistido', 'confirmada', 'aceptado']:
                with transaction.atomic(): # Envuelve la lógica en una transacción atómica
                    participacion.estado = 'completado'
                    form.save() # Guarda los datos del formulario directamente en la instancia
                    
                    # --- Lógica para la notificación interna ---
                    # Construir la URL de la encuesta usando reverse
                    url_encuesta = reverse('formacion:encuesta_satisfaccion', args=[participacion.id])
                    
                    Notificacion.objects.create(
                        usuario=participacion.empleado,
                        mensaje=f'El curso "{participacion.curso.nombre}" ha sido marcado como COMPLETADO. ¡Felicidades!',
                        tipo='success', # Mantén el tipo que ya tenías
                        url=url_encuesta, # <--- ¡AHORA AÑADIMOS LA URL AQUÍ!
                        leida=False # Asegúrate de que se marque como no leída
                    )
                    # Opcional: print de depuración para confirmar en la consola del servidor
                    print(f"DEBUG: Notificación de completado por RRHH creada para {participacion.empleado.username} con URL: {url_encuesta}")
                    # --- Fin Lógica para la notificación interna ---

                    messages.success(request, f'Participación de {participacion.empleado.get_full_name()} en "{participacion.curso.nombre}" marcada como COMPLETADO.')
            else:
                messages.warning(request, f'No se puede marcar como completado la participación de {participacion.empleado.get_full_name()} en su estado actual ({participacion.get_estado_display()}).')
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    error_messages.append(f"Error en '{field_label}': {error}")
            messages.error(request, f'Errores al marcar como completado: {" ".join(error_messages)}')
    else:
        messages.error(request, 'Método de solicitud no válido.')
    
    # Después de procesar la solicitud, siempre redirigimos
    return redirect('formacion:listar_participantes_curso', curso_id=participacion.curso.id)

@login_required
@user_passes_test(es_rrhh, login_url='formacion:dashboard') # Asumo que 'formacion:dashboard' es tu URL de redirección
def gestion_cursos_list(request):
    """
    Vista para que RRHH liste todos los cursos para su gestión,
    con opción de filtrar cursos terminados.
    """
    # Lógica de filtrado de cursos terminados
    show_finished_courses = request.GET.get('show_finished', 'false').lower() == 'true'

    cursos_queryset = Curso.objects.all()

    # Si NO se pide mostrar los terminados, filtramos los que hayan terminado antes de hoy
    if not show_finished_courses:
        # Un curso se considera "no terminado" si su fecha_fin es nula O si su fecha_fin es hoy o en el futuro.
        cursos_queryset = cursos_queryset.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
        )

    # Ordena los cursos. Puedes mantener '-created_at' o cambiarlo a '-fecha_inicio'
    cursos = cursos_queryset.order_by('-created_at') # o '-fecha_inicio' para un orden cronológico más útil

    context = {
        'cursos': cursos,
        'is_rrhh': True,
        'show_finished_courses': show_finished_courses, # Pasar el estado del checkbox al template
    }
    return render(request, 'formacion/gestion_cursos_list.html', context)


@login_required
def encuesta_satisfaccion(request, participacion_id):
    participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)

    # Verificar si la encuesta ya ha sido rellenada para esta participación
    if EncuestaSatisfaccion.objects.filter(participacion=participacion).exists():
        messages.info(request, "Ya has completado la encuesta de satisfacción para este curso.")
        return redirect('formacion:mis_cursos') # Redirige a mis cursos o a una página de confirmación

    # Asegurarse de que el curso está completado antes de permitir la encuesta
    if participacion.estado != 'completado':
        messages.error(request, "Solo puedes rellenar la encuesta para cursos marcados como completados.")
        return redirect('formacion:mis_cursos') # O a un detalle de la participación

    if request.method == 'POST':
        form = EncuestaSatisfaccionForm(request.POST)
        if form.is_valid():
            encuesta = form.save(commit=False)
            encuesta.participacion = participacion
            encuesta.empleado = request.user
            encuesta.fecha_encuesta = date.today() # Auto-rellenar la fecha actual
            
            # Auto-rellenar otros datos del curso si los quieres guardar en la encuesta
            # Esto es útil si los detalles del curso cambian en el futuro, la encuesta guarda el "snapshot"
            encuesta.nombre_curso_encuesta = participacion.curso.nombre
            # Si tienes campos para profesor, aula, etc. en tu modelo Curso:
            # encuesta.nombre_profesor_encuesta = participacion.curso.profesor.nombre if participacion.curso.profesor else None

            encuesta.save()
            messages.success(request, "¡Gracias! Tu encuesta de satisfacción ha sido enviada.")
            return redirect('formacion:mis_cursos') # Redirige a mis cursos después de enviar
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = EncuestaSatisfaccionForm()

    # Contexto para la plantilla: se pueden pasar datos del curso para mostrar
    context = {
        'form': form,
        'participacion': participacion,
        'curso': participacion.curso, # Para mostrar detalles del curso en la plantilla
        'fecha_actual': date.today(), # Para mostrar la fecha actual
        # Aquí puedes pasar otros datos del curso para que se muestren en la plantilla
        # como el nombre del profesor, aula, duración, horario, si existen en tu modelo Curso
    }
    return render(request, 'formacion/encuesta_satisfaccion.html', context)


@login_required
def marcar_participacion_completada(request, participacion_id):
    participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)

    if request.method == 'POST':
        # Definimos los estados que NO deben permitir al empleado marcar como "completado"
        estados_no_completables = ['completado', 'cancelado', 'abandonado', 'rechazado']
        
        if participacion.estado not in estados_no_completables:
            # Usamos una transacción atómica para asegurar que el estado se guarda
            # y la notificación se crea, o ninguna de las dos cosas.
            with transaction.atomic():
                participacion.estado = 'completado'
                participacion.save()
                messages.success(request, f"¡Has marcado tu participación en '{participacion.curso.nombre}' como completada!")
                
                # --- Lógica para la notificación interna ---
                notificacion_titulo = "Curso Completado - ¡Tu opinión es importante!"
                notificacion_mensaje = (
                    f"Has marcado '{participacion.curso.nombre}' como completado. "
                    "¡Ayúdanos a mejorar rellenando nuestra encuesta de satisfacción!"
                )
                
                # Construir la URL de la encuesta usando reverse
                # Asumo que tienes una URL configurada con el nombre 'encuesta_satisfaccion'
                # que toma el participacion_id como argumento.
                url_encuesta = reverse('formacion:encuesta_satisfaccion', args=[participacion.id])
                
                # Crear la notificación interna usando tu modelo Notificacion
                Notificacion.objects.create(
                    usuario=request.user,  # El usuario que marcó el curso como completado
                    mensaje=notificacion_mensaje,
                    tipo='info', # O 'success', según el tipo de icono que desees
                    url=url_encuesta, # Asocia la URL a la notificación
                    leida=False # Por defecto, la notificación no ha sido leída
                )
                print(f"DEBUG: Notificación de encuesta creada para {request.user.username} con URL: {url_encuesta}")
                # --- Fin Lógica para la notificación interna ---

            # Redirige a la encuesta de satisfacción
            return redirect('formacion:encuesta_satisfaccion', participacion_id=participacion.id)
        else:
            messages.warning(request, f"La participación en '{participacion.curso.nombre}' ya está en un estado final ({participacion.get_estado_display()}).")
            return redirect('formacion:detalle_participacion', participacion_id=participacion.id)
    else:
        messages.error(request, "Método no permitido para esta acción.")
        return redirect('formacion:mis_cursos')


@login_required
def detalle_participacion(request, participacion_id):
    # Ensure the user can only see their own participation details
    participacion = get_object_or_404(Participacion, id=participacion_id, empleado=request.user)

    # Define the list of excluded states here
    estados_finales_participacion = ['completado', 'cancelado', 'abandonado', 'rechazado']

    context = {
        'participacion': participacion,
        'curso': participacion.curso, # Pass the related course for easy access in template
    }
    return render(request, 'formacion/detalle_participacion.html', context)

