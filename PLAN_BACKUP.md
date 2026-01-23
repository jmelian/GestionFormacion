# Plan de Backup - Sistema de Gestión de Formación

## Introducción

Este documento establece el Plan de Backup para el Sistema de Gestión de Formación, una aplicación Django con base de datos PostgreSQL containerizada. El plan define las estrategias, procedimientos y responsabilidades para garantizar la protección, integridad y recuperación de los datos del sistema.

## Objetivos

- Proteger los datos críticos del negocio contra pérdida
- Garantizar la continuidad operativa en caso de fallos
- Cumplir con requisitos legales de retención de datos
- Minimizar el impacto de pérdida de datos en operaciones
- Proporcionar procedimientos claros de recuperación
- Mantener la confidencialidad de datos sensibles

## Alcance

El plan de backup cubre:
- Base de datos PostgreSQL (datos de aplicación)
- Archivos estáticos y multimedia
- Configuraciones del sistema
- Logs de aplicación
- Certificados y claves de seguridad
- Documentos subidos por usuarios (titulaciones, certificados)

No incluye:
- Código fuente (gestionado por Git)
- Imágenes Docker (reconstruibles)
- Dependencias de terceros

## Estrategia de Backup

### Principios Generales
- **3-2-1 Rule**: 3 copias, 2 medios diferentes, 1 offsite
- **Inmutable**: Backups no modificables una vez creados
- **Encriptado**: Todos los backups en tránsito y reposo
- **Probado**: Validación regular de integridad y recuperabilidad

### Arquitectura de Backup
```
Producción → Backup Local → Backup Remoto → Backup Offsite
    ↓            ↓              ↓              ↓
PostgreSQL   NAS/SAN       AWS S3       Azure Blob
Archivos     Disco Local   Cloud Storage Cold Storage
Config       Git Repo      S3 Glacier   Tape Backup
```

## Tipos de Backup

### Backup Completo (Full Backup)
- **Contenido**: Todos los datos del sistema
- **Frecuencia**: Semanal (domingos 02:00)
- **Tamaño Estimado**: 50-100 GB
- **Tiempo de Ejecución**: 2-4 horas
- **Retención**: 1 año

### Backup Incremental
- **Contenido**: Cambios desde último backup completo
- **Frecuencia**: Diario (lunes-sábado 02:00)
- **Tamaño Estimado**: 1-10 GB
- **Tiempo de Ejecución**: 30-60 minutos
- **Retención**: 30 días

### Backup Diferencial
- **Contenido**: Cambios desde último backup completo
- **Frecuencia**: Diaria (como alternativa a incremental)
- **Ventaja**: Restauración más rápida que incremental
- **Desventaja**: Mayor tamaño que incremental

### Backup de Configuración
- **Contenido**: Variables de entorno, settings Django, docker-compose
- **Frecuencia**: Con cada cambio de configuración
- **Almacenamiento**: Git repository + backup automático
- **Retención**: Indefinida (versionado)

### Backup de Logs
- **Contenido**: Logs de aplicación, acceso, errores
- **Frecuencia**: Continua (rotación diaria)
- **Compresión**: Automática con gzip
- **Retención**: 90 días para operativos, 1 año para auditoría

## Programación de Backups

### Calendario Principal
| Tipo | Frecuencia | Día/Hora | Retención | Ubicación |
|------|------------|----------|-----------|-----------|
| Completo | Semanal | Domingo 02:00 | 1 año | Local + Remoto + Offsite |
| Incremental | Diario | Lu-Sá 02:00 | 30 días | Local + Remoto |
| Configuración | On-change | Automático | Indefinida | Git + Backup |
| Logs | Diario | 23:59 rotación | 90 días | Local + Remoto |

### Backups Ad-hoc
- **Pre-despliegue**: Antes de cada deployment a producción
- **Pre-mantenimiento**: Antes de cambios mayores en BD
- **Solicitud manual**: Para casos especiales con aprobación

### Ventanas de Backup
- **Producción**: 02:00 - 06:00 (horario de menor actividad)
- **Duración máxima**: 4 horas para backup completo
- **Impacto**: Backup online, sin downtime para usuarios

## Almacenamiento y Retención

### Niveles de Almacenamiento

