# formacion/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin # Importar UserAdmin para personalizar Empleado
from django.utils.translation import gettext_lazy as _ # Para traducir los títulos de los fieldsets
from django.utils.html import format_html # Solo si se necesita para enlaces de documentos
from .forms import EmpleadoCreationForm, EmpleadoChangeForm, CursoForm, DepartamentoForm

from .models import (
    Departamento, Area,     
    PuestoDeTrabajo, Empleado,
    Proveedor, Proyecto,
    Curso, Participacion,
    RequisitoPuestoFormacion, Preseleccion,
    Notificacion, Titulacion, SolicitudCurso,
    PreguntaEncuesta, EncuestaSatisfaccion,
    RespuestaEncuesta, DetalleRespuesta
)

# Personalización del modelo Empleado (que ahora es nuestro AUTH_USER_MODEL)
@admin.register(Empleado)
class EmpleadoAdmin(UserAdmin):
    form = EmpleadoChangeForm
    add_form = EmpleadoCreationForm

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'departamento', 'area', 'es_empleado_activo'
    )
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'groups',
        'sexo', 'sede', 'estado', 'es_empleado_activo',
        'departamento', 'area',
    )
    search_fields = (
        'username', 'first_name', 'last_name', 'email', 'dni',
        'departamento__nombre', # Búsqueda directa por el nombre del nuevo departamento
        'area__nombre', # Búsqueda directa por el nombre del área
        'codigo_puesto__nombre'
    )
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = UserAdmin.fieldsets + (
        (_('Información de Empleado'), {
            'fields': (
                'dni', 'departamento', 'area', 'codigo_puesto', 'sexo',
                'sede', 'estado', 'es_empleado_activo', 'puesto'
            ),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        (_('Información Personal'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Información de Empleado'), {
            'fields': (
                'dni', 'departamento', 'area', 'codigo_puesto', 'sexo',
                'sede', 'estado', 'es_empleado_activo', 'puesto'
            ),
        }),
        (_('Permisos'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}),
    )
    

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'coordinador')
    search_fields = ('nombre', 'coordinador__username', 'coordinador__first_name', 'coordinador__last_name')
    fields = ('nombre', 'descripcion', 'coordinador')

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento', 'descripcion')
    list_filter = ('departamento',)
    search_fields = ('nombre', 'descripcion', 'departamento__nombre')
    raw_id_fields = ('departamento',)

@admin.register(PuestoDeTrabajo)
class PuestoDeTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'departamento')
    list_filter = ('departamento',)
    search_fields = ('nombre', 'codigo', 'departamento__nombre')
    raw_id_fields = ('departamento',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'created_at') 
    search_fields = ('nombre', 'email', 'telefono')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'jefe_proyecto', 'estado', 'fecha_inicio', 'fecha_fin_prevista', 'created_at')
    list_filter = ('estado', 'jefe_proyecto', 'fecha_inicio')
    search_fields = ('nombre', 'descripcion', 'jefe_proyecto__first_name', 'jefe_proyecto__last_name')
    date_hierarchy = 'fecha_inicio' # Permite navegar por fechas
    raw_id_fields = ('jefe_proyecto',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    form = CursoForm
    list_display = (
        'nombre', 'tipo', 'resultado_formal', 'proveedor', 'modalidad', 
        'duracion_horas', 'fecha_inicio', 'fecha_fin', 'plazas_disponibles', 'plazas_totales',
        'origen', 'proyecto'
    )
    list_filter = (
        'tipo', 'modalidad', 'origen', 'proveedor', 'proyecto',
        'fecha_inicio', 'fecha_fin', 'externo', 'departamento_solicitante'
    )
    search_fields = ('nombre', 'contenido', 'observaciones', 'departamento_solicitante__nombre')
    date_hierarchy = 'fecha_inicio' # Permite navegar por fechas
    raw_id_fields = ('proveedor', 'proyecto', 'departamento_solicitante')


@admin.register(Participacion)
class ParticipacionAdmin(admin.ModelAdmin):
    list_display = (
        'empleado', 'curso', 'estado', 'validado',
        'fecha_certificado', 'created_at' 
    )
    list_filter = (
        'estado', 'validado', 'curso', 
        'empleado__departamento',
        'empleado__area', 
        'empleado__codigo_puesto__departamento',
        'empleado__codigo_puesto'
    )
    search_fields = (
        'empleado__first_name', 'empleado__last_name', 'empleado__username',
        'curso__nombre', 'nota_final'
    )
    date_hierarchy = 'created_at'
    raw_id_fields = ('empleado', 'curso')

@admin.register(Titulacion)
class TitulacionAdmin(admin.ModelAdmin):
    list_display = (
        'empleado', 
        'nombre', 
        'tipo_titulacion', 
        'nivel_meces',
        'institucion_emisora',
        'fecha_obtencion', 
        'fecha_caducidad', 
        'nivel_idioma',
        'estado',
    )
    list_filter = (
        'tipo_titulacion', 
        'nivel_meces',
        'institucion_emisora',
        'nivel_idioma', 
        'estado',
        'empleado__codigo_puesto__departamento',
    )
    search_fields = (
        'empleado__first_name', 
        'empleado__last_name', 
        'nombre',
        'empleado__departamento__nombre',
        'empleado__area__nombre',
        'institucion_emisora'
    )
    date_hierarchy = 'fecha_obtencion'
    raw_id_fields = ('empleado', 'curso_relacionado')
    fieldsets = (
        (None, {
            'fields': ('empleado', 'nombre', 'tipo_titulacion', 'institucion_emisora', 
                       'fecha_obtencion', 'fecha_caducidad', 'documento_adjunto'),
        }),
        ('Información Adicional', {
            'fields': ('curso_relacionado', 'nivel_idioma', 'nivel_meces'),
            'classes': ('collapse',),
        }),
        ('Estado y Revisión RRHH', {
            'fields': ('estado', 'motivo_rechazo',),
            'classes': ('collapse',), 
        }),
    )


@admin.register(RequisitoPuestoFormacion)
class RequisitoPuestoFormacionAdmin(admin.ModelAdmin):
    list_display = ('puesto', 'curso', 'tipo_requisito')
    list_filter = ('puesto__departamento', 'puesto__nombre', 'curso__tipo', 'tipo_requisito')
    search_fields = ('puesto__nombre', 'curso__nombre', 'observaciones')

@admin.register(Preseleccion)
class PreseleccionAdmin(admin.ModelAdmin):
    list_display = ('empleado', 'curso', 'prioridad', 'creado_por', 'fecha')
    list_filter = (
        'prioridad', 'curso', 'creado_por', 
        'empleado__departamento',
        'empleado__area', 
        'empleado__codigo_puesto__departamento'
    )
    search_fields = ('empleado__first_name', 'empleado__last_name', 'curso__nombre', 'observaciones')
    raw_id_fields = ('empleado', 'curso', 'creado_por')
    date_hierarchy = 'fecha'

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'leida', 'fecha', 'tipo', 'url')
    list_filter = (
        'leida', 'tipo',
        'usuario__codigo_puesto__departamento'
    )
    search_fields = ('usuario__username', 'mensaje', 'usuario__first_name', 'usuario__last_name')
    readonly_fields = ('fecha',)


