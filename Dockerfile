FROM python:3.13-slim

# Establecer la variable de entorno para que Python no almacene archivos .pyc en el contenedor,
# y para que los logs de salida no tengan buffering, haciéndolos visibles de inmediato.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo del contenedor.
WORKDIR /app

# Copia los archivos de requerimientos e instala las dependencias.
# Se hace en un paso separado para aprovechar el cache de Docker y
# evitar reinstalar si requirements.txt no cambia.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código del proyecto al contenedor.
COPY . /app/

# Exponemos el puerto 8000 para que la aplicación sea accesible desde el exterior del contenedor.
EXPOSE 8000

# Comando para ejecutar el servidor de desarrollo de Django cuando se inicie el contenedor.
# En producción, usar un servidor como Gunicorn.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]