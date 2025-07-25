# formacion/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta, date
from django.utils import timezone

# --- Constantes de Choices Generales (se mantienen aquí si no pertenecen a un modelo específico) ---

# Para el modelo Curso
TIPO_CURSO_CHOICES = [
    ('onboarding', 'Onboarding'),
    ('refuerzo', 'Refuerzo'),
    ('tecnico', 'Técnico'),
    ('idiomas', 'Idiomas'),
    ('habilidades_blandas', 'Soft skills'),
    ('cumplimiento_seguridad', 'Cumplimiento y Seguridad'),
    ('otro', 'Otro'),
]

MODALIDAD_CURSO_CHOICES = [
    ('presencial', 'Presencial'),
    ('online', 'Online'),
    ('mixta', 'Mixta'),
]

RESULTADO_FORMAL_CHOICES = [
    ('academico', 'Título Académico (MECES)'),
    ('certificacion_profesional', 'Certificación Profesional Externa'),
    ('certificado_interno', 'Certificado/Diploma de Asistencia Interno'),
    ('no_aplica', 'Sin Reconocimiento Formal'),
]

ORIGEN_CURSO_CHOICES = [
    ('interno', 'Interno (desarrollado por la empresa)'),
    ('externo', 'Externo (contratado a un proveedor)'),
]

# Para el modelo Participacion
ESTADO_PARTICIPACION_CHOICES = [
    ('pendiente', 'Pendiente de Confirmación'),
    ('confirmado', 'Confirmado'),
    ('asistido', 'Asistido'),
    ('aprobado', 'Aprobado'),
    ('suspendido', 'Suspendido'),
    ('cancelado', 'Cancelado'),
    ('completado', 'Completado (Aprobado y Certificado)'),
]

# Para el modelo Proyecto
ESTADO_PROYECTO_CHOICES = [
    ('planificado', 'Planificado'),
    ('en_curso', 'En Curso'),
    ('completado', 'Completado'),
    ('cancelado', 'Cancelado'),
]

# Para el modelo Notificacion
TIPO_NOTIFICACION_CHOICES = [
    ('info', 'Información'),
    ('success', 'Éxito'),
    ('warning', 'Advertencia'),
    ('error', 'Error'),
]

# Para el modelo Titulacion
TIPO_TITULACION_CHOICES = [
    ('grado', 'Grado, Arquitecto Técnico, Ingeniero Técnico, Diplomado'),
    ('master', 'Máster, Licenciado, Arquitecto, Ingeniero'),
    ('doctorado', 'Doctorado'),
    ('fp_superior', 'Formación Profesional Grado Superior'),
    ('fp_medio', 'Formación Profesional Grado Medio'),
    ('bachiller', 'Bachillerato'),
    ('eso', 'Educación Secundaria Obligatoria (ESO)'),
    ('idioma', 'Idioma Extranjero'),
    ('curso_especializacion', 'Curso de Especialización/Experto'),
    ('otro', 'Otro'),
]

# Choices para MECES (con 'otro_meces' para evitar conflictos)
NIVEL_MECES_CHOICES = [
    ('nivel_0', 'Nivel 0: Certificado de Escolaridad o equivalente'),
    ('nivel_1', 'Nivel 1: Técnico Superior (FP Superior, Artes Plásticas y Diseño, Deportivo)'), # Ajustada descripción
    ('nivel_2', 'Nivel 2: Grado, Arquitecto Técnico, Ingeniero Técnico, Diplomado'), # Ajustada descripción
    ('nivel_3', 'Nivel 3: Máster, Licenciado, Arquitecto, Ingeniero'), # Ajustada descripción
    ('nivel_4', 'Nivel 4: Doctor'),
    ('otro_meces', 'Otro / No aplicable MECES'),
]


