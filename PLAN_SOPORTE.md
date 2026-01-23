# Plan de Soporte - Sistema de Gestión de Formación

## Introducción

Este documento describe el Plan de Soporte para el Sistema de Gestión de Formación, una aplicación web desarrollada con Django que permite la administración integral de procesos formativos dentro de una organización. El plan establece los niveles de soporte, procedimientos de resolución de incidentes, acuerdos de nivel de servicio (SLA) y responsabilidades del equipo de soporte.

## Objetivos

- Proporcionar soporte técnico eficiente y oportuno a usuarios del sistema
- Minimizar el tiempo de inactividad del sistema
- Garantizar la resolución adecuada de incidentes y problemas
- Mantener altos niveles de satisfacción del usuario
- Establecer procesos claros de escalada y comunicación

## Alcance

El soporte cubre:
- Aplicación web principal (formacion_demo)
- Base de datos PostgreSQL
- Servicios de contenedorización (Docker)
- Servidor web (Nginx + Gunicorn)
- Funcionalidades del sistema: gestión de cursos, empleados, titulaciones, reportes, etc.

No incluye soporte para:
- Hardware de usuario final
- Redes corporativas externas
- Software de terceros no relacionado con el sistema

## Niveles de Soporte

### Nivel 1 (L1) - Soporte de Primera Línea
**Responsables**: Equipo de Help Desk / Soporte Técnico Inicial

**Funciones**:
- Recepción y registro de incidentes
- Resolución de problemas básicos y conocidos
- Verificación de configuración de usuario
- Guía básica de uso del sistema
- Escalada a niveles superiores cuando sea necesario

**Herramientas**:
- Sistema de tickets (Jira/Redmine/ServiceNow)
- Base de conocimientos
- Documentación de usuario (GUIA_USUARIO.md)

### Nivel 2 (L2) - Soporte Técnico Avanzado
**Responsables**: Desarrolladores / Administradores de Sistema

**Funciones**:
- Análisis técnico detallado de incidentes
- Resolución de problemas de aplicación
- Configuración de entornos
- Optimización de rendimiento
- Desarrollo de parches temporales

**Herramientas**:
- Acceso a logs del sistema
- Herramientas de debugging (Django Debug Toolbar)
- Acceso a base de datos para consultas
- Repositorio de código (Git)

### Nivel 3 (L3) - Soporte de Desarrollo y Arquitectura
**Responsables**: Equipo de Desarrollo Senior / Arquitectos

**Funciones**:
- Análisis de problemas complejos
- Desarrollo de soluciones permanentes
- Modificaciones al código base
- Actualizaciones de arquitectura
- Consultoría técnica especializada

**Herramientas**:
- Entorno de desarrollo completo
- Acceso administrativo al sistema
- Herramientas de profiling y análisis

## Horarios de Soporte

### Soporte Estándar
- **Días laborables**: Lunes a Viernes, 8:00 - 18:00 (hora local)
- **Festivos**: Soporte limitado para incidentes críticos
- **Fuera de horario**: Soporte de guardia para emergencias

### Soporte 24/7
- Disponible para incidentes críticos que afectan operaciones críticas
- Activado mediante evaluación de impacto del incidente

## Contactos de Soporte

### Canal Principal
- **Email**: soporte.formacion@empresa.com
- **Teléfono**: +34 900 123 456
- **Portal de Soporte**: https://soporte.empresa.com/formacion

### Contactos por Rol
- **Administradores del Sistema**: admin@empresa.com
- **Equipo de Desarrollo**: desarrollo@empresa.com
- **Dirección Técnica**: cto@empresa.com

## Proceso de Gestión de Incidentes

### 1. Registro del Incidente
- Usuario reporta el problema a través del canal apropiado
- Se asigna número de ticket único
- Se recopila información inicial: descripción, impacto, urgencia

### 2. Clasificación y Priorización
**Niveles de Urgencia**:
- **Crítica**: Sistema completamente inoperable, afecta múltiples usuarios
- **Alta**: Funcionalidad principal afectada, impacto significativo
- **Media**: Funcionalidad secundaria afectada
- **Baja**: Problemas menores, sin impacto operativo

