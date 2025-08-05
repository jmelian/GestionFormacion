# formacion/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    Empleado, Curso, Preseleccion, Participacion, Departamento,
    PuestoDeTrabajo, Area, Proveedor, Proyecto, Titulacion,
    RequisitoPuestoFormacion, Notificacion, SolicitudCurso, EncuestaSatisfaccion
)
from .models import (TIPO_TITULACION_MECES_MAP, NIVEL_MECES_CHOICES, 
    TIPO_TITULACION_CHOICES, NIVEL_IDIOMA_CHOICES, CARACTER_FORMACION_CHOICES
)
from django.forms import ValidationError
from django.utils import timezone
from django.db.models import Q
import datetime




# Formularios para el modelo Empleado
# ---------------------------------------------------------------------------------
# FORMULARIOS PARA EL DJANGO ADMIN
# ---------------------------------------------------------------------------------

class EmpleadoCreationForm(UserCreationForm):

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        strip=False,
        required=True,

    )
    password2 = forms.CharField(
        label="Contraseña (confirmación)",
        widget=forms.PasswordInput,
        strip=False,
        required=True,
        # help_text="Vuelva a introducir la misma contraseña."
    )


    # Campos de información de Empleado (no parte del User base)
    dni = forms.CharField(max_length=20, required=False, label="DNI/NIE")
    sexo = forms.ChoiceField(choices=Empleado.SEXO_CHOICES, required=False, label="Género")
    sede = forms.ChoiceField(choices=Empleado.SEDE_CHOICES, required=False, label="Sede Principal de Trabajo")
    estado = forms.ChoiceField(
        choices=Empleado.ESTADO_EMPLEADO_CHOICES, 
        required=True, 
        initial='activo', 
        label="Estado Actual del Empleado"
    )
    
    # Campos para la estructura organizativa
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all().order_by('nombre'),
        required=False, 
        label="Departamento"
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all().order_by('departamento__nombre', 'nombre'),
        required=False,
        label="Área"
    )
    puesto = forms.CharField(max_length=255, required=False, label="Puesto (Descripción Libre)")
    codigo_puesto = forms.ModelChoiceField(
        queryset=PuestoDeTrabajo.objects.all().order_by('nombre'),
        required=False,
        label="Código de Puesto Oficial"
    )
    
    es_empleado_activo = forms.BooleanField(
        label="¿Es empleado activo?",
        initial=True,
        required=False, 
    )

    class Meta(UserCreationForm.Meta):
        model = Empleado
        # UserCreationForm.Meta.fields ya incluye 'username', 'password', 'password2'.
        # Añadimos los campos personalizados del modelo Empleado y los de AbstractUser que queremos en el formulario de creación.
        fields = UserCreationForm.Meta.fields + (
            'username', 'password1', 'password2',
            'first_name', 'last_name', 'email', # Campos de AbstractUser adicionales que no vienen por defecto en UserCreationForm.Meta.fields
            'dni', 'sexo', 'sede', 'estado', 'departamento', 'area', 'puesto', 'codigo_puesto',
            'es_empleado_activo',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].required = True 
        self.fields['password2'].required = True
        # Inicializar querysets para campos ModelChoiceField
        self.fields['departamento'].queryset = Departamento.objects.all().order_by('nombre')
        self.fields['area'].queryset = Area.objects.all().order_by('departamento__nombre', 'nombre')
        self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.all().order_by('nombre')


    def clean(self):
        cleaned_data = super().clean()

        departamento = cleaned_data.get('departamento')
        area = cleaned_data.get('area')
        codigo_puesto = cleaned_data.get('codigo_puesto')

        # Si se selecciona un área y un departamento, validar que el área pertenece al departamento.
        if area and departamento and area.departamento != departamento:
            self.add_error('area', "El área seleccionada no pertenece al departamento elegido.")

        # Si se selecciona un puesto de trabajo y un departamento, validar que el puesto pertenece a ese departamento.
        if codigo_puesto and departamento and codigo_puesto.departamento != departamento:
            self.add_error('codigo_puesto', "El puesto de trabajo seleccionado no pertenece al departamento elegido.")

        return cleaned_data

