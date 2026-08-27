---
last_updated: 2026-08-25T21:05:11Z
---

# Requisitos y progreso

## Resumen de requisitos

## Historias de usuario

# Desglose de tareas
- [x] Crear 11 modelos de datos (empleados/registros de acceso/motivos/asistencia diaria/aprobaciones/saldos de vacaciones/solicitudes de vacaciones/trabajo festivo/banco de horas extra/ejecuciones de nomina/detalles de nomina)
- [x] Cargar datos maestros de empleados, codigos de motivos y saldos de vacaciones
- [x] Motor de asistencia: extraccion automatica, calculo de retardos/salidas anticipadas/horas extra/trabajo nocturno/festivos y determinacion automatica del estado
- [x] Aprobacion electronica en tres etapas (responsable de asistencia -> gerente de departamento -> CEO) y bloqueo tras la aprobacion final
- [x] Registro y ajuste de motivos de asistencia, con historial de ajustes
- [x] Solicitud de vacaciones -> aprobacion -> descuento del saldo y reflejo automatico en asistencia
- [x] Solicitud de trabajo en sabado/domingo -> aprobacion -> confirmacion comparando los registros de acceso
- [x] Acumulacion de horas extra -> conversion a vacaciones y compensacion Extra de deducciones por retardos
- [x] Agregacion de nomina (semanal/quincenal/mensual) y exportacion CSV
- [x] Dashboard de asistencia por equipo/empleado (tendencias, distribucion y detalle)
- [x] Implementar 8 pantallas frontend y superar lint/build
- [x] Implementar diccionario i18n coreano/espanol y selector de idioma en el encabezado
- [x] Sustituir los textos de toda la interfaz mediante `t()`
- [x] Corregir la pantalla blanca del dashboard (diferencias entre campos de solicitud/respuesta y conversion de `detail` de errores a texto)
| ID | Task | Assignee | Status | Deps |
|----|------|----------|--------|------|

## Registro de progreso
- Se cargaron 240 registros de acceso de demostracion y se valido la liquidacion automatica de 80 registros de asistencia durante 14 dias.
- Se detecto un calculo incorrecto de 420 minutos de retraso por reinterpretacion de zona horaria al guardar la hora del dispositivo; se corrigio fijando la etiqueta UTC mediante `as_utc()`.
- Se agrego la API de reinicio de transacciones (`/attendance/reset_demo`) para validacion; tras recargar los datos, la clasificacion de retardos quedo normalizada (normal 53 / tarde 27).
- Se confirmo el bloqueo de 8 registros de asistencia al aprobar el flujo de tres etapas (envio -> gerente de departamento -> CEO).
- Se valido la compensacion de 11 minutos de retraso con Extra tras acumular horas extra (saldo 91 -> 80 minutos) y la nomina semanal de 2 empleados por 302,500.
- Se incorporo el cambio de idioma (ko/es): diccionario en `lib/i18n.ts`, selector desplegable en el encabezado de `AppShell` y sustitucion de textos en las 8 pantallas.
- Se corrigieron tres causas de pantalla blanca: claves de solicitud de dashboard/`settle_range` a `period_start`/`period_end`, esquema `days` para `seed_demo_logs` y conversion del array `detail` de FastAPI 422 a texto para el toast.
- Se alinearon los campos de respuesta del dashboard usando `trend`, `summary.late|absent|leave|confirmed|pending_approvals` y `absent_days|leave_days`; la distribucion de estados se calcula desde `summary`.
- Se elimino la logica de diagnostico temporal (overlay `diag` en `main.tsx`) y se completo la validacion de lint, build y renderizado.

