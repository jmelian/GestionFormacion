# Plan de Monitorización - Sistema de Gestión de Formación

## Introducción

Este documento define el Plan de Monitorización para el Sistema de Gestión de Formación, una aplicación Django containerizada que administra procesos formativos organizacionales. El plan establece las métricas, herramientas y procedimientos necesarios para mantener la observabilidad continua del sistema y responder proactivamente a incidentes.

## Objetivos

- Detectar problemas de rendimiento y disponibilidad de manera temprana
- Proporcionar visibilidad completa del estado del sistema
- Facilitar la resolución rápida de incidentes
- Optimizar el rendimiento y la utilización de recursos
- Garantizar el cumplimiento de acuerdos de nivel de servicio (SLA)
- Generar insights para mejora continua

## Alcance

La monitorización cubre:
- Aplicación Django (formacion_demo)
- Base de datos PostgreSQL
- Contenedores Docker
- Servidor web Nginx
- Servidor WSGI Gunicorn
- Sistema operativo del host
- Recursos de infraestructura (CPU, memoria, disco, red)

## Arquitectura de Monitorización

### Componentes Principales

#### 1. Health Check API
- **Endpoint**: `/formacion/api/health/`
- **Función**: Verificación automática del estado de servicios con métricas y umbrales
- **Frecuencia**: Consultas continuas por herramientas de monitoreo
- **Respuesta**: JSON con estado detallado, métricas actuales y umbrales configurados
- **Umbrales**: Incluye configuración completa de thresholds para CPU, memoria, disco, etc.
- **Métricas**: Valores actuales de CPU, memoria, disco y load average
- **Estado Inteligente**: Marca como unhealthy cuando se exceden umbrales críticos

#### 2. Dashboard de Monitorización
- **URL**: `/formacion/monitorizacion/`
- **Acceso**: Restringido a administradores
- **Funcionalidad**: Visualización en tiempo real del estado del sistema
- **Actualización**: Automática cada 30 segundos

#### 3. Sistema de Alertas
- **Umbrales Configurables**: Basados en métricas críticas
- **Canales de Notificación**: Email, Slack, SMS
- **Escalada Automática**: Según severidad del problema

## Métricas de Monitorización

### Aplicación Django

#### Rendimiento
- **Tiempo de Respuesta**: Promedio y percentil 95 de requests
- **Throughput**: Requests por segundo
- **Tasa de Error**: Porcentaje de respuestas 4xx/5xx
- **Conexiones Activas**: Número de sesiones concurrentes

#### Recursos de Aplicación
- **Uso de Memoria**: Heap memory de Python
- **Uso de CPU**: Por proceso Django/Gunicorn
- **Conexiones a BD**: Pool de conexiones PostgreSQL
- **Workers Gunicorn**: Estado y utilización

### Base de Datos PostgreSQL

#### Rendimiento
- **Query Time**: Tiempo promedio de ejecución de queries
- **Connection Pool**: Conexiones activas vs disponibles
- **Cache Hit Ratio**: Eficiencia del buffer cache
- **Lock Waits**: Contenciones de bloqueo

#### Recursos
- **Uso de Disco**: Espacio ocupado por datos
- **Uso de Memoria**: Shared buffers y work mem
- **I/O Operations**: Lecturas/escrituras por segundo
- **Replication Lag**: Retraso en replicación (si aplica)

### Contenedores Docker

#### Salud de Contenedores
- **Estado de Contenedores**: Running, stopped, restarting
- **Health Checks**: Resultado de probes configuradas
- **Restart Count**: Número de reinicios automáticos
- **Resource Usage**: CPU, memoria por contenedor

#### Logs de Contenedores
- **Errores de Aplicación**: Excepciones y errores Django
- **Warnings**: Advertencias del sistema
- **Access Logs**: Patrones de acceso anómalos

### Servidor Web Nginx

#### Rendimiento
- **Requests Rate**: Solicitudes por segundo
- **Response Time**: Tiempo de respuesta promedio
- **Upstream Response Time**: Tiempo de respuesta de backend
- **Error Rate**: Porcentaje de errores 5xx

#### Recursos
- **Active Connections**: Conexiones activas
- **Waiting Connections**: Cola de conexiones
- **Worker Processes**: Estado de procesos worker

