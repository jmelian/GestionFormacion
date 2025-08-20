@echo off
echo ==========================================
echo   Configurando aplicacion Django
echo ==========================================

echo.
echo [1/4] Ejecutando migraciones...
docker-compose exec web python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Fallo en las migraciones
    pause
    exit /b 1
)

echo.
echo [2/4] Cargando grupos iniciales...
docker-compose exec web python manage.py loaddata initial_groups.json
if %errorlevel% neq 0 (
    echo ERROR: Fallo al cargar grupos iniciales
    pause
    exit /b 1
)

echo.
echo [3/4] Cargando permisos iniciales...
docker-compose exec web python manage.py loaddata initial_permissions.json
if %errorlevel% neq 0 (
    echo ERROR: Fallo al cargar permisos iniciales
    pause
    exit /b 1
)

echo.
echo [4/4] Cargando datos de respaldo...
docker-compose exec web python manage.py loaddata datos/backup_temp.json
if %errorlevel% neq 0 (
    echo ERROR: Fallo al cargar datos de respaldo
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Configuracion completada exitosamente!
echo ==========================================
echo.
echo La aplicacion esta lista para usar.
pause