# Mapeo de Tipo de Titulación a Nivel MECES por defecto
TIPO_TITULACION_MECES_MAP = {
    'grado': 'nivel_2',          # Grado, Arquitecto Técnico, Ingeniero Técnico, Diplomado
    'master': 'nivel_3',         # Máster, Licenciado, Arquitecto, Ingeniero
    'doctorado': 'nivel_4',
    'fp_superior': 'nivel_1',    
    'fp_medio': 'nivel_0',       # FP Grado Medio no tiene MECES directo, pero se asocia con Nivel 0 o 1
    'bachiller': 'nivel_0',      # Bachillerato no tiene MECES directo, pero se asocia con Nivel 0 o 1
    'eso': 'nivel_0',            # ESO no tiene MECES directo, suele ser el nivel de acceso al 1
    'idioma': 'otro_meces',
    'curso_especializacion': 'otro_meces',
    'otro': 'otro_meces',
}

NIVEL_IDIOMA_CHOICES = [
    ('a1', 'A1 - Básico'),
    ('a2', 'A2 - Pre-intermedio'),
    ('b1', 'B1 - Intermedio'),
    ('b2', 'B2 - Intermedio Alto'),
    ('c1', 'C1 - Avanzado'),
    ('c2', 'C2 - Maestría'),
    ('nativo', 'Nativo'),
]

ESTADO_TITULACION_CHOICES = [
    ('pendiente', 'Pendiente de Revisión RRHH'),
    ('aprobado', 'Aprobado'),
    ('rechazado', 'Rechazado'),
]

# Definición de las opciones para el Carácter de la Formación
CARACTER_FORMACION_CHOICES = [
    ('urgente', 'Urgente / Crítico'),
    ('planificado', 'Planificado'),
    ('obligatorio_legal', 'Obligatorio / Legal'),
    ('otro', 'Otro'),
]

# --- Modelos ---

class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True, help_text="Nombre del departamento de la organización.")
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción detallada del departamento.")
    coordinador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='departamentos_coordinados', help_text="Empleado que coordina este departamento.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Area(models.Model):
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del área dentro de un departamento."
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name='areas',
        help_text="Departamento al que pertenece esta área."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del área."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        unique_together = ('nombre', 'departamento')
        ordering = ['departamento__nombre', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"


class PuestoDeTrabajo(models.Model):
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del puesto de trabajo."
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Código identificador único del puesto."
    )
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name='puestos_trabajo',
        help_text="Departamento al que pertenece el puesto de trabajo."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción de las responsabilidades y requisitos del puesto."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = ('nombre', 'departamento')
        verbose_name = "Puesto de Trabajo"
        verbose_name_plural = "Puestos de Trabajo"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"