### Sistema Operativo

#### Recursos del Host
- **CPU Usage**: Porcentaje de utilización
- **Memory Usage**: RAM utilizada vs disponible
- **Disk I/O**: Operaciones de lectura/escritura
- **Network I/O**: Tráfico de red entrante/saliente

#### Sistema de Archivos
- **Disk Space**: Espacio disponible en particiones
- **Inode Usage**: Nodos índice disponibles
- **File System Health**: Estado de sistemas de archivos

## Herramientas de Monitorización

### Monitoreo Interno (Built-in)

#### Health Check Endpoint
```json
{
  "status": "healthy",
  "timestamp": "2025-10-07T08:21:46.790Z",
  "thresholds": {
    "cpu": {"critical": 95, "high": 85, "medium": 70},
    "memory": {"critical": 95, "high": 85, "medium": 70},
    "disk": {"critical": 95, "high": 90, "medium": 80},
    "response_time": {"critical": 10.0, "high": 5.0, "medium": 2.0},
    "error_rate": {"critical": 5.0, "high": 1.0, "medium": 0.5}
  },
  "metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "memory_used_gb": 5.4,
    "memory_total_gb": 8.0,
    "disk_percent": 72.1,
    "disk_used_gb": 156.7,
    "disk_total_gb": 232.9,
    "load_average": [1.2, 1.1, 1.0]
  },
  "services": {
    "database": {"status": "healthy", "type": "PostgreSQL"},
    "application": {"status": "healthy", "version": "Django 5.2.3"},
    "server": {"status": "healthy"},
    "container": {"status": "healthy"},
    "email": {"status": "info"}
  }
}
```

#### Django Debug Toolbar
- **Uso**: Desarrollo y troubleshooting
- **Métricas**: SQL queries, templates, cache hits
- **Configuración**: Activado en DEBUG=True

### Herramientas Externas Recomendadas

#### Prometheus + Grafana
- **Prometheus**: Recolección de métricas
- **Grafana**: Visualización y dashboards
- **Alertmanager**: Gestión de alertas

#### ELK Stack
- **Elasticsearch**: Almacenamiento de logs
- **Logstash**: Procesamiento de logs
- **Kibana**: Análisis y visualización de logs

#### Zabbix/Nagios
- **Monitoreo Integral**: Métricas del sistema
- **Alertas**: Notificaciones configurables
- **Reporting**: Dashboards y reportes

## Sistema de Alertas

### Niveles de Severidad

#### Crítica (P1)
- **Condiciones**: Sistema completamente inoperable
- **Tiempo de Respuesta**: Inmediato (< 5 minutos)
- **Notificación**: Todos los canales (email, SMS, llamada)
- **Escalada**: Dirección técnica automáticamente

#### Alta (P2)
- **Condiciones**: Funcionalidad crítica afectada
- **Tiempo de Respuesta**: 15 minutos
- **Notificación**: Email + Slack
- **Escalada**: Equipo de soporte senior

#### Media (P3)
- **Condiciones**: Funcionalidad secundaria afectada
- **Tiempo de Respuesta**: 1 hora
- **Notificación**: Email
- **Escalada**: Equipo de soporte regular

#### Baja (P4)
- **Condiciones**: Problemas menores, sin impacto operativo
- **Tiempo de Respuesta**: 4 horas
- **Notificación**: Dashboard interno
- **Escalada**: No automática

### Umbrales de Alerta

| Métrica | Crítico | Alto | Medio | Bajo |
|---------|---------|------|-------|------|
| Disponibilidad | <99% | <99.5% | <99.9% | <99.95% |
| Tiempo Respuesta | >10s | >5s | >2s | >1s |
| Uso CPU | >95% | >85% | >70% | >50% |
| Uso Memoria | >95% | >85% | >70% | >50% |
| Espacio Disco | <5% | <10% | <15% | <20% |

## Procedimientos de Respuesta

### Detección de Problemas
1. **Alerta Automática**: Sistema detecta anomalía
2. **Verificación**: Equipo confirma el problema
3. **Clasificación**: Asignación de severidad
4. **Notificación**: Comunicación a stakeholders