class EmpleadoChangeForm(UserChangeForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
    )
    password2 = forms.CharField(
        label="Contraseña (confirmación)",
        widget=forms.PasswordInput,
        strip=False,
        required=False,
    )

    dni = forms.CharField(max_length=20, required=False, label="DNI/NIE")
    sexo = forms.ChoiceField(choices=Empleado.SEXO_CHOICES, required=False, label="Género")
    sede = forms.ChoiceField(choices=Empleado.SEDE_CHOICES, required=False, label="Sede Principal de Trabajo")
    estado = forms.ChoiceField(
        choices=Empleado.ESTADO_EMPLEADO_CHOICES, 
        required=False, 
        label="Estado Actual del Empleado"
    )
    
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all().order_by('nombre'),
        required=False,
        label="Departamento"
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all().order_by('departamento__nombre', 'nombre'),
        required=False,
        label="Área"
    )
    puesto = forms.CharField(max_length=255, required=False, label="Puesto (Descripción Libre)")
    codigo_puesto = forms.ModelChoiceField(
        queryset=PuestoDeTrabajo.objects.all().order_by('nombre'),
        required=False,
        label="Código de Puesto Oficial"
    )
    
    es_empleado_activo = forms.BooleanField(
        label="¿Es empleado activo?",
        required=False,
    )

    class Meta(UserChangeForm.Meta):
        model = Empleado
        fields = UserCreationForm.Meta.fields + (
            'dni', 'sexo', 'sede', 'estado', 'departamento', 'area', 'puesto', 'codigo_puesto',
            'es_empleado_activo',
        )
        widgets = {
            'password1': forms.PasswordInput(),
            'password2': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.all().order_by('nombre')
        self.fields['area'].queryset = Area.objects.all().order_by('departamento__nombre', 'nombre')
        self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.all().order_by('nombre')

        # Lógica para inicializar campos al editar (aquí SÍ aplica)
        if self.instance and self.instance.pk:
            # Filtra los querysets de 'area' y 'codigo_puesto' basándose en el departamento del empleado.
            # Se asume que el 'departamento' y 'area' del Empleado son los datos correctos
            # que deben usarse para filtrar los campos relacionados.
            if self.instance.departamento:
                self.fields['area'].queryset = Area.objects.filter(
                    departamento=self.instance.departamento
                ).order_by('nombre')
                self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.filter(
                    departamento=self.instance.departamento
                ).order_by('nombre')
            else:
                self.fields['area'].queryset = Area.objects.none()
                self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.none()

            # Establece los valores iniciales de los campos
            if self.instance.codigo_puesto:
                self.fields['codigo_puesto'].initial = self.instance.codigo_puesto
            
            if hasattr(self.instance, 'es_empleado_activo'):
                self.fields['es_empleado_activo'].initial = self.instance.es_empleado_activo

    def clean(self):
        cleaned_data = super().clean()
        departamento = cleaned_data.get('departamento')
        area = cleaned_data.get('area')
        codigo_puesto = cleaned_data.get('codigo_puesto')

        # Si se selecciona un área y un departamento, validar que el área pertenece al departamento.
        if area and departamento and area.departamento != departamento:
            self.add_error('area', "El área seleccionada no pertenece al departamento elegido.")

        # Si se selecciona un puesto de trabajo y un departamento, validar que el puesto pertenece a ese departamento.
        if codigo_puesto and departamento and codigo_puesto.departamento != departamento:
            self.add_error('codigo_puesto', "El puesto de trabajo seleccionado no pertenece al departamento elegido.")
            
        return cleaned_data
    
class EmpleadoProfileForm(UserChangeForm):
    puesto = forms.CharField(
        max_length=255,
        required=False,
        help_text="Título de puesto principal del empleado."
    )
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all().order_by('nombre'),
        required=False,
        help_text="Departamento al que pertenece el puesto del empleado."
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all().order_by('departamento__nombre', 'nombre'),
        required=False,
        help_text="Área del departamento a la que pertenece el puesto del empleado."
    )
    
    sexo = forms.ChoiceField(
        choices=Empleado.SEXO_CHOICES,
        required=False,
        help_text="Género del empleado."
    )
    sede = forms.ChoiceField(
        choices=Empleado.SEDE_CHOICES,
        required=False,
        help_text="Sede principal de trabajo del empleado."
    )
    estado = forms.ChoiceField(
        choices=Empleado.ESTADO_EMPLEADO_CHOICES,
        required=False,
        help_text="Estado actual del empleado en la empresa."
    )
    codigo_puesto = forms.ModelChoiceField(
        queryset=PuestoDeTrabajo.objects.all().order_by('nombre'),
        required=False,
        help_text="Puesto de trabajo oficial asignado a este empleado."
    )
    es_empleado_activo = forms.BooleanField(
        label="¿Es empleado activo?",
        required=False,
        help_text="Marca si el empleado está actualmente activo en la empresa."
    )

    class Meta(UserChangeForm.Meta):
        model = Empleado
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'dni', 'sexo', 'sede', 'estado', 'departamento', 'area', 'puesto', 'codigo_puesto', 'es_empleado_activo',
            'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.all().order_by('nombre')
        self.fields['area'].queryset = Area.objects.all().order_by('departamento__nombre', 'nombre')
        self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.all().order_by('nombre') # MODIFICADO

        # Filtra los querysets de 'area' y 'codigo_puesto' basándose en el departamento del empleado.
        if self.instance and self.instance.pk and self.instance.departamento:
            self.fields['area'].queryset = Area.objects.filter(
                departamento=self.instance.departamento
            ).order_by('nombre')
            self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.filter(
                departamento=self.instance.departamento
            ).order_by('nombre')
        else:
            self.fields['area'].queryset = Area.objects.none()
            self.fields['codigo_puesto'].queryset = PuestoDeTrabajo.objects.none()

        # Establece los valores iniciales para los campos
        if self.instance and self.instance.pk:
            if self.instance.codigo_puesto:
                self.fields['codigo_puesto'].initial = self.instance.codigo_puesto
            
            if hasattr(self.instance, 'es_empleado_activo'):
                self.fields['es_empleado_activo'].initial = self.instance.es_empleado_activo

    def clean(self):
        cleaned_data = super().clean()
        departamento = cleaned_data.get('departamento')
        area = cleaned_data.get('area')
        codigo_puesto = cleaned_data.get('codigo_puesto')

        # Si se selecciona un área y un departamento, validar que el área pertenece al departamento.
        if area and departamento and area.departamento != departamento:
            self.add_error('area', "El área seleccionada no pertenece al departamento elegido.")

        # Si se selecciona un puesto de trabajo y un departamento, validar que el puesto pertenece a ese departamento.
        if codigo_puesto and departamento and codigo_puesto.departamento != departamento:
            self.add_error('codigo_puesto', "El puesto de trabajo seleccionado no pertenece al departamento elegido.")
            
        return cleaned_data

