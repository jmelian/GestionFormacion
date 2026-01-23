# ============================================================================
# ETAPA 1: Preparación de certificados (opcional)
# ============================================================================
FROM python:3.12-slim AS cert-stage

# Crear directorio para certificados
RUN mkdir -p /tmp/certs

# Copiar certificado LDAP solo si existe, de lo contrario crear archivo vacío
RUN if [ -f "./certs/ldap_ca_chain.pem" ]; then \
        cp ./certs/ldap_ca_chain.pem /tmp/certs/ldap_ca_chain.pem && \
        echo "Certificado LDAP copiado exitosamente"; \
    else \
        echo "Archivo de certificado LDAP no encontrado, creando archivo vacío" && \
        touch /tmp/certs/ldap_ca_chain.pem; \
    fi

# Verificar resultado
RUN echo "Verificando certificado..." && \
    if [ -s /tmp/certs/ldap_ca_chain.pem ]; then \
        echo "Certificado LDAP encontrado y copiado"; \
    else \
        echo "Certificado LDAP no encontrado, archivo vacío creado"; \
    fi && \
    ls -la /tmp/certs/

# ============================================================================
# ETAPA 2: Aplicación principal
# ============================================================================
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Instala las dependencias de sistema necesarias para compilar ciertos
# paquetes de Python (como `psycopg2` para PostgreSQL y `psutil`).
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-all \
    build-essential \
    libldap2-dev \
    libsasl2-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de requisitos primero. Esto permite a Docker usar
# su caché para evitar reinstalar si `requirements.txt` no cambia.
COPY requirements.txt .

# Instala todas las dependencias de Python.
# Asegúrate de que `gunicorn` esté en tu archivo `requirements.txt`.
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Copiar certificados desde la etapa de preparación
# ============================================================================
# Crear directorio para certificados
RUN mkdir -p /etc/ssl/certs/

# Copiar certificado desde la etapa anterior (puede ser vacío si no existía)
COPY --from=cert-stage /tmp/certs/ldap_ca_chain.pem /etc/ssl/certs/ldap_ca_chain.pem

# Verificar si el certificado existe y tiene contenido
RUN echo "Verificando certificado en ubicación final..." && \
    if [ -s /etc/ssl/certs/ldap_ca_chain.pem ]; then \
        echo "Certificado LDAP disponible en /etc/ssl/certs/ldap_ca_chain.pem"; \
    else \
        echo "Certificado LDAP no disponible (archivo vacío)"; \
    fi

# ============================================================================
# Aplicación principal
# ============================================================================

# Copia el resto de tu código de la aplicación.
COPY . .

# Expone el puerto 8000 para que el contenedor pueda recibir tráfico externo.
EXPOSE 8000

# El comando principal que se ejecutará al iniciar el contenedor.
# Será sobrescrito por docker-compose.
CMD ["gunicorn", "formacion_demo.wsgi:application", "--bind", "0.0.0.0:8000"]
