# Usa la imagen base oficial de Nginx
FROM nginx:latest

# Copia tu archivo de configuración de Nginx
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Asegura que los directorios de volúmenes tengan los permisos correctos
RUN mkdir -p /vol/web/staticfiles /vol/web/media && \
    chmod -R 755 /vol/web

# Inicia Nginx en modo foreground
CMD ["nginx", "-g", "daemon off;"]