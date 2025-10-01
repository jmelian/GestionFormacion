# Documentación Técnica de la API

## Modelos de Datos

### 1. Empleado (Employee)

**Herencia**: `AbstractUser` de Django

**Campos principales**:
- `dni`: Número de identificación (único)
- `sexo`: Género (Masculino/Femenino/Otro)
- `sede`: Sede de trabajo (TF/Remoto/GC)
- `estado`: Estado del empleado (Activo/Baja/Baja médica/Vacaciones)
- `departamento`: Relación con Departamento
- `area`: Relación con Área
- `puesto`: Puesto de trabajo (texto libre)
- `codigo_puesto`: Relación con PuestoDeTrabajo

**Métodos importantes**:
- `get_full_name()`: Nombre completo
- `departamento_actual`: Propiedad que determina el departamento actual
- `area_actual`: Propiedad que determina el área actual
- Propiedades de rol: `is_rrhh`, `is_formacion`, `is_coordinador`, etc.

### 2. Departamento (Department)

**Campos principales**:
- `nombre`: Nombre del departamento (único)
- `descripcion`: Descripción detallada
- `coordinador`: Empleado coordinador del departamento

**Relaciones**:
- `areas`: Áreas pertenecientes al departamento
- `empleados`: Empleados del departamento

### 3. Área (Area)

**Campos principales**:
- `nombre`: Nombre del área
- `departamento`: Departamento al que pertenece
- `descripcion`: Descripción del área

**Restricciones**:
- `unique_together = ('nombre', 'departamento')`

### 4. PuestoDeTrabajo (JobPosition)

**Campos principales**:
- `nombre`: Nombre del puesto
- `codigo`: Código identificador único
- `departamento`: Departamento del puesto
- `descripcion`: Descripción de responsabilidades

### 5. Curso (Course)

**Campos principales**:
- `nombre`: Nombre del curso
- `contenido`: Descripción detallada
- `tipo`: Tipo de curso (Onboarding, Refuerzo, Técnico, etc.)
- `modalidad`: Modalidad (Presencial/Online/Mixta)
- `duracion_horas`: Duración en horas
- `fecha_inicio`/`fecha_fin`: Fechas del curso
- `plazas_totales`/`plazas_disponibles`: Control de capacidad
- `proveedor`: Proveedor externo (opcional)
- `es_obligatorio`: Indica si es obligatorio

**Métodos importantes**:
- `save()`: Actualiza plazas_disponibles al crear

### 6. Participacion (Participation)

**Campos principales**:
- `empleado`: Empleado participante
- `curso`: Curso al que se participa
- `estado`: Estado de la participación
- `nota_final`: Calificación final
- `certificado_obtenido`: Si se obtuvo certificado
- `fecha_certificado`: Fecha de obtención
- `fecha_inicio_real`/`fecha_fin_real`: Fechas reales

**Propiedades importantes**:
- `puede_ser_cancelada`: Verifica si puede cancelarse
- `encuesta_rellenada`: Si tiene encuesta de satisfacción
- `completado_con_datos_finales`: Si está completo con datos

### 7. Titulacion (Certification)

**Campos principales**:
- `empleado`: Empleado titular
- `nombre`: Nombre de la titulación
- `tipo_titulacion`: Tipo (Grado, Máster, Doctorado, etc.)
- `institucion_emisora`: Institución que la emite
- `fecha_obtencion`: Fecha de obtención
- `estado`: Estado (Pendiente/Aprobado/Rechazado)
- `nivel_meces`: Nivel MECES
- `nivel_idioma`: Nivel de idioma (si aplica)

**Métodos importantes**:
- `is_pending()`, `is_approved()`, `is_rejected()`

### 8. Proveedor (Provider)

**Campos principales**:
- `nombre`: Nombre del proveedor (único)
- `email`: Correo de contacto
- `telefono`: Teléfono de contacto
- `web`: Sitio web
- `direccion`: Dirección física

### 9. SolicitudCurso (CourseRequest)

**Campos principales**:
- `solicitante`: Empleado que solicita
- `titulo_curso_solicitado`: Título del curso
- `objetivo_curso`: Objetivo del curso
- `numero_participantes_estimado`: Número estimado
- `estado`: Estado de la solicitud
- `departamento_solicitante`: Departamento solicitante
- `caracter_formacion`: Carácter de la formación (urgente, planificado, etc.)
- `comentarios_adicionales`: Comentarios adicionales
- `motivo_rechazo`: Motivo del rechazo si aplica

### 10. EncuestaSatisfaccion (Survey)