@admin.register(SolicitudCurso)
class SolicitudCursoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo_curso_solicitado', 'solicitante', 'departamento_solicitante',
        'fecha_solicitud', 'estado', 'caracter_formacion'
    )
    list_filter = ('estado', 'caracter_formacion', 'departamento_solicitante', 'fecha_solicitud')
    search_fields = ('titulo_curso_solicitado', 'solicitante__username', 'solicitante__first_name', 'solicitante__last_name')
    date_hierarchy = 'fecha_solicitud'
    readonly_fields = ('solicitante', 'departamento_solicitante', 'fecha_solicitud')
    fieldsets = (
        (None, {
            'fields': ('solicitante', 'departamento_solicitante', 'fecha_solicitud', 'titulo_curso_solicitado', 'objetivo_curso', 'justificacion_necesidad')
        }),
        ('Detalles de la Formación', {
            'fields': ('numero_participantes_estimado', 'temas_contenidos_clave', 'formato_preferido', 'duracion_estimada', 'fechas_horarios_preferidos', 'caracter_formacion', 'comentarios_adicionales')
        }),
        ('Estado y Revisión', {
            'fields': ('estado', 'motivo_rechazo', 'comentarios_procesamiento'),
            'classes': ('collapse',) # Esto hace que esta sección sea colapsable por defecto
        }),
    )