### Resolución de Incidentes
1. **Diagnóstico**: Análisis de causa raíz
2. **Contención**: Medidas temporales para minimizar impacto
3. **Resolución**: Implementación de solución permanente
4. **Recuperación**: Verificación de funcionamiento normal
5. **Lecciones Aprendidas**: Documentación y mejoras

### Comunicación
- **Interna**: Actualizaciones cada 30 minutos durante incidentes
- **Externa**: Página de estado público para usuarios
- **Post-Incidente**: Informe detallado con timeline y acciones tomadas

## Reportes y Análisis

### Reportes Diarios
- **Disponibilidad del Sistema**: 99.9% objetivo
- **Métricas de Rendimiento**: Latencia, throughput, errores
- **Uso de Recursos**: CPU, memoria, disco
- **Incidentes**: Número y severidad

### Reportes Semanales
- **Tendencias**: Análisis de patrones
- **Capacidad**: Proyecciones de crecimiento
- **Problemas Recurrentes**: Identificación de áreas de mejora
- **Cumplimiento SLA**: Verificación de objetivos

### Reportes Mensuales
- **KPI de Monitorización**: Métricas de efectividad
- **Análisis de Incidentes**: Causas y tiempos de resolución
- **Recomendaciones**: Sugerencias de optimización
- **Benchmarking**: Comparación con períodos anteriores

## Configuración Técnica

### Configuración de Health Checks

#### Docker Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/formacion/api/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### Configuración de Umbrales
```python
# settings.py
MONITORING_THRESHOLDS = {
    'cpu': {
        'critical': config('MONITORING_CPU_CRITICAL', default=95, cast=int),
        'high': config('MONITORING_CPU_HIGH', default=85, cast=int),
        'medium': config('MONITORING_CPU_MEDIUM', default=70, cast=int),
    },
    'memory': {
        'critical': config('MONITORING_MEMORY_CRITICAL', default=95, cast=int),
        'high': config('MONITORING_MEMORY_HIGH', default=85, cast=int),
        'medium': config('MONITORING_MEMORY_MEDIUM', default=70, cast=int),
    },
    # ... otros umbrales
}
```

#### Variables de Entorno
```bash
# .env
MONITORING_CPU_CRITICAL=95
MONITORING_MEMORY_CRITICAL=95
MONITORING_DISK_CRITICAL=95
MONITORING_RESPONSE_TIME_CRITICAL=10.0
MONITORING_ERROR_RATE_CRITICAL=5.0
```

#### Métricas Personalizadas Django
```python
# settings.py
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

### Configuración de Logs

#### Niveles de Logging
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'file': {'class': 'logging.FileHandler', 'filename': 'django.log'}
    },
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'formacion': {'handlers': ['console', 'file'], 'level': 'DEBUG'}
    }
}
```

## Mejora Continua

### Revisión de Umbrales
- **Ajuste Dinámico**: Basado en patrones históricos
- **Machine Learning**: Detección automática de anomalías
- **Feedback Loop**: Incorporación de lecciones aprendidas

### Expansión de Cobertura
- **Nuevas Métricas**: Según evolución del sistema
- **Monitoreo de Usuario**: RUM (Real User Monitoring)
- **Monitoreo Sintético**: Tests automatizados de funcionalidades críticas

### Automatización
- **Auto-scaling**: Ajuste automático de recursos
- **Auto-healing**: Recuperación automática de fallos menores
- **Auto-remediation**: Soluciones automáticas para problemas conocidos

## Riesgos y Contingencias

### Riesgos Identificados
- **Pérdida de Métricas**: Backup de datos de monitoreo
- **Alert Fatigue**: Optimización de umbrales y reglas
- **Single Point of Failure**: Redundancia en herramientas de monitoreo
- **Configuración Incorrecta**: Revisiones regulares de configuración

### Planes de Contingencia
- **Monitoreo Manual**: Procedimientos para fallos de herramientas
- **Escalada de Emergencia**: Contactos alternativos
- **Documentación Offline**: Copias impresas de procedimientos críticos

---

**Versión**: 1.0
**Fecha**: 2025-10-07
**Autor**: Equipo de Operaciones e Infraestructura
**Aprobado por**: Dirección Técnica