# Modelo de Empleado (extiende AbstractUser de Django)
class Empleado(AbstractUser):
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]
    SEDE_CHOICES = [
        ('tf', 'TF'),
        ('remoto', 'Remoto'),
        ('gc', 'CG'),
    ]
    ESTADO_EMPLEADO_CHOICES = [
        ('activo', 'Activo'),
        ('baja', 'Baja definitiva'),
        ('baja_medica', 'Baja médica'),
        ('vacaciones', 'Vacaciones'),
        ('licencia', 'Licencia'),
    ]

    dni = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Número de identificación del empleado.")
    sexo = models.CharField(max_length=20, choices=SEXO_CHOICES, blank=True, null=True, help_text="Género del empleado.")
    sede = models.CharField(max_length=50, choices=SEDE_CHOICES, blank=True, null=True, help_text="Sede principal de trabajo del empleado.")
    estado = models.CharField(max_length=50, choices=ESTADO_EMPLEADO_CHOICES, default='activo', help_text="Estado actual del empleado en la empresa.")
    departamento = models.ForeignKey(
        'Departamento', # Referencia al modelo Departamento
        on_delete=models.SET_NULL, # Si un departamento se elimina, este campo se pone a NULL
        null=True, # Permite que el campo esté vacío en la base de datos
        blank=True, # Permite que el campo esté vacío en los formularios
        related_name='empleados', # Nombre inverso para obtener los empleados de un departamento (ej: depto.empleados.all())
        help_text="Departamento al que pertenece directamente el empleado."
    )
    area = models.ForeignKey(
        'Area',
        on_delete=models.SET_NULL, # Si un Área se elimina, este campo se pone a NULL
        null=True,                 # Permite que el campo esté vacío en la base de datos
        blank=True,                # Permite que el campo esté vacío en los formularios
        related_name='empleados_directos_area', # Nombre inverso para obtener empleados de un área (ej: area.empleados_directos_area.all())
        help_text="Área a la que pertenece directamente el empleado."
    )
    puesto = models.CharField(max_length=255, null=True, blank=True, help_text="Puesto principal del empleado.")
    codigo_puesto = models.ForeignKey( # Este es el ForeignKey a PuestoDeTrabajo
        'PuestoDeTrabajo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='empleados_vinculados_requisitos',
        help_text="Puesto de trabajo oficial asignado a este empleado."
    )
    es_empleado_activo = models.BooleanField(default=True, help_text="Indica si el empleado está actualmente activo en la empresa (para filtros rápidos).")

    groups = models.ManyToManyField('auth.Group', related_name='empleado_set', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups',)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='empleado_set', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions',)

    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def departamento_actual(self):
        # Prioriza el campo 'departamento' directo del empleado
        if self.departamento:
            return self.departamento
        # Luego, si el empleado tiene un 'area' directo, usa el departamento de esa área
        elif self.area and self.area.departamento:
            return self.area.departamento
        # Finalmente, si tiene un 'codigo_puesto', usa el departamento del área de ese puesto
        elif self.codigo_puesto and self.codigo_puesto.area and self.codigo_puesto.area.departamento:
            return self.codigo_puesto.area.departamento
        return None

    @property
    def area_actual(self):
        # NUEVA PROPIEDAD: Obtiene el área priorizando el campo directo
        if self.area: # Si tiene un área asignada directamente
            return self.area
        elif self.codigo_puesto and self.codigo_puesto.area: # Si no, intenta obtenerla del puesto de trabajo
            return self.codigo_puesto.area
        return None

    @property
    def is_rrhh(self):
        return self.groups.filter(name=settings.GRUPO_RRHH).exists()

    @property
    def is_formacion(self):
        return self.groups.filter(name=settings.GRUPO_FORMACION).exists()

    @property
    def is_coordinador(self):
        return self.groups.filter(name=settings.GRUPO_COORDINADOR).exists()

    @property
    def is_direccion(self):
        return self.groups.filter(name=settings.GRUPO_DIRECCION).exists()

    @property
    def is_empleado_rol(self):
        return self.groups.filter(name=settings.GRUPO_EMPLEADO).exists()


class Proveedor(models.Model):
    nombre = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nombre del proveedor de formación."
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Correo electrónico de contacto del proveedor."
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Número de teléfono de contacto del proveedor."
    )
    web = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Dirección URL de la página web del proveedor."
    )
    direccion = models.TextField(
        blank=True,
        null=True,
        help_text="Dirección física del proveedor."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Proyecto(models.Model):
    nombre = models.CharField(
        max_length=200,
        help_text="Nombre del proyecto o iniciativa de formación."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del proyecto."
    )
    jefe_proyecto = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_liderados',
        help_text="Empleado responsable del proyecto."
    )
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_PROYECTO_CHOICES,
        default='planificado',
        help_text="Estado actual del proyecto."
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de inicio del proyecto."
    )
    fecha_fin_prevista = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de fin prevista del proyecto."
    )
    fecha_fin_real = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de finalización real del proyecto."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['fecha_inicio', 'nombre']

    def __str__(self):
        return self.nombre


