# Base de datos: `asesorias`

La aplicación está configurada para conectarse (por defecto) a `postgresql://postgres:postgres@localhost:5432/asesorias`. Si necesitas cambiarla, ajusta la variable de entorno `DATABASE_URL` antes de arrancar Streamlit.

## Esquema requerido

La aplicación crea automáticamente la tabla `registros_asesorias`, pero puedes crearla manualmente ejecutando el siguiente script:

```sql
CREATE TABLE IF NOT EXISTS registros_asesorias (
    id SERIAL PRIMARY KEY,
    nombre_facultad VARCHAR(255) NOT NULL DEFAULT '',
    nombre_programa VARCHAR(255) NOT NULL DEFAULT '',
    cedula VARCHAR(64),
    nombre_usuario VARCHAR(255),
    asesor_recursos_academicos VARCHAR(255),
    nombre_asesoria VARCHAR(255),
    modalidad VARCHAR(128),
    asesor_metodologico_detalle VARCHAR(255),
    titulo_trabajo_grado VARCHAR(255),
    fecha DATE,
    revision_inicial VARCHAR(128),
    revision_plantilla VARCHAR(128),
    ok_referencistas VARCHAR(128),
    ok_servicios VARCHAR(128),
    observaciones TEXT,
    escaneado_turnitin VARCHAR(128),
    porcentaje_similitud DOUBLE PRECISION,
    aprobacion_similitud VARCHAR(128),
    modalidad_programa VARCHAR(128),
    total_asesorias INTEGER NOT NULL DEFAULT 0,
    historial_asesorias TEXT,
    historial_asesor_recursos TEXT,
    historial_asesor_metodologico TEXT,
    historial_fechas TEXT,
    paz_y_salvo VARCHAR(128),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_registros_asesorias_cedula ON registros_asesorias (cedula);
CREATE INDEX IF NOT EXISTS idx_registros_asesorias_nombre ON registros_asesorias (lower(nombre_usuario));
```

> **Nota:** Los `created_at`/`updated_at` se administran automáticamente por SQLAlchemy; no necesitas triggers adicionales.