# Formularios para otros modelos

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Por defecto, si es un nuevo departamento o si el coordinador no está asignado,
        # o si el coordinador existente no tiene departamento asignado,
        # mostrar todos los empleados que son staff.
        self.fields['coordinador'].queryset = Empleado.objects.filter(is_staff=True).order_by('first_name', 'last_name')

        # Si estamos EDITANDO un departamento existente:
        if self.instance and self.instance.pk:
            # Filtra el queryset para que solo muestre empleados STAFF que pertenecen a este departamento.
            # Nota: 'departamento' es el nuevo ForeignKey directo en el modelo Empleado
            # También incluye el coordinador actualmente seleccionado, incluso si no cumple el filtro
            # (esto evita que el campo aparezca vacío si el coordinador actual no está en el queryset filtrado).
            current_coordinador = self.instance.coordinador
            
            # Filtra por empleados que son staff Y pertenecen a este departamento
            filtered_queryset = Empleado.objects.filter(
                is_staff=True,
                departamento=self.instance # Filtra por el departamento actual (self.instance)
            ).order_by('first_name', 'last_name')
            
            # Si hay un coordinador actualmente asignado y no está en el queryset filtrado, añádelo
            if current_coordinador and current_coordinador not in filtered_queryset:
                self.fields['coordinador'].queryset = filtered_queryset | Empleado.objects.filter(pk=current_coordinador.pk)
            else:
                self.fields['coordinador'].queryset = filtered_queryset

    # Agrega una validación para asegurar que el coordinador seleccionado realmente pertenece a este departamento
    def clean_coordinador(self):
        coordinador = self.cleaned_data.get('coordinador')
        
        # Esta validación solo tiene sentido si estamos editando un departamento existente (self.instance.pk)
        # Y si se ha seleccionado un coordinador, Y si ese coordinador tiene un departamento asignado,
        # Y si ese departamento es diferente al departamento actual que estamos editando.
        if self.instance and self.instance.pk and coordinador:
            if coordinador.departamento != self.instance:
                raise forms.ValidationError(
                    "El coordinador seleccionado debe pertenecer a este departamento."
                )
        return coordinador

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento'].queryset = Departamento.objects.all().order_by('nombre')


