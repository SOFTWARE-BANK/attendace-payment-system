<div align="center">

# TimeLedger

### Sistema integrado de asistencia y nómina

Gestión de asistencia, aprobaciones, vacaciones, horas extra y nómina desde una sola plataforma.

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](app/backend)
[![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB?style=for-the-badge&logo=react&logoColor=111827)](app/frontend)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](app/backend/requirements.txt)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](app/frontend/package.json)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)

**[Guía de instalación](#instalación-en-windows)** · **[Arranque local](#configuración-y-arranque-local)** · **[API](#api-principal)** · **[GitHub](https://github.com/SOFTWARE-BANK/attendace-payment-system)**

</div>

## Visión general

TimeLedger es una aplicación web para administrar asistencia, registros de acceso, aprobaciones, vacaciones, horas extra y cálculo de nómina. Está pensada para convertir los registros de un dispositivo de control de acceso en información validada, aprobada y lista para el cálculo salarial.

### Arquitectura en una mirada

```mermaid
flowchart LR
	D[Dispositivo Hikvision] -->|Registros de acceso| API[Backend FastAPI]
	API --> DB[(SQLite o PostgreSQL)]
	API --> E[Motor de asistencia]
	E --> A[Aprobación en 3 etapas]
	A --> P[Cálculo de nómina]
	UI[Frontend React] <--> API
	P --> CSV[Exportación CSV]
```

### Tecnologías

- **Backend:** API REST construida con FastAPI, SQLAlchemy y SQLite/PostgreSQL.
- **Frontend:** interfaz React con TypeScript, Vite, Tailwind CSS y shadcn/ui.
- **Documentación técnica:** [.wiki.md](.wiki.md), [.atoms/ARCHITECTURE.md](.atoms/ARCHITECTURE.md) y [.atoms/PROGRESS.md](.atoms/PROGRESS.md).

## Índice

- [Funciones principales](#funciones-principales)
- [Requisitos](#requisitos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación en Windows](#instalación-en-windows)
- [Configuración y arranque local](#configuración-y-arranque-local)
- [Prueba rápida](#prueba-rápida-con-datos-de-demostración)
- [API principal](#api-principal)
- [Comandos del frontend](#comandos-del-frontend)
- [Base de datos y seguridad](#base-de-datos)
- [Solución de problemas](#solución-de-problemas)

## Funciones principales

| Módulo | Qué resuelve |
|---|---|
| Asistencia | Convierte registros de entrada/salida en jornadas liquidadas. |
| Aprobaciones | Gestiona el circuito responsable de asistencia -> gerente -> CEO. |
| Vacaciones | Registra solicitudes, aprobaciones y saldos disponibles. |
| Horas extra | Acumula, convierte a vacaciones y compensa retardos. |
| Nómina | Calcula periodos semanales, quincenales o mensuales y exporta CSV. |
| Internacionalización | Permite alternar la interfaz entre coreano y español. |
| Sincronización Hikvision | Sincronización automática con lectores de acceso. |
| Gestión de empleados | Foto, tipo de persona, registro facial. |

## Requisitos

- Python 3.11 o posterior.
- Node.js 20 o posterior.
- npm o pnpm.
- Git.

No es necesario instalar PostgreSQL para una prueba local: el backend puede utilizar SQLite.

## Estructura del proyecto

```text
.
├── app/
│   ├── backend/
│   │   ├── core/              # Configuración, autenticación y base de datos
│   │   ├── models/            # Modelos ORM
│   │   ├── routers/           # Endpoints REST
│   │   ├── services/          # Lógica de asistencia, aprobaciones y nómina
│   │   ├── mock_data/         # Datos iniciales de demostración
│   │   ├── requirements.txt   # Dependencias Python
│   │   └── main.py            # Aplicación FastAPI
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/    # Componentes compartidos
│   │   │   ├── pages/         # Pantallas de la aplicación
│   │   │   └── lib/           # API, tipos e internacionalización
│   │   ├── package.json
│   │   └── vite.config.ts
│   └── start_app_v2.sh        # Arranque automatizado para Linux/macOS
├── .gitignore
└── README.md
```

## Instalación en Windows

Abre dos terminales de PowerShell en la carpeta del proyecto. El backend y el frontend se ejecutan como procesos independientes.

> **Nota:** en este entorno se usa `npm.cmd` porque PowerShell puede bloquear el wrapper `npm.ps1`.

### 1. Preparar el backend

```powershell
Set-Location ".\app\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Preparar el frontend

En otra terminal:

```powershell
Set-Location ".\app\frontend"
npm.cmd install
```

El proyecto conserva `pnpm-lock.yaml`; si prefieres pnpm, usa `pnpm install` en lugar de `npm.cmd install`.

## Configuración y arranque local

> **Resultado esperado:** API en `http://127.0.0.1:8000` y aplicación web en `http://127.0.0.1:3000`.

### Backend

**Opción recomendada:** crea `app/backend/.env` con tu configuración (usa `app/backend/.env.example` como plantilla). El backend lo carga automáticamente al arrancar —gracias a `core/bootstrap_env.py`— y el archivo está excluido de Git. Con el `.env` en su lugar, basta con:

```powershell
Set-Location ".\app\backend"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Como alternativa, también puedes definir las variables de desarrollo en la propia terminal (estas tienen prioridad sobre el `.env`):

```powershell
Set-Location ".\app\backend"
$env:DATABASE_URL = "sqlite:///./attendance.db"
$env:JWT_SECRET_KEY = "cambia-esta-clave-en-produccion"
$env:JWT_ALGORITHM = "HS256"
$env:ADMIN_USER_ID = "local-admin"
$env:ADMIN_USER_EMAIL = "admin@local.test"
$env:ENVIRONMENT = "dev"
$env:IS_LAMBDA = "false"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Para habilitar la sincronizacion Hikvision, configura tambien estas variables en la misma terminal antes de iniciar el backend:

```powershell
$env:HIKVISION_HOST = "192.168.1.139"
$env:HIKVISION_PORT = "80"
$env:HIKVISION_USERNAME = "admin"
$env:HIKVISION_USE_HTTPS = "false"
$env:HIKVISION_SYNC_ENABLED = "true"
$env:HIKVISION_SYNC_INTERVAL_SECONDS = "60"
$env:HIKVISION_PASSWORD = Read-Host "Contraseña de Hikvision"
```

La contrasena se solicita de forma interactiva y no se guarda en el repositorio.
Con `HIKVISION_SYNC_ENABLED=true`, el backend consulta el lector automaticamente cada 60 segundos y evita duplicar eventos.

El backend estará disponible en:

- API: http://127.0.0.1:8000
- Salud: http://127.0.0.1:8000/health
- Swagger/OpenAPI: http://127.0.0.1:8000/docs

### Frontend

Desde `app/frontend`, inicia Vite en la segunda terminal:

```powershell
Set-Location ".\app\frontend"
$env:BACKEND_PORT = "8000"
npm.cmd run dev -- --host 127.0.0.1 --port 3000
```

Abre http://127.0.0.1:3000 en el navegador.

El archivo `vite.config.ts` reenvía las solicitudes `/api` al backend configurado en `BACKEND_PORT`.

## Prueba rápida con datos de demostración

La demostración permite comprobar el flujo completo sin conectar un dispositivo Hikvision real.

1. Abre el frontend.
2. En el dashboard, usa la acción de preparación de datos de demostración.
3. La aplicación creará registros de acceso y ejecutará la liquidación de asistencia.
4. Revisa las pantallas de asistencia, aprobaciones, vacaciones, horas extra y nómina.
5. Para reiniciar únicamente los datos transaccionales de demostración, utiliza el endpoint `POST /api/v1/attendance/reset_demo`.

Los datos maestros de empleados, motivos y saldos se conservan al reiniciar las transacciones.

## API principal

La documentación interactiva completa está disponible en `/docs`. Las rutas más importantes son:

| Área | Endpoint base | Uso |
|---|---|---|
| Salud | `/health` | Comprobar disponibilidad del servidor |
| Autenticación | `/api/v1/auth` | Inicio y gestión de sesión |
| Asistencia | `/api/v1/attendance` | Carga, liquidación, ajustes y dashboard |
| Entidades | `/api/v1/entities/*` | Consulta y modificación de datos maestros |
| Aprobaciones | `/api/v1/attendance/approval/*` | Envío, aprobación y rechazo |
| Nómina | `/api/v1/attendance/payroll/*` | Cálculo de nómina |
| Hikvision | `/api/v1/attendance/hikvision/sync` | Sincronizar eventos del terminal por rango de fechas |
| Sincronización Usuarios | `/api/v1/entities/employees/sync-from-reader` | Sincronizar empleados desde el lector Hikvision |
| Foto Empleado | `/api/v1/entities/employees/{id}/upload-photo` | Subir foto de empleado |
| Configuración | `/api/v1/admin/settings` | Configuración administrativa |

## Comandos del frontend

Ejecuta estos comandos desde `app/frontend`:

```powershell
npm.cmd run dev       # Servidor de desarrollo
npm.cmd run build     # Compilación de producción
npm.cmd run lint      # Revisión de ESLint
npm.cmd run preview   # Previsualización del build
```

## Base de datos

El sistema usa **PostgreSQL** por defecto para desarrollo y producción.

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/timeledger
```

### Configuración de PostgreSQL

1. Instalar PostgreSQL 17 desde [postgresql.org](https://www.postgresql.org/download/windows/)
2. Crear la base de datos:
   ```sql
   CREATE DATABASE timeledger;
   ```
3. Configurar en `app/backend/.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/timeledger
   ```

### Acceso remoto seguro

Para acceder fuera de la red local, se recomienda:
- **Neon** (neon.tech) - PostgreSQL serverless gratuito
- **Supabase** (supabase.com) - Con API automática
- **Railway** (railway.app) - Fácil despliegue

La base local, los logs, los entornos virtuales, `node_modules`, los archivos `.env` y los builds están excluidos mediante `.gitignore`.

## Seguridad

- No subas archivos `.env`, tokens, claves privadas ni bases de datos con información real.
- Usa una clave `JWT_SECRET_KEY` segura y única en producción.
- Configura `ADMIN_USER_ID` y `ADMIN_USER_EMAIL` con los valores reales del entorno.
- Revisa los permisos del flujo de aprobación antes de usar el sistema con datos reales.

## Solución de problemas

### El backend falla indicando que falta `DATABASE_URL`

Define la variable antes de iniciar Uvicorn. En PowerShell, las variables se establecen con `$env:NOMBRE = "valor"`.

### El frontend no puede consultar la API

Comprueba que el backend está activo en el puerto 8000 y que `$env:BACKEND_PORT` coincide con ese puerto antes de iniciar Vite.

### `npm` aparece bloqueado por PowerShell

Usa `npm.cmd` en lugar de `npm`, como en los comandos de esta guía, o ejecuta PowerShell con una política de ejecución adecuada para tu entorno.

### El script `start_app_v2.sh` no funciona en Windows

Ese script está escrito para Bash. En Windows, utiliza los comandos PowerShell de esta guía o ejecútalo desde WSL/Git Bash con sus dependencias disponibles.

## Configuración Hikvision

Para conectar con el lector de acceso Hikvision, configura estas variables en `app/backend/.env`:

```env
HIKVISION_HOST=192.168.100.75      # IP del lector
HIKVISION_PORT=80                   # Puerto HTTP
HIKVISION_USERNAME=admin            # Usuario del lector
HIKVISION_PASSWORD=tu-contraseña    # Contraseña
HIKVISION_SYNC_ENABLED=true         # Sincronización automática
HIKVISION_SYNC_INTERVAL_SECONDS=30  # Intervalo de sincronización
HIKVISION_STREAM_ENABLED=true       # Push en tiempo real
HIKVISION_AUTO_PROVISION=true       # Auto-crear empleados nuevos
```

### Sincronización de empleados

El sistema puede sincronizar automáticamente los usuarios registrados en el lector Hikvision:

1. **Botón "Sincronizar Lector"** en Configuración > Empleados
2. O vía API: `POST /api/v1/entities/employees/sync-from-reader`

La sincronización:
- Crea empleados nuevos desde el lector
- Actualiza nombres de empleados existentes
- Marca el campo `face_registered` para usuarios con registro facial
- Usa el ID del lector como `emp_no` y `terminal_user_id`

## Campos de empleados

| Campo | Descripción |
|---|---|
| `emp_no` | Número de empleado (único) |
| `name` | Nombre completo |
| `department` | Departamento |
| `position` | Puesto |
| `role` | Rol: ceo, hr, manager, employee |
| `person_type` | Tipo: admin, employee |
| `terminal_user_id` | ID en el lector Hikvision |
| `face_registered` | Si tiene rostro registrado |
| `photo_url` | URL de la foto del empleado |
| `std_start` / `std_end` | Horario laboral |
| `hire_date` | Fecha de contratación |

## Estado actual

El proyecto se publica en:

https://github.com/SOFTWARE-BANK/attendace-payment-system

La documentación técnica detallada está disponible en [.wiki.md](.wiki.md) y [.atoms/ARCHITECTURE.md](.atoms/ARCHITECTURE.md).

### Últimas actualizaciones

- ✅ Migración a PostgreSQL como base de datos principal
- ✅ Sincronización automática con lectores Hikvision
- ✅ Gestión de empleados con foto y tipo de persona
- ✅ Deduplicación de registros al sincronizar
- ✅ Subida de fotos de empleados
- ✅ Interfaz mejorada con diseño moderno
- ✅ Menú móvil responsive
