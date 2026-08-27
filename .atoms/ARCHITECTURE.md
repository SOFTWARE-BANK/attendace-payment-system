---
last_updated: 2026-08-25T21:05:11Z
---

# Diseno de arquitectura

## System Overview

Sistema de agregacion de asistencia y calculo de nomina (TimeLedger). Recibe los registros de acceso sin procesar del dispositivo de reconocimiento facial Hikvision, extrae automaticamente las horas de entrada y salida por dia y calcula los retardos, salidas anticipadas, horas extra, dias festivos y trabajo nocturno para liquidar la asistencia diaria. El resultado pasa por tres etapas de aprobacion electronica: responsable de asistencia -> gerente de departamento -> CEO, y queda confirmado y bloqueado. Solo la asistencia confirmada se incluye en la nomina semanal, quincenal o mensual. Las solicitudes de vacaciones, trabajo en dias festivos y conversion de horas extra a vacaciones usan el mismo flujo de tres etapas y se reflejan automaticamente en la asistencia y los saldos de vacaciones al aprobarse.

## Tech Stack

- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui + recharts + sonner
- Backend: Atoms Cloud (FastAPI + SQLAlchemy async + PostgreSQL)
- SDK: `@metagptx/web-sdk` (`client.entities.*` CRUD, API personalizada `client.apiCall.invoke`)
- Tema: neutro hue 200 + teal profundo (hue 187) como primario, Manrope/Noto Sans KR

## Diseno de modulos
| Module | Responsibility | Key Files |
|--------|---------------|-----------|
| Motor de asistencia | Extraccion automatica, calculo de tiempo, determinacion de estado, compensacion, nomina y dashboard | `app/backend/services/attendance_engine.py` |
| Aprobaciones electronicas | Transicion de estados en tres etapas y aplicacion de datos reales tras la aprobacion final | `app/backend/services/approval_flow.py` |
| API personalizada | Rutas de recepcion de registros, liquidacion, ajustes, aprobaciones, vacaciones, horas extra, nomina y dashboard | `app/backend/routers/attendance.py` |
| Frontend comun | Wrapper del SDK, tipos del dominio, utilidades de visualizacion y mapeo de etiquetas | `app/frontend/src/lib/api.ts` |
| Layout/sesion | Shell de la barra lateral y contexto para cambiar permisos de aprobacion | `src/components/AppShell.tsx`, `src/hooks/useSession.tsx` |
| Pantallas | Dashboard, registros de acceso, liquidacion diaria, aprobaciones, vacaciones, banco de horas extra, nomina y datos maestros | `src/pages/*.tsx` |

## Decisiones tecnicas
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Regla de extraccion | Primera entrada del dia = entrada; ultima salida = salida | El dispositivo genera varios registros diarios, por lo que solo se adoptan los limites |
| Bloqueo de asistencia | `locked=true` al aprobar el CEO | Evita distorsiones de nomina por nuevas liquidaciones o ajustes despues de confirmar |
| Criterio de nomina | Opcion `confirmed_only`; por defecto, solo aprobaciones del CEO | Impide que la asistencia pendiente se refleje en la nomina |
| Banco de horas extra | Libro mayor transaccional (acumulacion +, uso -) | Conserva el seguimiento de conversiones a vacaciones y compensaciones de retardos |
| Compensacion de retardos | Acumulacion de `offset_minutes` y registro en el libro mayor | Descuenta con precision de la deduccion salarial solo los minutos compensados |
| Tablas compartidas | `create_only=false` | Los responsables, gerentes y CEO consultan los mismos datos de asistencia y nomina |

## Plan del arbol de archivos

```
app/backend/
  services/attendance_engine.py   # calculo de liquidacion, nomina y dashboard
  services/approval_flow.py       # aprobacion en tres etapas
  routers/attendance.py           # /api/v1/attendance/*
  models|services|routers/<entity>.py  # generacion automatica de 11 entidades
app/frontend/src/
  lib/api.ts                      # wrapper del SDK, tipos y utilidades
  hooks/useSession.tsx            # contexto de permisos de aprobacion
  components/AppShell.tsx         # layout de barra lateral
  pages/Index.tsx                 # dashboard de asistencia
  pages/AccessLogs.tsx            # registros de acceso del dispositivo
  pages/DailyAttendance.tsx       # liquidacion, ajustes y compensaciones diarias
  pages/Approvals.tsx             # aprobaciones electronicas
  pages/LeaveManagement.tsx       # vacaciones y trabajo festivo
  pages/OvertimeBank.tsx          # banco de horas extra
  pages/Payroll.tsx               # agregacion de nomina
  pages/MasterSettings.tsx        # datos maestros y codigos de motivos
```

## Guia de implementacion

11 entidades: `employees`, `access_logs`, `attendance_reasons`, `daily_attendances`, `approvals`,
`leave_balances`, `leave_requests`, `weekend_work_requests`, `overtime_banks`, `payroll_runs`,
`payroll_items`.

Principales API personalizadas (`/api/v1/attendance`): `import_logs`, `seed_demo_logs`, `settle`, `settle_range`,
`adjust`, `approval/submit_daily_close`, `approval/submit_request`, `approval/approve`,
`approval/reject`, `leave/apply`, `weekend/apply`, `overtime/earn`, `overtime/convert`,
`overtime/offset_late`, `overtime/balance`, `payroll/calculate`, `dashboard`.

Flujo principal: recepcion de registros -> `settle` (extraccion y determinacion automatica) -> `adjust` si es necesario (registro del historial) -> `submit_daily_close` -> aprobacion del gerente de departamento -> aprobacion del CEO (bloqueo) -> acumulacion con `overtime/earn` -> `payroll/calculate`.

