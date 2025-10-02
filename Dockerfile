# Usa una imagen base oficial de Python en la versión Alpine,
# que es ligera y eficiente.
#FROM python:3.13-alpine
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

# Copia el archivo de certificado del host al contenedor.
# Asume que el archivo se llama __contactel_es.ca-bundle y está en la carpeta ./certs/
# El directorio /etc/ssl/certs/ es la ubicación estándar en Alpine para los certificados de confianza.
#COPY ./certs/__contactel_es.ca-bundle /etc/ssl/certs/
COPY ./certs/ldap_ca_chain.pem /etc/ssl/certs/


# Copia el resto de tu código de la aplicación.
COPY . .

# Expone el puerto 8000 para que el contenedor pueda recibir tráfico externo.
EXPOSE 8000

# El comando principal que se ejecutará al iniciar el contenedor.
# Será sobrescrito por docker-compose.
CMD ["gunicorn", "formacion_demo.wsgi:application", "--bind", "0.0.0.0:8000"]