**Niveles de Impacto**:
- **Alto**: Afecta operaciones críticas del negocio
- **Medio**: Afecta operaciones normales
- **Bajo**: Afecta usuarios individuales

### 3. Diagnóstico y Resolución
- Asignación automática basada en tipo de problema
- Investigación siguiendo procedimientos documentados
- Comunicación regular con el usuario sobre progreso

### 4. Cierre del Incidente
- Verificación de resolución por el usuario
- Documentación de la solución en base de conocimientos
- Análisis post-mortem para incidentes críticos

## Acuerdos de Nivel de Servicio (SLA)

### Tiempos de Respuesta
| Urgencia | Nivel 1 | Nivel 2 | Nivel 3 |
|----------|---------|---------|---------|
| Crítica  | 15 min  | 1 hora  | 4 horas |
| Alta     | 30 min  | 2 horas | 8 horas |
| Media    | 2 horas | 4 horas | 24 horas|
| Baja     | 4 horas | 8 horas | 48 horas|

### Tiempos de Resolución
| Urgencia | Objetivo de Resolución |
|----------|----------------------|
| Crítica  | 4 horas              |
| Alta     | 8 horas              |
| Media    | 24 horas             |
| Baja     | 72 horas             |

### Métricas de Calidad
- **Disponibilidad del Sistema**: >99.5% mensual
- **Satisfacción del Usuario**: >4.5/5 en encuestas
- **Tasa de Resolución en Primer Contacto**: >70%

## Procedimientos de Escalada

### Escalada Automática
- Incidentes sin respuesta en tiempo SLA se escalan automáticamente
- Incidentes críticos se notifican inmediatamente a dirección

### Escalada Manual
- Soporte L1 puede escalar si no puede resolver en 30 minutos
- Soporte L2 puede escalar si requiere cambios en código base

### Comité de Escalada
- Reunión semanal para revisión de incidentes pendientes
- Evaluación de tendencias y problemas recurrentes

## Herramientas y Recursos

### Herramientas de Monitoreo
- **Health Check Endpoint**: `/formacion/api/health/`
- **Página de Monitorización**: `/formacion/monitorizacion/`
- **Logs del Sistema**: Recopilados en contenedores Docker
- **Alertas**: Configuradas para métricas críticas

### Base de Conocimientos
- **Documentación Técnica**: PROJECT_DOCUMENTATION.md
- **Guía de Usuario**: GUIA_USUARIO.md
- **Guía de Instalación**: GUIA_INSTALACION.md
- **Base de Soluciones**: Wiki interna con soluciones comunes

### Capacitación del Equipo
- **Capacitación Inicial**: 40 horas para nuevos miembros
- **Capacitación Continua**: 8 horas mensuales
- **Certificaciones**: Django, PostgreSQL, Docker

## Comunicación

### Comunicación Interna
- **Reuniones Diarias**: Stand-up para revisión de incidentes
- **Informes Semanales**: Métricas de soporte y tendencias
- **Alertas de Emergencia**: Canal dedicado en Slack/Teams

### Comunicación con Usuarios
- **Actualizaciones de Estado**: A través del portal de soporte
- **Boletín Informativo**: Comunicaciones proactivas sobre mantenimiento
- **Encuestas de Satisfacción**: Después de resolución de incidentes

## Mejora Continua

### Revisión del Plan
- **Revisión Anual**: Actualización completa del plan
- **Revisión Trimestral**: Ajustes menores basados en métricas

### Indicadores de Mejora
- Reducción del tiempo medio de resolución
- Aumento de la tasa de resolución en primer contacto
- Mejora en puntuaciones de satisfacción

### Lecciones Aprendidas
- Análisis post-incidente para todos los incidentes críticos
- Actualización de procedimientos basada en experiencias

---

**Versión**: 1.0
**Fecha**: 2025-10-07
**Autor**: Equipo de Soporte y Desarrollo
**Aprobado por**: Dirección Técnica