class Curso(models.Model):
    nombre = models.CharField(max_length=200, help_text="Nombre completo del curso.")
    contenido = models.TextField(blank=True, null=True, help_text="Descripción detallada del contenido del curso.")
    tipo = models.CharField(max_length=50, choices=TIPO_CURSO_CHOICES, default='otro', help_text="Tipo de formación que imparte el curso.")
    resultado_formal = models.CharField(max_length=50, choices=RESULTADO_FORMAL_CHOICES, default='no_aplica', help_text="Tipo de reconocimiento formal que se obtiene al finalizar el curso.")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos_ofrecidos', help_text="Proveedor externo que imparte el curso.")
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_CURSO_CHOICES, default='presencial', help_text="Modalidad de impartición del curso.")
    duracion_horas = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)], help_text="Duración total del curso en horas.")
    fecha_inicio = models.DateField(null=True, blank=True, help_text="Fecha de inicio de la edición actual del curso.")
    fecha_fin = models.DateField(null=True, blank=True, help_text="Fecha de fin de la edición actual del curso.")
    plazas_totales = models.PositiveIntegerField(default=0, help_text="Número total de plazas disponibles en el curso.")
    plazas_disponibles = models.PositiveIntegerField(default=0, help_text="Número de plazas aún disponibles para inscripción. Se actualiza automáticamente.")
    observaciones = models.TextField(blank=True, null=True, help_text="Notas o comentarios adicionales sobre el curso.")
    externo = models.BooleanField(default=False, help_text="Indica si el curso es impartido por un proveedor externo.")
    origen = models.CharField(max_length=20, choices=ORIGEN_CURSO_CHOICES, default='interno', help_text="Indica si el curso es interno o externo a la organización.")
    es_obligatorio = models.BooleanField(default=False, help_text="Indica si este curso es generalmente obligatorio para algún puesto o perfil.")
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos_asociados', help_text="Proyecto de formación al que se asocia este curso.")
    departamento_solicitante = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos_solicitados', help_text="Departamento que solicitó o al que va dirigido principalmente este curso.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['fecha_inicio', 'nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.pk:
            self.plazas_disponibles = self.plazas_totales
        super().save(*args, **kwargs)

class SolicitudCurso(models.Model):
    # Información básica y de solicitante (gestionada automáticamente)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitudes_cursos',
        verbose_name='Coordinador/a Solicitante'
    )
    # Si el usuario tiene un departamento asociado, lo asignamos aquí.
    # Asegúrate de que tu modelo de usuario o un modelo de Empleado relacionado tenga un campo 'departamento'.
    # Ejemplo: Si tienes un modelo Empleado con ForeignKey a Departamento, y User tiene OneToOneField a Empleado
    departamento_solicitante = models.ForeignKey(
        'formacion.Departamento',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Departamento Solicitante'
    )
    fecha_solicitud = models.DateTimeField(default=timezone.now, verbose_name='Fecha de Solicitud')

    # Información del curso solicitado
    titulo_curso_solicitado = models.CharField(max_length=200, verbose_name='Título del Curso Solicitado')
    
    objetivo_curso = models.TextField(verbose_name='Objetivo del Curso')
    justificacion_necesidad = models.TextField(verbose_name='Justificación de la Necesidad')
    numero_participantes_estimado = models.PositiveIntegerField(
        verbose_name='Número Estimado de Participantes',
        help_text='Indica cuántos empleados aproximadamente necesitarían esta formación.'
    )

    temas_contenidos_clave = models.TextField(
        blank=True, null=True,
        verbose_name='Temas o Contenidos Clave a Cubrir',
        help_text='Describe brevemente los principales temas o módulos que te gustaría que el curso abarcara.'
    )
    formato_preferido = models.CharField(
        max_length=50,
        choices=[
            ('presencial', 'Presencial'),
            ('online_sincrono', 'Online (con instructor en vivo)'),
            ('online_asincrono', 'Online (a tu ritmo)'),
            ('blended', 'Blended (Mixto)')
        ],
        blank=True, null=True,
        verbose_name='Formato Preferido'
    )
    duracion_estimada = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name='Duración Estimada',
        help_text='Ej: "8 horas", "2 días", "3 módulos por semana".'
    )
    fechas_horarios_preferidos = models.TextField(
        blank=True, null=True,
        verbose_name='Fechas/Horarios Preferidos',
        help_text='Si tienes alguna preferencia de fechas o franjas horarias.'
    )

    # Nuevo campo de Carácter de la Formación
    caracter_formacion = models.CharField(
        max_length=50,
        choices=CARACTER_FORMACION_CHOICES,
        default='planificado', # Valor por defecto si no se especifica
        verbose_name='Carácter de la Formación',
        help_text='Indica la urgencia o naturaleza de la necesidad de formación.'
    )

    comentarios_adicionales = models.TextField(
        blank=True, null=True,
        verbose_name='Comentarios/Notas Adicionales'
    )

    # Estado de la solicitud (para el seguimiento interno por RRHH/Formación)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('aprobada', 'Aprobada'),
            ('rechazada', 'Rechazada'),
            ('en_proceso', 'En Proceso'),
            ('completada', 'Completada')
        ],
        default='pendiente',
        verbose_name='Estado de la Solicitud'
    )

    motivo_rechazo = models.TextField(
        blank=True, null=True,
        verbose_name='Motivo del Rechazo',
        help_text='Explica por qué se ha rechazado esta solicitud.'
    )
    comentarios_procesamiento = models.TextField(
        blank=True, null=True,
        verbose_name='Comentarios de Procesamiento',
        help_text='Notas internas sobre la conversión a curso formal o finalización.'
    )

    class Meta:
        verbose_name = "Solicitud de Curso"
        verbose_name_plural = "Solicitudes de Cursos"
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"Solicitud: {self.titulo_curso_solicitado} por {self.solicitante.username}"
    