class PreguntaEncuestaInline(admin.TabularInline):
    model = PreguntaEncuesta
    extra = 1 # Número de formularios vacíos a mostrar
    fields = ['texto_pregunta', 'tipo_pregunta', 'orden'] # Campos a mostrar en el inline


@admin.register(EncuestaSatisfaccion)
class EncuestaSatisfaccionAdmin(admin.ModelAdmin):
    # Campos que se muestran en la lista de objetos en el admin
    list_display = (
        'empleado',
        'participacion_link',
        'fecha_encuesta',
        'opinion_contenido_curso',
        'gusto_general_curso',
        'valoracion_media_curso_profesor_display',
        'valoracion_media_eficacia_display',
    )

    # Campos por los que se puede filtrar la lista
    list_filter = (
        'fecha_encuesta',
        'opinion_contenido_curso',
        'gusto_general_curso',
        'empleado',
        'participacion__curso',
    )

    # Campos por los que se puede buscar texto
    search_fields = (
        'empleado__username',
        'empleado__first_name',
        'empleado__last_name',
        'participacion__curso__nombre',
        'sugerencias_observaciones',
    )
    
    # Campos que solo se pueden leer (no editar) en el formulario de detalle
    readonly_fields = (
        'participacion',
        'empleado',
        'fecha_encuesta',
        'valoracion_media_curso_profesor_display',
        'valoracion_media_eficacia_display',
    )

    # Orden por defecto de la lista
    ordering = ('-fecha_encuesta',)

    # Configuración de los fieldsets para organizar el formulario de detalle/edición
    fieldsets = (
        ('Información Básica de la Encuesta', {
            'fields': ('participacion', 'empleado', 'fecha_encuesta'),
            'description': 'Datos fundamentales de la encuesta y el encuestado.',
        }),
        ('Datos del Curso (Instantánea)', {
            'fields': ('nombre_curso_encuesta', 'nombre_profesor_encuesta'),
            'description': 'Detalles del curso al momento de realizar la encuesta.',
            'classes': ('collapse',), # Opcional: para que esta sección esté plegada por defecto
        }),
        ('Valoración del Profesor / Curso', {
            'fields': (
                'opinion_contenido_curso',
                'conocimientos_profesor',
                'gusto_general_curso',
                'valoracion_media_curso_profesor_display', # Campo calculado
            ),
            'description': 'Opinión sobre el contenido y el instructor.',
        }),
        ('Valoración de la Eficacia de la Formación', {
            'fields': (
                'mejora_conocimientos_carrera',
                'adquisicion_habilidades_puesto',
                'valoracion_media_eficacia_display', # Campo calculado
            ),
            'description': 'Percepción sobre la utilidad y aplicación de la formación.',
        }),
        ('Comentarios Adicionales', {
            'fields': ('sugerencias_observaciones',),
            'description': 'Espacio para sugerencias y observaciones abiertas del empleado.',
        }),
    )

    inlines = [PreguntaEncuestaInline]

    # Métodos para list_display que no son campos directos del modelo
    @admin.display(description='Participación')
    def participacion_link(self, obj):
        from django.utils.html import format_html
        from django.urls import reverse
        try:
            # enlazar a la vista de cambio de la participación en el admin
            url = reverse('admin:%s_%s_change' % (obj.participacion._meta.app_label, obj.participacion._meta.model_name), args=[obj.participacion.id])
            return format_html('<a href="{}">{}</a>', url, obj.participacion)
        except Exception:
            return str(obj.participacion)
    participacion_link.admin_order_field = 'participacion__curso__nombre' # Ordena por el nombre del curso de la participación

    @admin.display(description='Media Curso/Profesor')
    def valoracion_media_curso_profesor_display(self, obj):
        return f"{obj.valoracion_media_curso_profesor:.2f}" if obj.valoracion_media_curso_profesor is not None else 'N/A'
    valoracion_media_curso_profesor_display.admin_order_field = 'opinion_contenido_curso'

    @admin.display(description='Media Eficacia')
    def valoracion_media_eficacia_display(self, obj):
        return f"{obj.valoracion_media_eficacia:.2f}" if obj.valoracion_media_eficacia is not None else 'N/A'
    valoracion_media_eficacia_display.admin_order_field = 'mejora_conocimientos_carrera'