class PuestoDeTrabajoForm(forms.ModelForm):
    class Meta:
        model = PuestoDeTrabajo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area'].queryset = Area.objects.all().order_by('nombre')


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = '__all__'


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = '__all__'
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin_prevista': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin_real': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['jefe_proyecto'].queryset = Empleado.objects.all().order_by('first_name', 'last_name')


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        exclude = ['codigo', 'origen']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['departamento_solicitante'].queryset = Departamento.objects.all().order_by('nombre')
        self.fields['proveedor'].queryset = Proveedor.objects.all().order_by('nombre')
        self.fields['proyecto'].queryset = Proyecto.objects.all().order_by('nombre')

    def save(self, commit=True):
        curso = super().save(commit=False) # Obtenemos la instancia sin guardar aún

        # Si el curso es nuevo (no tiene PK), asignamos plazas_disponibles
        # O puedes usar otra lógica si también quieres restablecerlas al editar en ciertos casos
        if not curso.pk:
            curso.plazas_disponibles = curso.plazas_totales

        if commit:
            curso.save()
        return curso
    
class SolicitudCursoForm(forms.ModelForm):
    class Meta:
        model = SolicitudCurso
        fields = [
            'titulo_curso_solicitado',
            'objetivo_curso',
            'justificacion_necesidad',
            'numero_participantes_estimado',
            'temas_contenidos_clave',
            'formato_preferido',
            'duracion_estimada',
            'fechas_horarios_preferidos',
            'caracter_formacion',
            'comentarios_adicionales',
        ]
        # Estos campos son excluidos porque los asigna la vista automáticamente
        exclude = ('solicitante', 'departamento_solicitante', 'fecha_solicitud', 'estado')

        labels = {
            'titulo_curso_solicitado': 'Título Propuesto del Curso',
            'objetivo_curso': 'Objetivo Principal del Curso',
            'justificacion_necesidad': 'Justificación de la Necesidad',
            'numero_participantes_estimado': 'Nº Estimado de Participantes',
            'temas_contenidos_clave': 'Temas / Contenidos Clave',
            'formato_preferido': 'Formato Preferido',
            'duracion_estimada': 'Duración Estimada',
            'fechas_horarios_preferidos': 'Fechas y Horarios Preferidos',
            'caracter_formacion': 'Carácter de la Formación',
            'comentarios_adicionales': 'Comentarios Adicionales',
        }
        help_texts = {
            'numero_participantes_estimado': '¿Cuántos empleados de tu equipo/departamento lo necesitarían?',
            'temas_contenidos_clave': 'Ej: "Fundamentos de Python", "Gestión de Proyectos Ágil", "Técnicas de Negociación".',
            'duracion_estimada': 'Ej: "8 horas", "2 días", "3 sesiones de 2h", "A lo largo de un mes".',
            'fechas_horarios_preferidos': 'Ej: "Primera quincena de julio", "Solo por las mañanas", "Martes y Jueves por la tarde".',
            'caracter_formacion': 'Clasifica la necesidad para ayudar en la priorización.',
        }
        widgets = {
            'formato_preferido': forms.Select(attrs={'class': 'form-select-modern'}),
            'caracter_formacion': forms.Select(attrs={'class': 'form-select-modern'}),
            'objetivo_curso': forms.Textarea(attrs={'rows': 3}), 
            'justificacion_necesidad': forms.Textarea(attrs={'rows': 3}), 
            'temas_contenidos_clave': forms.Textarea(attrs={'rows': 4}),
            'comentarios_adicionales': forms.Textarea(attrs={'rows': 3}), 
        }

    def __init__(self, *args, **kwargs):
        # Extrae el argumento 'solicitante' de kwargs antes de pasarlo a super().__init__
        self.solicitante = kwargs.pop('solicitante', None)
        super().__init__(*args, **kwargs)