class Participacion(models.Model):
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='participaciones',
        help_text="Empleado que participa en el curso."
    )
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='participantes',
        help_text="Curso en el que participa el empleado."
    )
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_PARTICIPACION_CHOICES,
        default='pendiente',
        help_text="Estado actual de la participación del empleado en el curso."
    )
    nota_final = models.CharField(
        max_length=100, # Choose an appropriate max_length, e.g., 50, 100, or 255
        blank=True,
        null=True, # CharField with blank=True will store '' by default if not null=True. null=True is better for truly optional fields.
        help_text="Calificación final o estado textual (ej. Aprobado, N/A, 7.5)."
    )
    validado = models.BooleanField(
        default=False,
        help_text="Indica si la participación y resultados han sido validados por RRHH."
    )
    certificado_obtenido = models.BooleanField(
        default=False,
        help_text="Indica si el empleado ha obtenido el certificado/título del curso."
    )
    fecha_certificado = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de obtención del certificado."
    )
    fecha_inicio_real = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de inicio asignada por RRHH para esta participación específica."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación de la participación (puede usarse como fecha de inscripción inicial)."
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Participación"
        verbose_name_plural = "Participaciones"
        unique_together = ('empleado', 'curso')
        ordering = ['created_at', 'empleado']

    def __str__(self):
        return f"{self.empleado.get_full_name()} - {self.curso.nombre} ({self.get_estado_display()})"


