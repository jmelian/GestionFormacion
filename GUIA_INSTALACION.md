# Guía de Instalación y Despliegue

## Requisitos Previos

### Sistema Operativo
- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 10+
- **macOS**: 10.15+ (Catalina o superior)
- **Windows**: 10/11 con WSL2 recomendado

### Software Requerido
- **Docker**: Versión 20.10 o superior
- **Docker Compose**: Versión 2.0 o superior
- **Git**: Para clonar el repositorio
- **Python**: 3.9+ (solo para desarrollo local)

### Recursos del Sistema
- **RAM**: Mínimo 2GB, recomendado 4GB+
- **Espacio en Disco**: 2GB libres
- **CPU**: 2 núcleos mínimo

## Instalación con Docker (Recomendado)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/jmelian/GestionFormacion.git
cd GestionFormacion
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# .env
# Clave secreta de Django (generar una nueva para producción)
SECRET_KEY='tu_clave_secreta_muy_larga_y_aleatoria_aqui'

# Modo debug (False para producción)
DEBUG=False

# Hosts permitidos (separados por comas)
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com

# Zona horaria
TIME_ZONE=Europe/Madrid

# Configuración de Base de Datos
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=formacion_db
POSTGRES_USER=formacion_user
POSTGRES_PASSWORD=tu_password_seguro_aqui
DB_HOST_DOCKER=db
DB_HOST_LOCAL=localhost
DB_PORT=5432

# Configuración de Email (opcional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com
```

### 3. Generar Clave Secreta Segura

```bash
# Ejecutar en terminal con Python instalado
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Construir e Iniciar los Contenedores

```bash
# Construir las imágenes
docker-compose build

# Iniciar todos los servicios
docker-compose up -d

# Verificar que los contenedores están ejecutándose
docker-compose ps
```

### 5. Ejecutar Migraciones de Base de Datos

```bash
# Acceder al contenedor de la aplicación
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser
```

### 6. Cargar Datos Iniciales

```bash
# Cargar grupos de usuarios
docker-compose exec web python manage.py loaddata initial_groups.json

# Cargar permisos (opcional)
docker-compose exec web python manage.py loaddata initial_permissions.json
```

### 7. Verificar Instalación

Acceder a la aplicación en: `http://localhost:8082/formacion/`

## Instalación Local (Desarrollo)

### 1. Crear Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Linux/macOS:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Base de Datos PostgreSQL

```sql
-- Crear base de datos
CREATE DATABASE formacion_db;
CREATE USER formacion_user WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE formacion_db TO formacion_user;
```

### 4. Configurar Variables de Entorno

Crear archivo `.env` con la configuración local:

```bash
DEBUG=True
DB_HOST_LOCAL=localhost
# ... resto de variables
```

### 5. Ejecutar Migraciones

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Iniciar Servidor de Desarrollo

```bash
python manage.py runserver
```

Acceder en: `http://localhost:8000/formacion/`

## Configuración Avanzada

### Configuración de Nginx

El archivo `nginx/nginx.conf` incluye:

```nginx
upstream formacion_web {
    server web:8000;
}

server {
    listen 80;
    client_max_body_size 50M;

    location /static/ {
        alias /vol/web/staticfiles/;
    }

    location / {
        proxy_pass http://formacion_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Configuración de Docker Compose

```yaml
services:
  web:
    build: .
    command: sh -c "
      mkdir -p /vol/web/staticfiles /vol/web/media &&
      chmod -R 755 /vol/web &&
      python manage.py migrate &&
      python manage.py collectstatic --no-input &&
      gunicorn formacion_demo.wsgi:application --bind 0.0.0.0:8000"
    volumes:
      - formacion_static_volume:/vol/web/staticfiles
      - formacion_media_volume:/vol/web/media
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy

  nginx:
    build: ./nginx
    ports:
      - "8082:80"
    volumes:
      - formacion_static_volume:/vol/web/staticfiles
      - formacion_media_volume:/vol/web/media
    depends_on:
      - web

  db:
    image: postgres:17
    volumes:
      - formacion_postgres_data:/var/lib/postgresql/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Configuración de Producción

