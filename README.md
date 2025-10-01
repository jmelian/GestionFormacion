# Sistema de Gestión de Formación

## Descripción del Proyecto

Este proyecto es un sistema web desarrollado con **Django** para la gestión integral de la formación dentro de una organización. Permite a los empleados solicitar cursos, a los administradores de RRHH y Formación gestionar estas solicitudes, organizar cursos, llevar un registro de participantes y sus certificaciones, y gestionar proveedores y titulaciones.

El objetivo principal es centralizar y optimizar los procesos relacionados con la capacitación del personal, facilitando la identificación de necesidades formativas, la planificación de cursos y el seguimiento del desarrollo profesional de los empleados.

---

## Características Principales

- **Sistema de Solicitudes de Cursos:** Coordinadores pueden proponer formaciones detalladas con justificación completa y seguimiento de aprobación jerárquica.
- **Gestión Avanzada de Solicitudes:** RRHH/Formación/Dirección pueden revisar, aprobar, rechazar con motivos detallados y gestionar el flujo completo.
- **Gestión Integral de Cursos:** Creación completa con modalidades (Presencial/Online/Blended), proveedores, plazas limitadas, tipos de formación y resultados formales.
- **Sistema de Preselección:** Coordinadores pueden preseleccionar empleados con prioridades para optimizar la participación.
- **Gestión Completa de Participantes:** Inscripciones múltiples, estados detallados, seguimiento de progreso y marcado unificado de completado.
- **Sistema de Titulaciones MECES:** Gestión completa con niveles del Marco Español de Cualificaciones, validación RRHH y subida segura de documentos.
- **Encuestas de Satisfacción Detalladas:** Sistema completo con valoraciones numéricas, comentarios y análisis estadístico.
- **Notificaciones Contextuales:** Sistema automático de alertas con tipos diferenciados y enlaces de acción directa.
- **Dashboard Ejecutivo:** Panel con métricas, KPIs y visión global del estado de formación organizacional.
- **Sistema de Solicitudes de Cursos:** Coordinadores pueden proponer cursos con justificación completa y seguimiento de aprobación.
- **Reportes Avanzados:** Análisis detallado con estadísticas ITIL, satisfacción de cursos y métricas de formación.
- **Marcado Unificado de Completado:** Sistema inteligente que adapta el proceso según el tipo de resultado formal.
- **Roles y Permisos Granulares:** Sistema jerárquico con 6 roles (Empleado, Coordinador, RRHH, Formación, Dirección, Admin) y permisos específicos.

---

## Tecnologías Utilizadas

| Componente         | Tecnología / Herramienta                                    |
|--------------------|-------------------------------------------------------------|
| Backend            | Python 3.x, Django                                          |
| Servidor web       | Gunicorn, Nginx                                             |
| Orquestación       | Docker, Docker Compose                                      |
| Base de Datos      | PostgreSQL                                                  |
| Dependencias       | pip, requirements.txt                                       |
| Variables Entorno  | python-decouple                                             |
| Frontend           | HTML5, CSS3 (estilos personalizados), Bootstrap, JavaScript (opcional) |
| Iconos             | Bootstrap Icons                                             |
| Formularios        | django-widget-tweaks, django-crispy-forms                   |

---

## Configuración del Entorno de Desarrollo

Sigue estos pasos para poner en marcha el proyecto en tu máquina local.

### 1. Clonar el Repositorio

```bash
git clone https://github.com/jmelian/GestionFormacion.git
cd GestionFormacion
```

### 2. Configurar Variables de Entorno (.env)
Crea un archivo llamado `.env` en la raíz de tu proyecto (al mismo nivel que `docker-compose.yml`).

**Opción A: Usar la plantilla**
```bash
cp .env.example .env
```

**Opción B: Crear desde cero**
Copia el siguiente contenido en tu archivo `.env` y reemplaza los valores de ejemplo con los tuyos. Docker Compose usará estas variables para configurar los servicios.

**⚠️ Importante sobre seguridad:**
- El archivo `.env` contiene información sensible y ya está configurado para NO subirse a Git
- Usa `.env.example` como plantilla (este archivo SÍ se sube a Git)
- Nunca compartas tu archivo `.env` real