class Titulacion(models.Model):
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='titulaciones',
        help_text="Empleado que posee esta titulación."
    )
    nombre = models.CharField(
        max_length=255,
        help_text="Nombre oficial de la titulación, grado, certificación o curso."
    )
    tipo_titulacion = models.CharField(
        max_length=50,
        choices=TIPO_TITULACION_CHOICES, # Asegúrate de que TIPO_TITULACION_CHOICES está definido
        default='otro',
        help_text="Tipo de cualificación académica o profesional."
    )
    institucion_emisora = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Institución o entidad que emitió la titulación."
    )
    fecha_obtencion = models.DateField(
        help_text="Fecha en que la titulación fue obtenida."
    )
    fecha_caducidad = models.DateField(
        blank=True,
        null=True,
        help_text="Fecha de caducidad de la titulación, si aplica (ej. certificaciones)."
    )

    documento_adjunto = models.FileField(
        upload_to='titulaciones/',
        blank=True,
        null=True,
        help_text="Documento de soporte de la titulación (ej. certificado, diploma)."
    )
    
    estado = models.CharField(
        max_length=50,
        choices=ESTADO_TITULACION_CHOICES,
        default='pendiente', # La titulación empieza en estado pendiente
        help_text="Estado actual de la titulación en el proceso de revisión de RRHH."
    )
    motivo_rechazo = models.TextField(
        blank=True,
        null=True,
        help_text="Razón específica proporcionada por RRHH si la titulación fue rechazada."
    )

    curso_relacionado = models.ForeignKey(
        'Curso', # Usa una cadena si Curso está definido más abajo o en otro archivo en el mismo app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='titulaciones_emitidas',
        help_text="Curso interno de la empresa al que está relacionada esta titulación (si aplica)."
    )
    nivel_idioma = models.CharField(
        max_length=10,
        choices=NIVEL_IDIOMA_CHOICES, # Asegúrate de que NIVEL_IDIOMA_CHOICES está definido
        blank=True,
        null=True,
        help_text="Nivel del idioma obtenido, según marco común europeo (si aplica a titulaciones de idioma)."
    )
    nivel_meces = models.CharField(
        max_length=20,
        choices=NIVEL_MECES_CHOICES, # Asegúrate de que NIVEL_MECES_CHOICES está definido
        blank=True,
        null=True,
        help_text="Nivel de la titulación según el Marco Español de Cualificaciones para la Educación Superior (MECES)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Titulación/Certificación"
        verbose_name_plural = "Titulaciones/Certificaciones"
        ordering = ['-fecha_obtencion', 'empleado']
        # Si tenías 'unique_together', reevalúa si sigue siendo adecuado
        # unique_together = ('empleado', 'nombre', 'institucion_emisora', 'fecha_obtencion')

    def __str__(self):
        return f"{self.nombre} ({self.empleado.get_full_name()}) - {self.get_estado_display()}"

    # Métodos de conveniencia para el estado
    def is_pending(self):
        return self.estado == 'pendiente'

    def is_approved(self):
        return self.estado == 'aprobado'

    def is_rejected(self):
        return self.estado == 'rechazado'


class RequisitoPuestoFormacion(models.Model):
    puesto = models.ForeignKey(
        PuestoDeTrabajo, # Esto sigue apuntando al modelo PuestoDeTrabajo
        on_delete=models.CASCADE,
        related_name='requisitos_formacion',
        help_text="Puesto de trabajo al que aplica este requisito de formación."
    )
    curso = models.ForeignKey(
        'Curso',
        on_delete=models.CASCADE,
        related_name='requisitos_puesto',
        help_text="Curso obligatorio o recomendado para este puesto."
    )
    tipo_requisito = models.CharField(
        max_length=20,
        choices=[('obligatorio', 'Obligatorio'), ('recomendado', 'Recomendado')],
        default='obligatorio',
        help_text="Indica si el curso es obligatorio o recomendado para el puesto."
    )
    fecha_implementacion = models.DateField(null=True, blank=True, help_text="Fecha a partir de la cual este requisito es efectivo.")

    class Meta:
        unique_together = ('puesto', 'curso')
        verbose_name = "Requisito de Puesto de Formación"
        verbose_name_plural = "Requisitos de Puestos de Formación"

    def __str__(self):
        return f"Req. {self.curso.nombre} para {self.puesto.nombre} ({self.tipo_requisito})"

class Preseleccion(models.Model):
    curso = models.ForeignKey(
        Curso,
        on_delete=models.CASCADE,
        related_name='preseleccionados',
        help_text="Curso para el que se postularán participantes."
    )
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preselecciones',
        help_text="Empleado preseleccionado para el curso."
    )
    prioridad = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Orden de prioridad de la preselección."
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones del coordinador sobre la preselección."
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preselecciones_creadas',
        help_text="Coordinador que realizó la preselección."
    )
    fecha = models.DateField(
        auto_now_add=True,
        help_text="Fecha de la preselección."
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Preselección"
        verbose_name_plural = "Preselecciones"
        unique_together = ('curso', 'empleado')
        ordering = ['prioridad', 'fecha']

    def __str__(self):
        return f"{self.empleado.get_full_name()} → {self.curso.nombre} (P{self.prioridad})"

class EncuestaSatisfaccion(models.Model):
    # Relación con la participación y el curso
    participacion = models.OneToOneField('Participacion', on_delete=models.CASCADE,
                                         related_name='encuesta',
                                         help_text="La participación a la que se refiere esta encuesta.",
                                         null=True, blank=True)
    empleado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 help_text="Empleado que rellena la encuesta.",
                                 null=True, blank=True)
    
    # Datos del curso (pueden ser redundantes si se obtienen de participacion.curso,
    # pero a veces se guardan para "snapshot" en el momento de la encuesta)
    # Sin embargo, si siempre accedemos via participacion, no es estrictamente necesario guardarlos aquí.
    # Podrías eliminarlos y acceder a ellos vía participacion.curso.nombre, etc.
    # Los incluyo si quieres guardar un registro inmutable de esos datos en la encuesta.
    nombre_curso_encuesta = models.CharField(max_length=255, blank=True, null=True)
    nombre_profesor_encuesta = models.CharField(max_length=255, blank=True, null=True)
    fecha_encuesta = models.DateField(default=date.today) # Fecha en que se rellena la encuesta

    # Valoración del Profesor / Curso (usamos Choices para las valoraciones 1-5)
    VALORACION_CHOICES = (
        (5, 'Excelente'),
        (4, 'Muy Bueno'),
        (3, 'Bueno'),
        (2, 'Regular'),
        (1, 'Mal'),
    )
    
    opinion_contenido_curso = models.PositiveSmallIntegerField(
        choices=VALORACION_CHOICES,
        verbose_name="Opinión sobre el contenido del curso"
    )
    conocimientos_profesor = models.PositiveSmallIntegerField(
        choices=VALORACION_CHOICES,
        verbose_name="Conocimientos técnicos del profesor"
    )
    gusto_general_curso = models.PositiveSmallIntegerField(
        choices=VALORACION_CHOICES,
        verbose_name="En general, ¿le ha gustado el curso?"
    )
    # valoracion_final_curso_profesor: Podría ser un campo calculado en el admin o en un método del modelo
    # o un campo de entrada si quieres que el usuario dé una valoración final manual

    # Valoración de la Eficacia de la Formación
    mejora_conocimientos_carrera = models.PositiveSmallIntegerField(
        choices=VALORACION_CHOICES,
        verbose_name="He mejorado/ampliado conocimientos para progresar en mi carrera profesional"
    )
    adquisicion_habilidades_puesto = models.PositiveSmallIntegerField(
        choices=VALORACION_CHOICES,
        verbose_name="He adquirido nuevas habilidades/capacidades que puedo aplicar a mi puesto de trabajo"
    )
    # valoracion_final_eficacia: Similar al anterior, campo calculado o manual

    # Sugerencias / Observaciones
    sugerencias_observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Sugerencias / Observaciones"
    )

    class Meta:
        verbose_name = "Encuesta de Satisfacción"
        verbose_name_plural = "Encuestas de Satisfacción"
        # Asegura que un empleado solo pueda rellenar una encuesta por participación
        unique_together = ('participacion', 'empleado') 

    def __str__(self):
        return f"Encuesta de {self.empleado.username} para {self.participacion.curso.nombre}"

    # Métodos para calcular valoraciones finales si no son campos de entrada
    @property
    def valoracion_media_curso_profesor(self):
        return (self.opinion_contenido_curso + self.conocimientos_profesor + self.gusto_general_curso) / 3

    @property
    def valoracion_media_eficacia(self):
        return (self.mejora_conocimientos_carrera + self.adquisicion_habilidades_puesto) / 2


