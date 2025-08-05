# Sistema de Gestión de Formación

## Descripción del Proyecto

Este proyecto es un sistema web desarrollado con **Django** para la gestión integral de la formación dentro de una organización. Permite a los empleados solicitar cursos, a los administradores de RRHH y Formación gestionar estas solicitudes, organizar cursos, llevar un registro de participantes y sus certificaciones, y gestionar proveedores y titulaciones.

El objetivo principal es centralizar y optimizar los procesos relacionados con la capacitación del personal, facilitando la identificación de necesidades formativas, la planificación de cursos y el seguimiento del desarrollo profesional de los empleados.

---

## Características Principales

- **Solicitud de Cursos:** Los coordinadores pueden proponer y solicitar nuevas formaciones para sus equipos/departamentos.
- **Gestión de Solicitudes:** Roles de RRHH/Formación pueden revisar, aprobar, rechazar o poner en proceso las solicitudes de cursos.
- **Gestión de Cursos:** Creación, edición y administración de la oferta formativa (cursos, fechas, plazas, proveedores).
- **Gestión de Participantes:** Inscripción y seguimiento de empleados en cursos, registro de notas y emisión de certificados.
- **Gestión de Titulaciones:** Registro y seguimiento de titulaciones y certificaciones obtenidas por los empleados.
- **Gestión de Empleados:** Perfiles de empleados con su historial formativo.
- **Notificaciones:** Sistema de notificaciones internas para informar sobre el estado de las solicitudes y otras acciones relevantes.
- **Roles de Usuario:** Diferentes niveles de acceso y permisos (Coordinador, RRHH, Formación, Dirección, Administrador).

---

## Tecnologías Utilizadas

| Componente         | Tecnología / Herramienta                                     |
|--------------------|-------------------------------------------------------------|
| Backend            | Python 3.x, Django                                          |
| Base de Datos      | SQLite (desarrollo), PostgreSQL/MySQL (producción)          |
| Dependencias       | pip, requirements.txt                                       |
| Variables Entorno  | python-decouple                                             |
| Frontend           | HTML5, CSS3 (estilos personalizados), JavaScript (opcional) |
| Iconos             | Bootstrap Icons (o Font Awesome)                            |
| Formularios        | django-widget-tweaks, django-crispy-forms                   |

---

## Configuración del Entorno de Desarrollo

Sigue estos pasos para poner en marcha el proyecto en tu máquina local.

### 1. Clonar el Repositorio

```bash
git clone https://github.com/jmelian/GestionFormacion.git
cd GestionFormacion
```

### 2. Crear y Activar el Entorno Virtual

Es altamente recomendable usar un entorno virtual para aislar las dependencias de tu proyecto.

```bash
python -m venv venv
```

Activar el entorno virtual:

- Windows (Command Prompt):
    ```bash
    venv\Scripts\activate
    ```
- Windows (PowerShell):
    ```bash
    .\venv\Scripts\Activate.ps1
    ```
- macOS / Linux:
    ```bash
    source venv/bin/activate
    ```

### 3. Instalar Dependencias
Con el entorno virtual activado, instala todas las dependencias del proyecto usando `pip`:
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno (.env)
Crea un archivo llamado `.env` en la raíz de tu proyecto (al mismo nivel que manage.py).

Copia el siguiente contenido en tu archivo `.env` y reemplaza los valores de ejemplo con los tuyos:

```bash
# .env
# Este archivo NO se sube a GitHub. Contiene información sensible.

SECRET_KEY='tu_clave_secreta_generada_aqui_es_muy_larga_y_aleatoria'
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost # Separa por comas, sin espacios

# Si usas PostgreSQL/MySQL, descomenta y configura:
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=nombre_de_tu_bd
# DB_USER=usuario_bd
# DB_PASSWORD=contraseña_bd
# DB_HOST=localhost
# DB_PORT=5432

# Configuración de Email 
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.ejemplo.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=tu_email@ejemplo.com
# EMAIL_HOST_PASSWORD=tu_password_email
# DEFAULT_FROM_EMAIL=tu_email@ejemplo.com
```
Para `SECRET_KEY`: Puedes generar una clave segura ejecutando en tu terminal (con el entorno virtual activado):
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Base de Datos y Migraciones
Aplica las migraciones de la base de datos para crear las tablas necesarias:
```bash
python manage.py migrate
```

## Crear un Superusuario
Necesitarás un superusuario para acceder al panel de administración de Django:
```bash
python manage.py createsuperuser
```

Sigue las instrucciones en la terminal para crear tu usuario y contraseña.

Ejecutar el Servidor de Desarrollo
Una vez que todo esté configurado, puedes iniciar el servidor de desarrollo de Django:
```bash
python manage.py runserver
```

El servidor estará disponible en `http://127.0.0.1:8000/` (o la dirección que te indique la terminal).


## Configuración Inicial de la Aplicación
Para asegurar que tu aplicación tenga los grupos de usuarios y permisos necesarios desde el principio (ej. `RRHH`, `Formación`, `Coordinador`, `Dirección`), puedes cargar los datos iniciales proporcionados. Estos archivos definen la estructura de permisos y roles que la aplicación espera.

### Función de los archivos:

- `initial_groups.json`: Contiene la definición de los grupos de usuarios de Django (ej. 'RRHH', 'Formación').

- `initial_permissions.json`: Contiene la definición de los permisos de Django (ej. 'Can add curso', 'Can view empleado'). Estos permisos son generados automáticamente por Django al ejecutar _makemigrations_ y _migrate_, pero este archivo asegura que estén disponibles si se necesitan cargar explícitamente o para auditoría.

### Cómo cargar los datos iniciales:

Asegúrate de que los archivos `initial_groups.json` y `initial_permissions.json` se encuentren en la raíz de tu proyecto o en la carpeta fixtures de una de tus aplicaciones (ej. formacion/fixtures/).

```bash
# Carga los grupos de usuarios
python manage.py loaddata initial_groups.json

# Carga los permisos (si los necesitas cargar explícitamente, aunque migrate suele crearlos)
python manage.py loaddata initial_permissions.json
```

>**Nota**: Estos archivos se pueden generar usando el comando _dumpdata_ de Django. Por ejemplo: `python manage.py dumpdata auth.Group --indent 2 > initial_groups.json`. Si encuentras problemas de codificación al generarlos, especialmente en Windows, puedes usar ´export PYTHONIOENCODING=utf-8´ antes del comando dumpdata.

## Acceso al Panel de Administración
Puedes acceder al panel de administración de Django en:
`http://127.0.0.1:8000/admin/`

Usa las credenciales del superusuario que creaste.


## Licencia
Este proyecto está bajo la [Licencia Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0). Consulta el archivo `LICENSE` para más detalles.
