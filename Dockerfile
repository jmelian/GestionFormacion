# Usa una imagen base oficial de Python en la versión Alpine,
# que es ligera y eficiente.
FROM python:3.13-alpine

# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Instala las dependencias de sistema necesarias para compilar ciertos
# paquetes de Python (como `psycopg2` para PostgreSQL).
RUN apk add --no-cache postgresql-dev build-base

# Copia el archivo de requisitos primero. Esto permite a Docker usar
# su caché para evitar reinstalar si `requirements.txt` no cambia.
COPY requirements.txt .

# Instala todas las dependencias de Python.
# Asegúrate de que `gunicorn` esté en tu archivo `requirements.txt`.
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código de la aplicación.
COPY . .

# Crea un usuario no-root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Expone el puerto 8000 para que el contenedor pueda recibir tráfico externo.
EXPOSE 8000

# El comando principal que se ejecutará al iniciar el contenedor.
# Inicia el servidor Gunicorn.
CMD ["gunicorn", "formacion_demo.wsgi:application", "--bind", "0.0.0.0:8000"]