class PreguntaEncuesta(models.Model):
    """
    Define una pregunta para una EncuestaSatisfaccion.
    """
    TIPOS_PREGUNTA = [
        ('texto', 'Respuesta Abierta (Texto)'),
        ('opcion_multiple', 'Opción Múltiple (Selección Única)'), # Si necesitas varias opciones, usa un ManyToMany en la respuesta
        ('escala', 'Escala de Calificación (1-5, 1-10, etc.)'),
    ]
    
    encuesta = models.ForeignKey(EncuestaSatisfaccion, on_delete=models.CASCADE, related_name='preguntas')
    texto_pregunta = models.TextField()
    tipo_pregunta = models.CharField(max_length=50, choices=TIPOS_PREGUNTA, default='texto')
    orden = models.IntegerField(default=0, help_text="Orden en que aparecerá la pregunta en la encuesta.")

    # Para preguntas de opción múltiple o escala, podrías añadir un campo para las opciones,
    # aunque para simplicidad inicial, la escala puede ser implícita (ej. 1 al 5)
    # Si las opciones son fijas y pocas:
    # opciones_choice = models.CharField(max_length=255, blank=True, help_text="Opciones separadas por coma para opción múltiple/escala")

    def __str__(self):
        return f"{self.encuesta.titulo} - Pregunta {self.orden}: {self.texto_pregunta[:50]}..."

    class Meta:
        verbose_name = "Pregunta de Encuesta"
        verbose_name_plural = "Preguntas de Encuesta"
        ordering = ['orden']