class ParticipacionForm(forms.ModelForm):
    class Meta:
        model = Participacion
        fields = '__all__'
        widgets = {
            'fecha_certificado': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.all().order_by('first_name', 'last_name')
        self.fields['curso'].queryset = Curso.objects.all().order_by('nombre')


#títulos y certificaciones

class TitulacionForm(forms.ModelForm):
    class Meta:
        model = Titulacion
        fields = [
            'nombre',
            'tipo_titulacion',
            'institucion_emisora',
            'fecha_obtencion',
            'fecha_caducidad', # Puede ser nulo
            'documento_adjunto', # Para subir el PDF/imagen del certificado
            'curso_relacionado', # Si quieres que el empleado pueda enlazarlo a un curso interno
            'nivel_idioma',      # Si aplica
        ]
        # Campos que no deben ser manipulados por el empleado en este formulario
        exclude = ('empleado', 'estado', 'motivo_rechazo', 'created_at', 'updated_at')
        widgets = {
            'fecha_obtencion': forms.DateInput(attrs={'type': 'date'}),
            'fecha_caducidad': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'nombre': 'Nombre de la Titulación/Certificación',
            'tipo_titulacion': 'Tipo',
            'institucion_emisora': 'Institución Emisora',
            'fecha_obtencion': 'Fecha de Obtención',
            'fecha_caducidad': 'Fecha de Caducidad (si aplica)',
            'documento_adjunto': 'Documento de Soporte (PDF, Imagen)',
            'curso_relacionado': 'Curso Interno Relacionado',
            'nivel_idioma': 'Nivel de Idioma',
        }
        help_texts = {
            'curso_relacionado': 'Si esta titulación corresponde a un curso interno de la empresa, selecciónalo.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso_relacionado'].queryset = Curso.objects.all().order_by('nombre')
        
        
class RequisitoPuestoFormacionForm(forms.ModelForm):
    class Meta:
        model = RequisitoPuestoFormacion
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['puesto'].queryset = PuestoDeTrabajo.objects.all().order_by('nombre')
        self.fields['curso'].queryset = Curso.objects.all().order_by('nombre')


class PreseleccionForm(forms.ModelForm):
    class Meta:
        model = Preseleccion
        exclude = ['creado_por']
        widgets = {
            'fecha_solicitud': forms.DateInput(attrs={'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.coordinador = kwargs.pop('coordinador', None) 
        super().__init__(*args, **kwargs)

        # Filtra el queryset de 'empleado' para mostrar solo empleados del departamento del coordinador
        if self.coordinador and self.coordinador.departamento:
            self.fields['empleado'].queryset = Empleado.objects.filter(
                departamento=self.coordinador.departamento
            ).order_by('last_name', 'first_name')
        else:
            # Si no hay coordinador o departamento, no mostrar empleados
            self.fields['empleado'].queryset = Empleado.objects.none() 

        # Filtra el queryset de 'curso' para mostrar solo cursos que no han acabado o no tienen fecha de fin
        self.fields['curso'].queryset = Curso.objects.filter(
            Q(fecha_fin__gte=datetime.date.today())
        ).order_by('nombre')

        # Si estamos editando una preselección existente, nos aseguramos de que el curso actual
        # de esa preselección esté disponible en el queryset, incluso si ya ha terminado.
        if self.instance.pk and self.instance.curso:
            current_course = self.instance.curso
            # Comprueba si el curso actual ya está en el queryset filtrado
            if not self.fields['curso'].queryset.filter(pk=current_course.pk).exists():
                self.fields['curso'].queryset |= Curso.objects.filter(pk=current_course.pk)
            self.fields['curso'].queryset = self.fields['curso'].queryset.distinct()

class AprobarParticipacionForm(forms.ModelForm):
    # Usamos un DateInput para que aparezca un selector de fecha en el navegador
    fecha_inicio_real = forms.DateField(
        label="Fecha de Inicio del Curso (Asignada por RRHH)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        input_formats=['%Y-%m-%d']
    )

    class Meta:
        model = Participacion
        fields = ['fecha_inicio_real']

    
    def clean_fecha_inicio_real(self):
        fecha = self.cleaned_data['fecha_inicio_real']

        # Si la fecha debe ser FUTURA:
        if fecha < timezone.localdate(): # o timezone.now().date()
            raise forms.ValidationError("La fecha de inicio no puede ser en el pasado.")
        
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha_inicio_real')
        return cleaned_data

class MarcarCompletadoForm(forms.ModelForm):
    nota_final = forms.CharField(
        label="Nota Final / Calificación",
        max_length=100,
        required=False # Puede que no todos los cursos tengan nota
    )
    certificado_obtenido = forms.BooleanField(
        label="¿Certificado Obtenido?",
        required=False, # Puede que no todos los cursos den certificado
        initial=False
    )
    fecha_certificado = forms.DateField(
        label="Fecha de Obtención del Certificado",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False # Opcional si no siempre hay certificado
    )
    fecha_caducidad_certificado = forms.DateField(
        label="Fecha de Caducidad del Certificado",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False # Opcional si no todos los certificados caducan
    )


    class Meta:
        model = Participacion
        fields = ['nota_final', 'certificado_obtenido', 'fecha_certificado', 'fecha_caducidad_certificado'] # Añadir 'certificado_url' si lo tienes
    
    def clean(self):
        cleaned_data = super().clean()
        certificado_obtenido = cleaned_data.get('certificado_obtenido')
        fecha_certificado = cleaned_data.get('fecha_certificado')
        fecha_caducidad_certificado = cleaned_data.get('fecha_caducidad_certificado')

        if certificado_obtenido and not fecha_certificado:
            raise forms.ValidationError(
                "Si el certificado ha sido obtenido, la fecha de obtención es obligatoria."
            )
        return cleaned_data

class EncuestaSatisfaccionForm(forms.ModelForm):
    # Campos que el usuario rellenará directamente
    # Usamos RadioSelect para la valoración 1-5 para que sea más visual
    opinion_contenido_curso = forms.TypedChoiceField(
        coerce=int,
        choices=EncuestaSatisfaccion.VALORACION_CHOICES,
        widget=forms.RadioSelect,
        label="Su opinión sobre el contenido del curso ha sido:",
        help_text="Valore del 1 (Mal) al 5 (Excelente)"
    )
    conocimientos_profesor = forms.TypedChoiceField(
        coerce=int,
        choices=EncuestaSatisfaccion.VALORACION_CHOICES,
        widget=forms.RadioSelect,
        label="Los conocimientos técnicos del profesor le han parecido:",
        help_text="Valore del 1 (Mal) al 5 (Excelente)"
    )
    gusto_general_curso = forms.TypedChoiceField(
        coerce=int,
        choices=EncuestaSatisfaccion.VALORACION_CHOICES,
        widget=forms.RadioSelect,
        label="En general, ¿le ha gustado el curso?:",
        help_text="Valore del 1 (Mal) al 5 (Excelente)"
    )
    mejora_conocimientos_carrera = forms.TypedChoiceField(
        coerce=int,
        choices=EncuestaSatisfaccion.VALORACION_CHOICES,
        widget=forms.RadioSelect,
        label="Con este curso he mejorado / ampliado mis conocimientos para progresar en mi carrera profesional:",
        help_text="Valore del 1 (Mal) al 5 (Excelente)"
    )
    adquisicion_habilidades_puesto = forms.TypedChoiceField(
        coerce=int,
        choices=EncuestaSatisfaccion.VALORACION_CHOICES,
        widget=forms.RadioSelect,
        label="Con este curso he adquirido nuevas habilidades / capacidades que puedo aplicar a mi puesto de trabajo:",
        help_text="Valore del 1 (Mal) al 5 (Excelente)"
    )

    class Meta:
        model = EncuestaSatisfaccion
        fields = [
            'opinion_contenido_curso',
            'conocimientos_profesor',
            'gusto_general_curso',
            'mejora_conocimientos_carrera',
            'adquisicion_habilidades_puesto',
            'sugerencias_observaciones'
        ]
        widgets = {
            'sugerencias_observaciones': forms.Textarea(attrs={'rows': 4}),
        }

class NotificacionForm(forms.ModelForm):
    class Meta:
        model = Notificacion
        fields = '__all__'
        widgets = {
            'fecha': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['usuario'].queryset = Empleado.objects.all().order_by('first_name', 'last_name')