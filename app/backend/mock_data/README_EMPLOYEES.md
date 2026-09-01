# 📋 Carga Masiva de Empleados

## Formato del Archivo

Crea un archivo JSON con la siguiente estructura:

```json
[
    {
        "emp_no": "EMP001",           // ID único del empleado (requerido)
        "name": "Nombre Completo",    // Nombre (requerido)
        "department": "Departamento", // Departamento (requerido)
        "position": "Puesto",         // Puesto (opcional)
        "role": "employee",           // Rol: admin, ceo, hr, manager, employee
        "email": "email@empresa.com", // Email (opcional)
        "pay_type": "monthly",        // Tipo: monthly, hourly
        "hourly_rate": 0,             // Tarifa por hora (si es hourly)
        "monthly_salary": 50000,      // Salario mensual (si es monthly)
        "pay_cycle": "monthly",       // Ciclo: weekly, biweekly, monthly
        "std_start": "09:00",         // Hora inicio jornada
        "std_end": "18:00",           // Hora fin jornada
        "break_minutes": 60,          // Minutos de descanso
        "grace_minutes": 10,          // Minutos de tolerancia
        "hire_date": "2024-01-15",    // Fecha contratación (YYYY-MM-DD)
        "annual_leave_days": 15,      // Días de vacaciones anuales
        "terminal_user_id": "HK001",  // ID en lector Hikvision (opcional)
        "manager_emp_no": "EMP000",   // ID del gerente (opcional)
        "active": true                // Activo: true/false
    }
]
```

## Valores para el campo `role`

| Valor | Descripción |
|-------|-------------|
| `admin` | Administrador del sistema |
| `ceo` | Director ejecutivo |
| `hr` | Recursos humanos |
| `manager` | Gerente/Supervisor |
| `employee` | Empleado regular |

## Valores para `pay_type`

| Valor | Descripción |
|-------|-------------|
| `monthly` | Salario mensual fijo |
| `hourly` | Pago por hora trabajada |

## Valores para `pay_cycle`

| Valor | Descripción |
|-------|-------------|
| `weekly` | Pago semanal |
| `biweekly` | Pago quincenal |
| `monthly` | Pago mensual |

## Cómo Cargar los Datos

### Opción 1: Carga automática al iniciar
1. Guarda tu archivo como `employees.json` en esta carpeta
2. El sistema cargará automáticamente los datos la primera vez que inicie

### Opción 2: Carga vía API
```bash
# Cargar un empleado
curl -X POST http://127.0.0.1:8000/api/v1/entities/employees \
  -H "Content-Type: application/json" \
  -d '{
    "emp_no": "EMP001",
    "name": "Nombre",
    "department": "Depto",
    "role": "employee"
  }'
```

### Opción 3: Usar el script de carga
```bash
python scripts/load_employees.json
```

## Ejemplo Completo

Ver `employees.json` para un ejemplo con 8 empleados de prueba.