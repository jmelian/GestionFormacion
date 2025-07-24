# formacion/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import custom_logout, EmpleadoListView
from django.views.generic import TemplateView

app_name = 'formacion' 

urlpatterns = [
    # URLs de autenticación
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='formacion/login.html'), name='login'),
    path('logout/', custom_logout, name='logout'),

    # URLs relacionadas con Empleados
    path('empleados/', EmpleadoListView.as_view(), name='empleado_list'), 
    path('alta-usuario-empleado/', views.alta_usuario_empleado, name='alta_usuario_empleado'),
    path('perfil/editar/', views.editar_perfil_empleado, name='editar_perfil_empleado'), # Perfil fuera del admin
    path('empleados-con-formacion/', views.empleados_con_formacion, name='empleados_con_formacion'),
    #path('empleados-con-formacion/', TemplateView.as_view(template_name='formacion/empleados_con_formacion_test.html'), name='empleados_con_formacion'),

    path('empleado/<int:empleado_id>/formacion/', views.empleado_formacion_detalle, name='empleado_formacion_detalle'),


    path('perfil/', views.editar_perfil_empleado, name='perfil_empleado_visualizar'), # hace falta?? verificar

    # URLs para auto-servicio de Titulaciones/Certificaciones
    path('perfil/titulaciones/', views.mis_titulaciones_list, name='mis_titulaciones_list'),
    path('perfil/titulaciones/add/', views.mi_titulacion_create, name='mi_titulacion_create'),
    path('perfil/titulaciones/<int:pk>/edit/', views.mi_titulacion_update, name='mi_titulacion_update'),
    path('perfil/titulaciones/<int:pk>/delete/', views.mi_titulacion_delete, name='mi_titulacion_delete'),
    path('titulaciones-pendientes/', views.titulaciones_pendientes_rrhh, name='titulaciones_pendientes_rrhh'),
    path('titulaciones/<int:titulacion_id>/', views.detalle_titulacion, name='detalle_titulacion'),

    # URLs relacionadas con Cursos
    path('gestion-de-cursos/', views.gestion_cursos_list, name='gestion_cursos_list'),
    path('mis-cursos/', views.mis_cursos, name='mis_cursos'),
    path('proximos-cursos/', views.proximos_cursos, name='proximos_cursos'),
    path('estado-cursos/', views.estado_cursos, name='estado_cursos'),
    path('cursos/crear/', views.crear_editar_curso, name='crear_curso'),
    path('cursos/editar/<int:curso_id>/', views.crear_editar_curso, name='editar_curso'),
    path('cursos/eliminar/<int:curso_id>/', views.eliminar_curso, name='eliminar_curso'),
    path('curso/<int:curso_id>/participantes/', views.listar_participantes_curso, name='listar_participantes_curso'),
    path('solicitar-curso/', views.solicitud_curso_create, name='solicitar_curso'),
    path('participacion/<int:participacion_id>/encuesta/', views.encuesta_satisfaccion, name='encuesta_satisfaccion'),
    path('participacion/<int:participacion_id>/marcar_completada/', views.marcar_participacion_completada, name='marcar_participacion_completada'),
    path('participacion/<int:participacion_id>/', views.detalle_participacion, name='detalle_participacion'),
    # URLs para Solicitudes de Curso (Gestión)
    path('solicitudes-gestion/', views.solicitudes_curso_gestion_list, name='solicitudes_curso_gestion'),
    path('solicitudes-gestion/<int:pk>/detalle/', views.solicitud_curso_detail, name='detalle_solicitud_curso'),
    # Nueva URL para el listado de cursos y su obligatoriedad
    path('cursos_obligatorios/', views.cursos_obligatorios_lista, name='cursos_obligatorios_lista'),
    path('gestion-solicitudes-obligatorias-rrhh/', views.gestionar_solicitudes_obligatorias_rrhh, name='gestionar_solicitudes_obligatorias_rrhh'), # URL actualizada
    path('gestion-solicitudes-obligatorias-rrhh/<int:participacion_id>/aprobar/', views.aprobar_solicitud_obligatoria, name='aprobar_solicitud_obligatoria'), # URL y name actualizados
    path('gestion-solicitudes-obligatorias-rrhh/<int:participacion_id>/rechazar/', views.rechazar_solicitud_obligatoria, name='rechazar_solicitud_obligatoria'), # URL y name actualizados
    path('cursos/<int:curso_id>/solicitar/', views.solicitar_inscripcion_curso, name='solicitar_inscripcion_curso'),
    
    path('participaciones/<int:participacion_id>/marcar-asistido/', views.marcar_asistido, name='marcar_asistido'),
    path('participaciones/<int:participacion_id>/marcar-completado/', views.marcar_completado, name='marcar_completado'),
    
    # URLs para acciones sobre solicitudes
    path('solicitudes-gestion/<int:pk>/aceptar/', views.aceptar_solicitud, name='aceptar_solicitud'),
    path('solicitudes-gestion/<int:pk>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
    path('solicitudes-gestion/<int:pk>/procesar/', views.procesar_solicitud, name='procesar_solicitud'),

    # URLs de gestión y roles
    path('equipo-departamento/', views.equipo_departamento, name='equipo_departamento'),
    path('certificados-pendientes/', views.certificados_pendientes_rrhh, name='certificados_pendientes_rrhh'),
    
    # URLs de Preselección y Participación
    path('preseleccion/', views.preseleccionar_empleado, name='preseleccionar_empleado'),
    path('preselecciones/lista/', views.confirmar_preseleccionados_lista, name='confirmar_preseleccionados_lista'),
    path('preselecciones/gestionar/<int:curso_id>/', views.gestionar_preselecciones_curso, name='gestionar_preselecciones_curso'),
    path('gestionar-preseleccion/<int:preseleccion_id>/', views.gestionar_preseleccion, name='gestionar_preseleccion'),
    path('cancelar-participacion/<int:participacion_id>/', views.cancelar_participacion, name='cancelar_participacion'),
    path('rechazar-participacion/<int:participacion_id>/', views.rechazar_participacion, name='rechazar_participacion'), # Confirmada y añadida

    # URLs de Notificaciones
    path('notificaciones/', views.ver_notificaciones, name='ver_notificaciones'),
]