```bash
# .env - Sistema de Gestión de Formación v1.0
# Este archivo NO se sube a GitHub. Contiene información sensible.
# IMPORTANTE: No uses comillas alrededor de los valores

# === CONFIGURACIÓN BÁSICA DE DJANGO ===
SECRET_KEY=rqrvmu&ug-oynsefgwi5d9bw528(!$v0p)^+j#q6*d-ahmrj2$
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://localhost:8082,http://127.0.0.1:8082

# === CONFIGURACIÓN DE BASE DE DATOS ===
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=formacion_db
POSTGRES_USER=formacion_user
POSTGRES_PASSWORD=tu_password_seguro_aqui
DB_HOST_LOCAL=localhost
DB_HOST_DOCKER=db
DB_PORT=5432

# === CONFIGURACIÓN DE ZONA HORARIA ===
TIME_ZONE=Atlantic/Canary

# === CONFIGURACIÓN DE EMAIL ===
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password_o_password_normal
DEFAULT_FROM_EMAIL=tu_email@gmail.com
```

Para `SECRET_KEY`: Puedes generar una clave segura ejecutando en tu terminal (con el entorno virtual activado):
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Configuración de Email

Para Gmail, necesitas:
1. **EMAIL_HOST_USER**: Tu dirección de Gmail completa
2. **EMAIL_HOST_PASSWORD**: Una "contraseña de aplicación" (no tu contraseña normal)
   - Ve a https://myaccount.google.com/security
   - Activa la verificación en 2 pasos
   - Genera una contraseña de aplicación
3. **EMAIL_PORT**: 587 (TLS) o 465 (SSL)

### Variables Obligatorias vs Opcionales

**Obligatorias:**
- `SECRET_KEY`: Clave secreta de Django
- `DB_ENGINE`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_PORT`: Base de datos
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: Email
- `CSRF_TRUSTED_ORIGINS`: Orígenes confiables para CSRF

**Opcionales (con valores por defecto):**
- `DEBUG`: False por defecto
- `ALLOWED_HOSTS`: '127.0.0.1,localhost' por defecto
- `TIME_ZONE`: 'Atlantic/Canary' por defecto
- `DB_HOST_LOCAL`: 'localhost' por defecto
- `DB_HOST_DOCKER`: Solo para Docker

### Mejores Prácticas de Seguridad

1. **Nunca subas el archivo .env a Git**
2. **Usa contraseñas fuertes y únicas**
3. **Para producción:**
   - `DEBUG=False`
   - `SECRET_KEY` muy larga y aleatoria
   - `ALLOWED_HOSTS` específicos (no '*')
   - `SESSION_COOKIE_SECURE=True`
   - `CSRF_COOKIE_SECURE=True`
4. **Variables sensibles:**
   - Mantén `SECRET_KEY` y contraseñas seguras
   - Usa variables de entorno del sistema para producción
   - Considera usar servicios como AWS Secrets Manager o Azure Key Vault
### 3. Verificar Configuración del .env

Antes de iniciar el servidor, verifica que tu archivo `.env` esté correctamente configurado:

```bash
# Verificar que el archivo existe
ls -la .env

# Verificar sintaxis básica (no debe haber errores de formato)
python -c "import os; [print(f'{k}={v}') for k,v in os.environ.items() if k in open('.env').read()]" 2>/dev/null || echo "Archivo .env no encontrado o con errores"
```

### 4. Iniciar el servidor
```bash
docker-compose up -d --build
```

### 5. Base de Datos y Migraciones
Aplica las migraciones de la base de datos para crear las tablas necesarias en el contenedor de PostgreSQL:
```bash
docker-compose exec web python manage.py migrate
```

### 6. Crear un Superusuario
Necesitarás un superusuario para acceder al panel de administración de Django:
```bash
docker-compose exec web python manage.py createsuperuser
```

### 7. Configuración Inicial de la Aplicación
Para asegurar que tu aplicación tenga los grupos de usuarios y permisos necesarios desde el principio (ej. `RRHH`, `Formación`, `Coordinador`, `Dirección`, `Empleado`), puedes cargar los datos iniciales proporcionados. Estos archivos definen la estructura de permisos y roles que la aplicación espera.

#### Función de los archivos:

- `initial_groups.json`: Contiene la definición de los grupos de usuarios de Django (ej. 'RRHH', 'Formación').

- `initial_permissions.json`: Contiene la definición de los permisos de Django (ej. 'Can add curso', 'Can view empleado'). Estos permisos son generados automáticamente por Django al ejecutar _makemigrations_ y _migrate_, pero este archivo asegura que estén disponibles si se necesitan cargar explícitamente o para auditoría.

#### Cómo cargar los datos iniciales:

Asegúrate de que los archivos `initial_groups.json` y `initial_permissions.json` se encuentren en la raíz de tu proyecto o en la carpeta fixtures de una de tus aplicaciones (ej. formacion/fixtures/).

```bash
# Carga los grupos de usuarios
docker-compose exec web python manage.py loaddata initial_groups.json