### 1. Configuración de Seguridad

```bash
# En .env para producción
DEBUG=False
SECRET_KEY=tu_clave_muy_segura
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
```

### 2. Configuración de SSL/HTTPS

```nginx
# En nginx.conf para producción
server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;

    # ... resto de configuración
}
```

### 3. Configuración de Base de Datos

```bash
# Variables de entorno para producción
POSTGRES_DB=formacion_prod
POSTGRES_USER=formacion_prod_user
POSTGRES_PASSWORD=contraseña_muy_segura
```

### 4. Backup de Base de Datos

```bash
# Backup
docker-compose exec db pg_dump -U formacion_user formacion_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar
docker-compose exec -T db psql -U formacion_user -d formacion_db < backup.sql
```

## Solución de Problemas

### Problemas Comunes

#### 1. Error de Conexión a Base de Datos

```bash
# Verificar estado de contenedores
docker-compose ps

# Ver logs de base de datos
docker-compose logs db

# Reiniciar servicios
docker-compose restart
```

#### 2. Error de Migraciones

```bash
# Resetear migraciones (CUIDADO: pierde datos)
docker-compose exec web python manage.py migrate --fake-initial
docker-compose exec web python manage.py migrate
```

#### 3. Error de Permisos de Archivos

```bash
# Corregir permisos en contenedores
docker-compose exec web chown -R www-data:www-data /vol/web/
```

#### 4. Error de Memoria

```bash
# Verificar uso de recursos
docker stats

# Aumentar límite de memoria en docker-compose.yml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 1G
```

### Logs de Depuración

```bash
# Ver logs de todos los servicios
docker-compose logs

# Ver logs de un servicio específico
docker-compose logs web

# Seguir logs en tiempo real
docker-compose logs -f web
```

## Comandos Útiles

### Gestión de Contenedores

```bash
# Detener servicios
docker-compose down

# Detener y eliminar volúmenes
docker-compose down -v

# Reconstruir imágenes
docker-compose build --no-cache

# Ver uso de recursos
docker stats
```

### Gestión de Base de Datos

```bash
# Acceder a PostgreSQL
docker-compose exec db psql -U formacion_user -d formacion_db

# Backup de datos
docker-compose exec web python manage.py dumpdata > backup.json

# Restaurar datos
docker-compose exec web python manage.py loaddata backup.json
```

### Gestión de Archivos Estáticos

```bash
# Recolectar archivos estáticos
docker-compose exec web python manage.py collectstatic --no-input

# Limpiar cache
docker-compose exec web python manage.py clear_cache
```

## Monitoreo y Mantenimiento

### Comandos de Monitoreo

```bash
# Ver estado de servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f

# Ver uso de disco
docker system df

# Limpiar imágenes no utilizadas
docker image prune -f
```

### Tareas de Mantenimiento

1. **Backup Regular**: Programar backups diarios de base de datos
2. **Actualización**: Mantener imágenes Docker actualizadas
3. **Monitoreo de Logs**: Revisar logs periódicamente
4. **Limpieza**: Eliminar contenedores e imágenes no utilizadas

## Variables de Entorno Completas

```bash
# Archivo .env completo
SECRET_KEY=tu_clave_secreta_muy_larga
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com
TIME_ZONE=Europe/Madrid

# Base de datos
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=formacion_db
POSTGRES_USER=formacion_user
POSTGRES_PASSWORD=tu_password_seguro
DB_HOST_DOCKER=db
DB_HOST_LOCAL=localhost
DB_PORT=5432

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com

# Seguridad adicional
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
```

---

**Guía de Instalación**
**Versión**: 1.3
**Última actualización**: 2025-10-02