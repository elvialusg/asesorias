# Tablero de Asesorías (Tesis) · Streamlit

Aplicación para registrar, consultar y exportar asesorías de tesis utilizando archivos Excel como fuente de datos. La interfaz replica el estilo de la Universidad de Manizales y ahora está organizada por capas para facilitar el mantenimiento.

## Arquitectura

```
asesorias_app/
+-- config.py              # Rutas, nombres de hojas y assets
+-- core/utils.py          # Helpers reutilizables (norm_str, append_pipe…)
+-- domains/models.py      # Dataclasses ligeras para tipos del dominio
+-- repositories/
¦   +-- excel_repository.py  # Lectura/escritura de Excel y plantillas
+-- services/
¦   +-- registro_service.py  # Lógica de negocio (guardar, modificar, historial…)
+-- ui/
    +-- app_shell.py       # Componentes Streamlit y tabs
    +-- theme.py           # Carga de estilos y sección hero
assets/styles.css          # CSS responsivo inspirado en el diseño adjunto
.streamlit/config.toml     # Tema global de Streamlit
app.py                     # Punto de entrada (invoca a la UI)
```

## Funcionalidades preservadas
- Formulario dinámico (facultad ? programa, múltiples asesorías).
- Autocompletar por cédula, edición y eliminación.
- Exportar registro actual e historial individual en Excel.
- Importar archivos masivos (`.xlsx`) y descargar plantilla.

## Ejecución local

```bash
python -m venv .venv
.venv\Scripts\activate  # o source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Coloca en `data/` los archivos:
- `Control_Asesorias_Tesis_template.xlsm`
- `registro_actual.xlsx` (se crea automáticamente si no existe).

## Despliegue

La app funciona en Streamlit Community Cloud o cualquier plataforma que soporte Python + Streamlit. Recuerda subir:
- Carpeta `data/` con el template.
- `app.py`, `requirements.txt`, `.streamlit/config.toml`, `assets/styles.css`.

> Si necesitas persistencia más robusta considera migrar a una BD (PostgreSQL/SQLite). El repositorio actual sigue utilizando Excel como almacenamiento principal.
