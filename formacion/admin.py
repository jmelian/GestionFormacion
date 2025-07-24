# formacion/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin # Importar UserAdmin para personalizar Empleado
from django.utils.translation import gettext_lazy as _ # Para traducir los títulos de los fieldsets
from django.utils.html import format_html # Solo si se necesita para enlaces de documentos
from .forms import EmpleadoCreationForm, EmpleadoChangeForm, CursoForm, DepartamentoForm

from .models import (
    Departamento,
    Area,     
    PuestoDeTrabajo, 
    Empleado,
    Proveedor,
    Proyecto,
    Curso,
    Participacion,
    RequisitoPuestoFormacion, 
    Preseleccion,
    Notificacion,
    Titulacion, 
    SolicitudCurso,
)
from .models import EncuestaSatisfaccion, PreguntaEncuesta, RespuestaEncuesta, DetalleRespuesta


# Personalización del modelo Empleado (que ahora es nuestro AUTH_USER_MODEL)
class EmpleadoAdmin(UserAdmin):
    form = EmpleadoChangeForm
    add_form = EmpleadoCreationForm

    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'departamento', 'area', 'es_empleado_activo' # Usa el nuevo campo 'departamento' directo aquí
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
                'dni', 'departamento', 'area', 'codigo_puesto', 'sexo', # AÑADE 'departamento' aquí
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
    

# Admin para el modelo Departamento
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'coordinador')
    search_fields = ('nombre', 'coordinador__username', 'coordinador__first_name', 'coordinador__last_name')
    # Quita raw_id_fields = ('coordinador',)
    fields = ('nombre', 'descripcion', 'coordinador') # Asegúrate de incluir 'coordinador' aquí

# Admin para el nuevo modelo Area
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento', 'descripcion')
    list_filter = ('departamento',)
    search_fields = ('nombre', 'descripcion', 'departamento__nombre')
    raw_id_fields = ('departamento',)

# Admin para el nuevo modelo PuestoDeTrabajo
class PuestoDeTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo', 'departamento')
    list_filter = ('departamento',)
    search_fields = ('nombre', 'codigo', 'departamento__nombre')
    raw_id_fields = ('departamento',)
    readonly_fields = ('created_at', 'updated_at')


# Admin para el nuevo modelo Proveedor
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'created_at') 
    search_fields = ('nombre', 'email', 'telefono') # 'contacto' eliminado
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

# Admin para el nuevo modelo Proyecto
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'jefe_proyecto', 'estado', 'fecha_inicio', 'fecha_fin_prevista', 'created_at')
    list_filter = ('estado', 'jefe_proyecto', 'fecha_inicio')
    search_fields = ('nombre', 'descripcion', 'jefe_proyecto__first_name', 'jefe_proyecto__last_name')
    date_hierarchy = 'fecha_inicio' # Permite navegar por fechas
    raw_id_fields = ('jefe_proyecto',)
    readonly_fields = ('created_at', 'updated_at')

# Admin para el modelo Curso
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


# Admin para el modelo Participacion
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

# Admin para el nuevo modelo Titulacion
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


# Admin para el modelo RequisitoPuestoFormacion (antes RequisitoPuesto)
class RequisitoPuestoFormacionAdmin(admin.ModelAdmin):
    list_display = ('puesto', 'curso', 'tipo_requisito')
    list_filter = ('puesto__departamento', 'puesto__nombre', 'curso__tipo', 'tipo_requisito')
    search_fields = ('puesto__nombre', 'curso__nombre', 'observaciones')

# Admin para el modelo Preseleccion
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

# Admin para el modelo Notificacion
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'leida', 'fecha', 'tipo', 'url')
    list_filter = (
        'leida', 'tipo',
        'usuario__codigo_puesto__departamento'
    )
    search_fields = ('usuario__username', 'mensaje', 'usuario__first_name', 'usuario__last_name')
    readonly_fields = ('fecha',)

class PreguntaEncuestaInline(admin.TabularInline):
    model = PreguntaEncuesta
    extra = 1 # Número de formularios vacíos a mostrar