class RespuestaEncuesta(models.Model):
    """
    Almacena las respuestas de un empleado a una encuesta específica para una participación de curso.
    """
    participacion = models.OneToOneField(
        Participacion,
        on_delete=models.CASCADE,
        related_name='respuesta_satisfaccion',
        help_text="Participación de curso a la que corresponde esta respuesta de encuesta."
    )
    encuesta = models.ForeignKey(EncuestaSatisfaccion, on_delete=models.CASCADE, related_name='respuestas_recibidas')
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    completada = models.BooleanField(default=False, help_text="Indica si la encuesta ha sido completada por el usuario.")

    def __str__(self):
        return f"Respuesta de {self.participacion.empleado.get_full_name()} para {self.participacion.curso.nombre}"

    class Meta:
        verbose_name = "Respuesta de Encuesta"
        verbose_name_plural = "Respuestas de Encuestas"
        # Asegura que solo haya una respuesta por participación
        unique_together = ('participacion',)


class DetalleRespuesta(models.Model):
    """
    Almacena cada respuesta individual a una pregunta específica de la encuesta.
    """
    respuesta_encuesta = models.ForeignKey(RespuestaEncuesta, on_delete=models.CASCADE, related_name='detalles')
    pregunta = models.ForeignKey(PreguntaEncuesta, on_delete=models.CASCADE)
    
    # Campo para almacenar la respuesta, adaptable al tipo de pregunta
    respuesta_texto = models.TextField(blank=True, null=True) # Para preguntas de texto
    respuesta_escala = models.IntegerField(blank=True, null=True) # Para escalas numéricas (ej. 1-5)
    # Si tuvieras opción múltiple con ID de opción, necesitarías otro ForeignKey
    # respuesta_opcion = models.ForeignKey(OpcionPregunta, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Respuesta a '{self.pregunta.texto_pregunta[:30]}...' de {self.respuesta_encuesta.participacion.empleado.get_full_name()}"

    class Meta:
        verbose_name = "Detalle de Respuesta"
        verbose_name_plural = "Detalles de Respuestas"
        # Asegura que un usuario solo responda una vez cada pregunta en una encuesta específica
        unique_together = ('respuesta_encuesta', 'pregunta')

class Notificacion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        help_text="Usuario que recibe la notificación."
    )
    mensaje = models.TextField(
        help_text="Contenido del mensaje de notificación."
    )
    leida = models.BooleanField(
        default=False,
        help_text="Indica si la notificación ha sido leída por el usuario."
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación de la notificación."
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_NOTIFICACION_CHOICES,
        default='info',
        help_text="Tipo de notificación (ej. 'success', 'info', 'warning', 'error')."
    )
    url = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="URL a la que apunta la notificación (opcional)."
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha', 'leida']

    def __str__(self):
        return f"Notificación para {self.usuario.username}: {self.mensaje[:50]}..."