# INLINE para DetalleRespuesta (usado dentro de RespuestaEncuestaAdmin)
class DetalleRespuestaInline(admin.TabularInline):
    model = DetalleRespuesta
    extra = 0 # No mostrar formularios vacíos por defecto
    # Todos los campos son de solo lectura ya que son las respuestas enviadas
    readonly_fields = ('pregunta', 'respuesta_texto', 'respuesta_escala')
    fields = ('pregunta', 'respuesta_texto', 'respuesta_escala')
    can_delete = False 
    verbose_name = "Respuesta Individual"
    verbose_plural = "Respuestas Individuales"

    # Para mostrar la pregunta de forma más amigable en el inline
    @admin.display(description='Pregunta')
    def pregunta_display(self, obj):
        return obj.pregunta.texto_pregunta


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = (
        'participacion_info', 'encuesta_titulo', 'fecha_respuesta', 'completada'
    )
    list_filter = ('encuesta', 'completada', 'fecha_respuesta')
    search_fields = (
        'participacion__empleado__username',
        'participacion__empleado__first_name',
        'participacion__empleado__last_name',
        'participacion__curso__nombre',
        'encuesta__titulo',
    )
    date_hierarchy = 'fecha_respuesta'
    # Los campos de relación son de solo lectura porque se asignan automáticamente
    readonly_fields = ('participacion', 'encuesta', 'fecha_respuesta')
    
    # Añadimos el inline para DetalleRespuesta aquí
    inlines = [DetalleRespuestaInline]

    fieldsets = (
        (None, {
            'fields': ('participacion', 'encuesta', 'fecha_respuesta', 'completada')
        }),
    )

    # Métodos para mostrar información relacionada en list_display
    @admin.display(description='Participación / Empleado')
    def participacion_info(self, obj):
        if obj.participacion:
            return f"{obj.participacion.empleado.get_full_name()} ({obj.participacion.curso.nombre})"
        return "N/A"

    @admin.display(description='Encuesta')
    def encuesta_titulo(self, obj):
        if obj.encuesta:
            # Si la encuesta está ligada a una participación, muestra el nombre del curso
            if obj.encuesta.participacion and obj.encuesta.participacion.curso:
                return obj.encuesta.participacion.curso.nombre
            # Si no, muestra el título de la encuesta si lo tiene (o su PK como fallback)
            return obj.encuesta.titulo if hasattr(obj.encuesta, 'titulo') else obj.encuesta.pk
        return "N/A"


@admin.register(DetalleRespuesta)
class DetalleRespuestaAdmin(admin.ModelAdmin):
    list_display = (
        'respuesta_encuesta_info', 'pregunta_texto', 'respuesta_texto', 'respuesta_escala'
    )
    list_filter = (
        'pregunta__tipo_pregunta',
        'pregunta__encuesta', # Filtra por la encuesta a la que pertenece la pregunta
        'respuesta_escala',
    )
    search_fields = (
        'pregunta__texto_pregunta',
        'respuesta_texto',
        'respuesta_encuesta__participacion__empleado__username',
        'respuesta_encuesta__participacion__curso__nombre',
    )
    readonly_fields = ('respuesta_encuesta', 'pregunta', 'respuesta_texto', 'respuesta_escala') # Todos los campos son de solo lectura
    
    fieldsets = (
        (None, {
            'fields': ('respuesta_encuesta', 'pregunta', 'respuesta_texto', 'respuesta_escala')
        }),
    )

    # Métodos para mostrar información relacionada en list_display
    @admin.display(description='Respuesta de Encuesta (Participante / Curso)')
    def respuesta_encuesta_info(self, obj):
        if obj.respuesta_encuesta and obj.respuesta_encuesta.participacion:
            participacion = obj.respuesta_encuesta.participacion
            return f"{participacion.empleado.get_full_name()} - {participacion.curso.nombre}"
        return "N/A"

    @admin.display(description='Pregunta')
    def pregunta_texto(self, obj):
        if obj.pregunta:
            return obj.pregunta.texto_pregunta
        return "N/A"