**Campos principales**:
- `participacion`: Participación relacionada
- `empleado`: Empleado que responde
- `opinion_contenido_curso`: Valoración contenido (1-5)
- `conocimientos_profesor`: Valoración profesor (1-5)
- `gusto_general_curso`: Valoración general (1-5)
- `mejora_conocimientos_carrera`: Mejora conocimientos (1-5)
- `adquisicion_habilidades_puesto`: Adquisición habilidades (1-5)
- `sugerencias_observaciones`: Comentarios abiertos

### 10. Notificacion (Notification)

**Campos principales**:
- `usuario`: Usuario destinatario
- `mensaje`: Contenido del mensaje
- `tipo`: Tipo (info/success/warning/error)
- `leida`: Estado de lectura
- `url`: URL relacionada (opcional)

## Vistas Principales

### Vistas de Autenticación

#### `custom_logout(request)`
- **Función**: Cierra la sesión del usuario
- **Decoradores**: `@login_required`
- **Redirección**: A página de login

### Vistas de Dashboard

#### `DashboardView` (Class-Based View)
- **Template**: `formacion/dashboard.html`
- **Contexto**: Roles del usuario, número de notificaciones
- **Funcionalidad**: Panel principal con información del usuario

#### `NotificacionesListView` (Class-Based View)
- **Template**: `formacion/notificaciones.html`
- **Funcionalidad**: Lista de notificaciones del usuario
- **Paginación**: 20 notificaciones por página

### Vistas de Cursos

#### `formacion_planificada(request)`
- **Función**: Muestra cursos planificados con filtros
- **Filtros**: Palabra clave, cursos finalizados
- **Ordenación**: Por fecha, nombre, duración, etc.
- **Paginación**: Configurable

#### `mis_cursos(request)`
- **Función**: Cursos del usuario actual
- **Filtros**: Por estado de participación
- **Ordenación**: Por fecha de inicio

#### `estado_cursos(request)`
- **Función**: Estado general de todos los cursos
- **Permisos**: RRHH, Formación, Dirección, Coordinador
- **Filtros**: Mostrar cursos terminados
- **Estadísticas**: Participantes por estado

### Vistas de Gestión de Empleados

#### `empleados_con_formacion(request)`
- **Función**: Lista de empleados con formación
- **Filtros**: Por departamento, palabra clave
- **Anotaciones**: Número de participaciones y titulaciones
- **Paginación**: 10 empleados por página

#### `empleado_formacion_detalle(request, empleado_id)`
- **Función**: Detalle de formación de un empleado específico
- **Permisos**: RRHH, Formación, Dirección, Admin
- **Información**: Participaciones y titulaciones

### Vistas de Titulaciones

#### `MisTitulacionesListView` (Class-Based View)
- **Template**: `formacion/mis_titulaciones_list.html`
- **Funcionalidad**: Lista de titulaciones del usuario
- **Ordenación**: Por fecha de obtención descendente

#### `MiTitulacionCreateView` (Class-Based View)
- **Template**: `formacion/mi_titulacion_form.html`
- **Funcionalidad**: Crear nueva titulación
- **Validación**: Asignación automática de nivel MECES

#### `MiTitulacionUpdateView` (Class-Based View)
- **Template**: `formacion/mi_titulaciones_form.html`
- **Permisos**: Solo el propietario, estado pendiente/rechazado
- **Funcionalidad**: Editar titulación existente

### Vistas de Solicitudes

#### `SolicitudCursoCreateView` (Class-Based View)
- **Template**: `formacion/solicitud_curso_form.html`
- **Permisos**: Solo coordinadores
- **Funcionalidad**: Crear solicitud de curso
- **Notificaciones**: Automáticas a RRHH/Formación/Dirección

#### `SolicitudesCursoGestionListView` (Class-Based View)
- **Template**: `formacion/solicitudes_curso_gestion_list.html`
- **Permisos**: Formación o Dirección
- **Estados**: Pendiente, Aprobada, En Proceso

### Vistas de Participación

#### `cancelar_participacion(request, participacion_id)`
- **Función**: Cancelar participación en curso
- **Validaciones**: Estado del curso, permisos del usuario
- **Notificaciones**: Al empleado y coordinador

#### `marcar_completado_unificado(request, participacion_id)`
- **Función**: Marcar participación como completada
- **Lógica**: Diferente según resultado formal del curso
- **Notificaciones**: Automáticas al completar

### Vistas de Encuestas

#### `encuesta_satisfaccion(request, participacion_id)`
- **Función**: Rellenar encuesta de satisfacción
- **Validaciones**: Curso completado, encuesta no existente
- **Campos**: Valoración contenido, profesor, eficacia