# Carga los permisos (si los necesitas cargar explícitamente, aunque migrate suele crearlos)
docker-compose exec web python manage.py loaddata initial_permissions.json
```

>**Nota**: Estos archivos se pueden generar usando el comando _dumpdata_ de Django. Por ejemplo: `exec web python manage.py dumpdata auth.Group --indent 2 > initial_groups.json`. Si encuentras problemas de codificación al generarlos, especialmente en Windows, puedes usar ´export PYTHONIOENCODING=utf-8´ antes del comando dumpdata.

## Ejecución del Proyecto
Con todos los pasos anteriores completados, tu proyecto ya debería estar en ejecución. Simplemente usa docker-compose up para iniciar todos los servicios:
```bash
docker-compose up
```
Tu proyecto estará disponible en `http://localhost:8082/formacion` y el servidor Nginx se encargará de dirigir el tráfico a tu aplicación. Si necesitas detener los servicios, usa:
```bash
docker-compose down
```

## Acceso al Panel de Administración
Puedes acceder al panel de administración de Django en:
`http://localhost:8082/admin/`

Usa las credenciales del superusuario que creaste.

## Backup

### Generar un backup de los datos
```bash
docker-compose exec web sh -c "python manage.py dumpdata --indent 2 > /app/datos/backup_temp.json"
```
> NOTA: El archivo queda dentro del contenedor y no se corrompe al pasar a la terminal. Para copiarlo:  `docker cp django_app:/app/datos/backup_temp.json ./backup_temp.json` 

### Restaurar un backup de los datos
```bash
docker-compose exec web python manage.py loaddata backup_temp.json
```

## Verificación de Instalación

Después de completar todos los pasos, verifica que todo funciona correctamente:

1. **Acceder a la aplicación**: `http://localhost:8082/formacion`
2. **Panel de administración**: `http://localhost:8082/admin`
3. **Base de datos**: Verificar que las tablas se crearon correctamente
4. **Email**: Probar envío de emails desde el sistema
5. **Logs**: Revisar que no hay errores en los logs de Docker

### Comandos de Verificación

```bash
# Ver estado de contenedores
docker-compose ps

# Ver logs de la aplicación
docker-compose logs web

# Ver logs de la base de datos
docker-compose logs db

# Acceder a PostgreSQL
docker-compose exec db psql -U formacion_user -d formacion_db

# Verificar migraciones aplicadas
docker-compose exec web python manage.py showmigrations
```

## 📖 Documentación

- **[📋 Documentación Técnica Completa](PROJECT_DOCUMENTATION.md)** - Arquitectura, funcionalidades detalladas, modelos de datos y API
- **[🚀 Guía de Instalación](GUIA_INSTALACION.md)** - Instalación avanzada y configuración de producción
- **[👥 Guía del Usuario](GUIA_USUARIO.md)** - Manual completo para usuarios finales
- **[🔧 Documentación API](DOCUMENTACION_API.md)** - Referencia técnica de modelos y vistas
- **[📝 Archivo de Configuración](.env.example)** - Plantilla completa de variables de entorno
- **[✅ Lista de Tareas](TODO.txt)** - Estado del proyecto y mejoras planificadas

## Licencia
Este proyecto está bajo la [Licencia Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0). Consulta el archivo `LICENSE` para más detalles.

---

**Versión**: 1.1
**Última actualización**: 2025-10-01
**Autor**: Sistema de Documentación Automática