#### Almacenamiento Local (Hot)
- **Tecnología**: NAS/SAN de alta velocidad
- **Ubicación**: Mismo datacenter que producción
- **Acceso**: < 15 minutos
- **Costo**: Alto
- **Uso**: Restauraciones rápidas, desarrollo

#### Almacenamiento Remoto (Warm)
- **Tecnología**: AWS S3, Azure Blob Storage
- **Ubicación**: Región secundaria
- **Acceso**: < 1 hora
- **Costo**: Medio
- **Uso**: Recuperación de desastres, compliance

#### Almacenamiento Offsite (Cold)
- **Tecnología**: AWS Glacier, Azure Archive Storage, Tape
- **Ubicación**: Región diferente o datacenter secundario
- **Acceso**: < 24 horas
- **Costo**: Bajo
- **Uso**: Retención a largo plazo, auditoría

### Política de Retención

#### Datos Operativos
- **Transaccionales**: 7 años (requisitos legales)
- **Históricos**: 3 años (análisis de tendencias)
- **Auditoría**: 5 años (cumplimiento)

#### Datos de Configuración
- **Versiones**: Indefinida (Git history)
- **Backups**: 1 año
- **Documentación**: Indefinida

#### Logs
- **Operativos**: 90 días
- **Seguridad**: 1 año
- **Auditoría**: 5 años

## Procedimientos de Backup

### Backup de Base de Datos PostgreSQL

#### Comando de Backup
```bash
# Backup completo
docker-compose exec db pg_dumpall -U formacion_user > backup_full_$(date +%Y%m%d_%H%M%S).sql

# Backup comprimido
docker-compose exec db pg_dumpall -U formacion_user | gzip > backup_full_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup por base de datos
docker-compose exec db pg_dump -U formacion_user -d formacion_db > backup_db_$(date +%Y%m%d_%H%M%S).sql
```

#### Backup de Archivos
```bash
# Archivos de la aplicación
docker run --rm -v formacion_media:/data -v $(pwd):/backup alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz -C /data .

# Archivos estáticos
tar czf static_backup_$(date +%Y%m%d).tar.gz staticfiles/
```

### Automatización
```bash
#!/bin/bash
# script_backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

# Crear directorio
mkdir -p $BACKUP_DIR/$DATE

# Backup base de datos
docker-compose exec -T db pg_dumpall -U formacion_user | gzip > $BACKUP_DIR/$DATE/db_backup.sql.gz

# Backup archivos
docker run --rm -v formacion_media:/data alpine tar czf $BACKUP_DIR/$DATE/media_backup.tar.gz -C /data .

# Copiar a almacenamiento remoto
aws s3 cp $BACKUP_DIR/$DATE/ s3://formacion-backups/$DATE/ --recursive

# Limpiar backups locales antiguos (mantener 7 días)
find $BACKUP_DIR -type d -mtime +7 -exec rm -rf {} \;
```

## Procedimientos de Recuperación

### Restauración Completa
1. **Preparación**: Detener aplicación y servicios
2. **Restaurar Base de Datos**:
   ```bash
   docker-compose exec -T db psql -U formacion_user < backup.sql
   ```
3. **Restaurar Archivos**:
   ```bash
   docker run --rm -v formacion_media:/data alpine tar xzf media_backup.tar.gz -C /data
   ```
4. **Verificación**: Ejecutar pruebas de integridad
5. **Reinicio**: Iniciar servicios y validar funcionamiento

### Restauración Parcial
- **Tabla específica**: Usar pg_restore con opciones de tabla
- **Archivo específico**: Extraer del backup comprimido
- **Punto en tiempo**: Usar WAL logs para recuperación PITR

### Tiempo de Recuperación Objetivo (RTO)
- **Crítico**: 4 horas para restauración completa
- **Importante**: 24 horas para datos históricos
- **No crítico**: 72 horas para datos antiguos

### Punto de Recuperación Objetivo (RPO)
- **Datos críticos**: Máximo 1 hora de pérdida
- **Datos importantes**: Máximo 24 horas de pérdida
- **Datos históricos**: Hasta 1 semana de pérdida aceptable

## Testing y Validación