#### `reports_view(request)`
- **Función**: Mostrar reportes avanzados con gráficos
- **Permisos**: Acceso general con métricas específicas por rol
- **Características**: Dashboard con ITIL, satisfacción, formación por departamento
- **Filtros**: Por año seleccionado

#### `marcar_completado_unificado(request, participacion_id)`
- **Función**: Marcar participación como completada de forma unificada
- **Lógica**: Diferente según resultado formal del curso
- **Validaciones**: Permisos del usuario, estado de la participación

## URLs y Rutas

### Patrón de URLs

```python
urlpatterns = [
    # Dashboard y autenticación
    path('', DashboardView.as_view(), name='dashboard'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),

    # Empleados
    path('empleados/', empleado_list_view, name='empleado_list'),
    path('empleados-con-formacion/', empleados_con_formacion, name='empleados_con_formacion'),

    # Cursos
    path('mis-cursos/', mis_cursos, name='mis_cursos'),
    path('formacion_planificada/', formacion_planificada, name='formacion_planificada'),
    path('estado-cursos/', estado_cursos, name='estado_cursos'),

    # Titulaciones
    path('perfil/titulaciones/', mis_titulaciones_list, name='mis_titulaciones_list'),
    path('perfil/titulaciones/add/', mi_titulacion_create, name='mi_titulacion_create'),

    # Solicitudes
    path('solicitudes-gestion/', solicitudes_curso_gestion_list, name='solicitudes_curso_gestion'),

    # Notificaciones
    path('notificaciones/', NotificacionesListView.as_view(), name='ver_notificaciones'),
]
```

## Formularios

### Formularios Principales

#### `EmpleadoCreationForm`
- **Modelo**: Empleado
- **Campos**: username, email, password, información personal
- **Validaciones**: Unicidad de DNI, formato de email

#### `CursoForm`
- **Modelo**: Curso
- **Campos**: Todos los campos del modelo
- **Validaciones**: Fechas coherentes, plazas positivas

#### `TitulacionForm`
- **Modelo**: Titulacion
- **Campos**: Información de la titulación
- **Validaciones**: Fecha de obtención no futura

#### `SolicitudCursoForm`
- **Modelo**: SolicitudCurso
- **Campos**: Información de la solicitud
- **Validaciones**: Campos requeridos según tipo

## Configuración de Base de Datos

### Modelo de Datos Relacional

```
Empleado --1:N-- Participacion --N:1-- Curso
Empleado --1:N-- Titulacion
Empleado --N:1-- Departamento
Empleado --N:1-- Area
Departamento --1:N-- Area
Curso --N:1-- Proveedor
Participacion --1:1-- EncuestaSatisfaccion
```

### Índices y Constraints

- **Unique Constraints**:
  - `(empleado, curso)` en Participacion
  - `(empleado, nombre)` en Titulacion
  - `(nombre, departamento)` en Area

- **Foreign Keys**:
  - Todas las relaciones con `on_delete` apropiado
  - `SET_NULL` para mantener integridad

## Seguridad y Permisos

### Grupos de Usuarios

1. **Empleado**: Acceso básico de lectura
2. **Coordinador**: Gestión de equipo departamental
3. **RRHH**: Validación y gestión de personal
4. **Formación**: Gestión de cursos y proveedores
5. **Dirección**: Visión global y aprobaciones

### Decoradores de Seguridad

```python
@login_required
@user_passes_test(es_rrhh)
def funcion_restringida(request):
    # Solo accesible para usuarios RRHH autenticados
    pass
```

### Validaciones de Negocio

- **Permisos por departamento**: Coordinadores solo ven su departamento
- **Estados de transición**: Validaciones de cambio de estado
- **Fechas coherentes**: Validación de lógica temporal
- **Capacidad de cursos**: Control de plazas disponibles

## Manejo de Errores

### Tipos de Errores

1. **Errores de Validación**: Formularios inválidos
2. **Errores de Permisos**: Acceso no autorizado
3. **Errores de Base de Datos**: IntegrityError, OperationalError
4. **Errores de Sistema**: Excepciones generales

### Manejo en Vistas

```python
try:
    # Código que puede fallar
    participacion.save()
except IntegrityError:
    messages.error(request, "Error de integridad de datos")
except Exception as e:
    logger.error(f"Error inesperado: {e}")
    messages.error(request, "Error inesperado")
```

## Logging

### Configuración de Logs

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'formacion': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

### Niveles de Log

- **DEBUG**: Información detallada para desarrollo
- **INFO**: Eventos normales del sistema
- **WARNING**: Situaciones que requieren atención
- **ERROR**: Errores que afectan la funcionalidad
- **CRITICAL**: Errores críticos del sistema

---

**Documentación Técnica - API**
**Versión**: 1.1
**Última actualización**: 2025-10-01