@admin.register(EncuestaSatisfaccion)
class EncuestaSatisfaccionAdmin(admin.ModelAdmin):
    # Campos que se muestran en la lista de objetos en el admin
    list_display = (
        'empleado',          # Empleado que hizo la encuesta
        'participacion_link',# Enlace a la participación (método personalizado)
        'fecha_encuesta',    # Fecha en que se rellenó la encuesta
        'opinion_contenido_curso', # Una de las valoraciones para ver rápidamente
        'gusto_general_curso',     # Otra valoración clave
        'valoracion_media_curso_profesor_display', # Propiedad para mostrar la media
        'valoracion_media_eficacia_display',     # Propiedad para mostrar la media
    )

    # Campos por los que se puede filtrar la lista
    list_filter = (
        'fecha_encuesta',
        'opinion_contenido_curso',
        'gusto_general_curso',
        'empleado', # Para filtrar por empleado
        'participacion__curso', # Para filtrar por el curso de la participación
    )

    # Campos por los que se puede buscar texto
    search_fields = (
        'empleado__username',
        'empleado__first_name',
        'empleado__last_name',
        'participacion__curso__nombre', # Buscar por nombre del curso
        'sugerencias_observaciones',
    )
    
    # Campos que solo se pueden leer (no editar) en el formulario de detalle
    readonly_fields = (
        'participacion',
        'empleado',
        'fecha_encuesta',
        'valoracion_media_curso_profesor_display', # Mostrar la media calculada
        'valoracion_media_eficacia_display',     # Mostrar la media calculada
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

    # Métodos para list_display que no son campos directos del modelo
    def participacion_link(self, obj):
        # Asumiendo que tienes una URL para ver los detalles de Participacion
        from django.utils.html import format_html
        from django.urls import reverse
        # Intenta enlazar al detalle de la participación si tienes una URL para ello
        try:
            url = reverse('admin:%s_%s_change' % (obj.participacion._meta.app_label, obj.participacion._meta.model_name), args=[obj.participacion.id])
            return format_html('<a href="{}">{}</a>', url, obj.participacion)
        except Exception:
            return str(obj.participacion)
    participacion_link.short_description = 'Participación'
    participacion_link.admin_order_field = 'participacion' # Permite ordenar por la relación

    def valoracion_media_curso_profesor_display(self, obj):
        # Utiliza el @property del modelo
        return f"{obj.valoracion_media_curso_profesor:.2f}" if obj.valoracion_media_curso_profesor is not None else 'N/A'
    valoracion_media_curso_profesor_display.short_description = 'Media Curso/Profesor'
    valoracion_media_curso_profesor_display.admin_order_field = 'opinion_contenido_curso' # Ordena por un campo relevante

    def valoracion_media_eficacia_display(self, obj):
        # Utiliza el @property del modelo
        return f"{obj.valoracion_media_eficacia:.2f}" if obj.valoracion_media_eficacia is not None else 'N/A'
    valoracion_media_eficacia_display.short_description = 'Media Eficacia'
    valoracion_media_eficacia_display.admin_order_field = 'mejora_conocimientos_carrera' # Ordena por un campo relevante

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

# Registrar los modelos con sus clases Admin personalizadas
admin.site.register(Departamento, DepartamentoAdmin) 
admin.site.register(Area, AreaAdmin)             
admin.site.register(PuestoDeTrabajo, PuestoDeTrabajoAdmin) 
admin.site.register(Empleado, EmpleadoAdmin)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Proyecto, ProyectoAdmin)
admin.site.register(Curso, CursoAdmin)
admin.site.register(Participacion, ParticipacionAdmin)
admin.site.register(RequisitoPuestoFormacion, RequisitoPuestoFormacionAdmin) 
admin.site.register(Preseleccion, PreseleccionAdmin)
admin.site.register(Notificacion, NotificacionAdmin)
admin.site.register(Titulacion, TitulacionAdmin)
admin.site.register(RespuestaEncuesta)
admin.site.register(DetalleRespuesta)