### Pruebas de Integridad
- **Checksum**: Verificación automática post-backup
- **Conteo de Registros**: Validación de número de filas
- **Referential Integrity**: Verificación de claves foráneas
- **Logical Checks**: Validación de reglas de negocio

### Pruebas de Recuperación
- **Frecuencia**: Trimestral para backups completos
- **Alcance**: Al menos 1 backup por tipo por trimestre
- **Entorno**: Servidor de testing dedicado
- **Validación**: Pruebas funcionales completas

### Reportes de Testing
- **Resultado**: Éxito/fallo de cada prueba
- **Tiempo**: Duración de restauración real
- **Problemas**: Issues encontrados y resueltos
- **Recomendaciones**: Mejoras al proceso

## Seguridad

### Encriptación
- **En tránsito**: TLS 1.3 para transferencias
- **En reposo**: AES-256 para archivos almacenados
- **Claves**: Gestionadas por AWS KMS/Azure Key Vault

### Control de Acceso
- **Principio de menor privilegio**: Acceso solo a backups necesarios
- **Autenticación**: Multi-factor para acceso administrativo
- **Auditoría**: Logging completo de accesos a backups

### Cumplimiento
- **GDPR**: Anonimización de datos personales en backups no productivos
- **ISO 27001**: Controles de seguridad para backups
- **SOX**: Retención y auditabilidad para datos financieros

## Monitoreo y Alertas

### Métricas de Backup
- **Éxito de ejecución**: 100% de backups completados
- **Tamaño de backups**: Tendencia y alertas de crecimiento anormal
- **Tiempo de ejecución**: Dentro de ventana programada
- **Espacio de almacenamiento**: Alertas de capacidad baja

### Alertas Críticas
- **Backup fallido**: Notificación inmediata al equipo de operaciones
- **Espacio insuficiente**: Alerta 48 horas antes de agotamiento
- **Corrupción detectada**: Investigación inmediata
- **Acceso no autorizado**: Alerta de seguridad

## Responsabilidades

### Equipo de Operaciones
- **Ejecución**: Monitoreo y ejecución de backups automáticos
- **Validación**: Verificación diaria de éxito de backups
- **Testing**: Coordinación de pruebas de recuperación trimestrales
- **Soporte**: Resolución de problemas de backup

### Equipo de Desarrollo
- **Configuración**: Mantenimiento de scripts de backup
- **Optimización**: Mejora de procedimientos de backup
- **Testing**: Desarrollo de tests de integridad
- **Documentación**: Actualización de procedimientos

### Administración
- **Aprobación**: Cambios mayores al plan de backup
- **Recursos**: Aseguramiento de presupuesto y recursos
- **Auditoría**: Revisión anual del cumplimiento
- **Comunicación**: Notificación de cambios a stakeholders

## Gestión de Riesgos

### Riesgos Identificados
- **Falla de backup**: Mitigado con múltiples copias
- **Corrupción de datos**: Detectado por checksums
- **Pérdida de claves**: Backup de claves en HSM
- **Acceso no autorizado**: Encriptación y control de acceso

### Planes de Contingencia
- **Backup manual**: Procedimiento alternativo si automatización falla
- **Restauración desde réplica**: Usar standby database si disponible
- **Recuperación de desastres**: Plan completo para pérdida total de datacenter
- **Comunicación**: Protocolo de notificación a stakeholders

## Mejora Continua

### Indicadores de Rendimiento
- **Cobertura de backup**: Porcentaje de datos respaldados
- **Tiempo de recuperación**: Medición real vs objetivos
- **Tasa de éxito**: Porcentaje de backups exitosos
- **Costo por GB**: Eficiencia de almacenamiento

### Revisiones del Plan
- **Trimestral**: Revisión de métricas y procedimientos
- **Anual**: Auditoría completa y actualización
- **Post-incidente**: Revisión después de cualquier fallo de backup
- **Tecnológica**: Evaluación de nuevas herramientas

### Objetivos de Mejora
- Reducir RTO a 2 horas para recuperación completa
- Lograr 100% de éxito en backups automáticos
- Implementar backup continuo para datos críticos
- Automatizar validación completa de backups

---

**Versión**: 1.0
**Fecha**: 2025-10-07
**Autor**: Equipo de Operaciones y Seguridad
**Aprobado por**: Dirección Técnica