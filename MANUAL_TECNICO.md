# Manual tecnico - ControlTesis

Fecha de documentacion: 2026-05-07

## 1. Resumen ejecutivo

ControlTesis es una aplicacion web en Python + Streamlit para registrar, consultar, asignar, normalizar, publicar y medir el avance de asesorias/tesis. La aplicacion trabaja con dos fuentes de datos:

- Google Sheets, cuando existe `GOOGLE_SHEETS_SPREADSHEET_ID`.
- Excel local, usando `data/registro_actual.xlsx`, cuando no hay configuracion de Google Sheets.

La arquitectura esta organizada por capas:

- `app.py`: punto de entrada Streamlit y carga de credenciales.
- `asesorias_app/config.py`: constantes globales, rutas, nombres de hojas, columnas y responsables.
- `asesorias_app/ui/`: interfaz Streamlit.
- `asesorias_app/services/`: reglas de negocio.
- `asesorias_app/repositories/`: persistencia en Excel o Google Sheets.
- `asesorias_app/auth/`: autenticacion, roles y usuarios.
- `assets/`: estilos y logos.
- `data/`: plantilla XLSM y base local XLSX.

El sistema es adecuado para operacion interna con volumen bajo/medio. Para alta concurrencia, trazabilidad institucional y escalabilidad real, debe migrarse a PostgreSQL y, preferiblemente, separar una API backend.

## 2. Objetivo funcional

La aplicacion administra el ciclo operativo de tesis:

1. Registrar estudiantes y datos de tesis.
2. Consultar, filtrar, editar y eliminar registros.
3. Importar registros masivamente desde Excel.
4. Exportar registros a Excel/CSV.
5. Distribuir tesis entre responsables de normalizacion.
6. Marcar normalizacion como pendiente u OK, con observaciones, revisor y fecha.
7. Pasar tesis normalizadas al flujo de publicacion.
8. Asignar tesis de publicacion entre responsables.
9. Marcar tesis como publicadas, con observaciones, responsable y fecha.
10. Consultar metricas de avance y descargar reportes.

## 3. Stack tecnologico

- Python 3.11 recomendado por `.devcontainer/devcontainer.json`.
- Streamlit para UI web y estado de sesion.
- Pandas para transformacion tabular.
- OpenPyXL para lectura de XLSM/XLSX.
- XlsxWriter para generar descargas Excel.
- Google API Client y Google Auth para Google Sheets.
- Plotly y Altair para visualizacion.
- ftfy para reparar textos con problemas de encoding.

Dependencias declaradas en `requirements.txt`:

```text
streamlit>=1.36
pandas>=2.2
openpyxl>=3.1
xlsxwriter>=3.2
google-api-python-client>=2.190
google-auth>=2.48
google-auth-httplib2>=0.3
plotly>=5.0.0
ftfy>=6.3
```

## 4. Ejecucion local

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La app abre por defecto en el puerto `8501`.

## 5. Estructura del proyecto

```text
.
|-- app.py
|-- README.md
|-- requirements.txt
|-- MANUAL_TECNICO.md
|-- asesorias-488318-60432dd8ea86.json
|-- .streamlit/
|   |-- config.toml
|   |-- secrets.toml
|   |-- service-account.json
|-- .devcontainer/
|   |-- devcontainer.json
|-- asesorias_app/
|   |-- __init__.py
|   |-- config.py
|   |-- auth/
|   |   |-- __init__.py
|   |   |-- service.py
|   |   |-- user_sheet_repository.py
|   |-- core/
|   |   |-- utils.py
|   |-- domains/
|   |   |-- models.py
|   |-- repositories/
|   |   |-- excel_repository.py
|   |   |-- google_sheets_repository.py
|   |-- services/
|   |   |-- registro_service.py
|   |-- ui/
|   |   |-- app_shell.py
|   |   |-- login.py
|   |   |-- theme.py
|-- assets/
|   |-- styles.css
|   |-- logo_biblioteca_umanizales_blanco.png
|   |-- logo_biblioteca_ycr_umanizales_blanco.png
|-- data/
|   |-- Control_Asesorias_Tesis_template.xlsm
|   |-- registro_actual.xlsx
|   |-- users.json
|-- scripts/
|   |-- generate_test_data.py
|-- app_old_backup.py
|-- tmp_*.py / temp*.txt / bytes.txt
```

## 6. Archivos principales

### `app.py`

Punto de entrada de Streamlit.

Responsabilidades:

- Configura la pagina con `st.set_page_config(page_title="Controltesis", layout="wide")`.
- Lee secretos desde `st.secrets`.
- Convierte `GOOGLE_SERVICE_ACCOUNT_JSON` en `.streamlit/service-account.json`.
- Inyecta `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_SHEETS_SPREADSHEET_ID` y `GOOGLE_SHEETS_REGISTRO_RANGE`.
- Actualiza valores del modulo `config` en runtime.
- Ejecuta `render_app()`.

Flujo:

```text
streamlit run app.py
  -> main()
  -> configure_google_credentials()
  -> render_app()
```

Riesgo: escribe credenciales en `.streamlit/service-account.json`. Ese archivo debe estar fuera de Git y protegido en despliegue.

### `asesorias_app/config.py`

Define el contrato global del sistema.

Incluye:

- Rutas: `BASE_DIR`, `DATA_DIR`, `TEMPLATE_PATH`, `DB_PATH`.
- Hojas: `Registro asesorias`, `Data_Facultades`, `Data_Programas`, `Insumo_Listas_Desplegables`.
- Assets: logos y CSS.
- Google Sheets: credenciales, rangos y scopes.
- Columnas de registro: `REGISTRO_COLUMNS`.
- Columnas de normalizacion y publicacion.
- Responsables por defecto.
- Alias de columnas para compatibilidad con versiones anteriores.

Si se agrega, elimina o renombra una columna, este archivo es el primer lugar que debe revisarse.

### `asesorias_app/core/utils.py`

Utilidades compartidas.

Funciones relevantes:

- `fix_text_encoding(value, strip=False)`: repara texto corrupto por encoding.
- `norm_str(value)`: convierte valores a string limpio o `None`.
- `normalize_fac_name(name)`: transforma nombres de facultad a formato con guiones bajos.
- `safe_int(value, default=0)`: conversion segura a entero.
- `append_pipe(existing, item)`: agrega valores separados por ` | ` sin duplicar.
- `split_hist(value)` y `join_hist(items)`: manejan historiales.
- `ensure_date(value)`: convierte valores a `datetime.date`.
- `clean_text_dataframe(df)`: limpia encabezados y celdas string de un DataFrame.

### `asesorias_app/domains/models.py`

Define dataclasses ligeras:

- `AsesoriaDetalle`.
- `RegistroFiltro`.
- `HistorialItem`.
- `HistorialTabla`.

Estado actual: la app usa principalmente diccionarios y DataFrames. Estos modelos pueden evolucionar a DTOs o esquemas Pydantic si se crea una API.

### `asesorias_app/repositories/excel_repository.py`

Repositorio para persistencia local en Excel.

Funciones principales:

- `normalize_registro_df(df)`: aplica alias, elimina columnas obsoletas y garantiza columnas esperadas.
- `load_lists()`: lee listas desplegables, facultades y programas desde el XLSM template.
- `ensure_db()`: crea `data/registro_actual.xlsx` si no existe.
- `load_registro()`: carga el Excel principal.
- `save_registro(df)`: guarda con archivo temporal y reemplazo atomico.
- `download_current_excel_bytes()`: genera descarga Excel.
- `build_bulk_template(columns)`: genera plantilla de importacion masiva.

Limitaciones:

- Excel no es transaccional.
- No soporta concurrencia real.
- Cada guardado reescribe el archivo completo.

### `asesorias_app/repositories/google_sheets_repository.py`

Extiende `ExcelRepository` para usar Google Sheets como fuente principal.

Funciones principales:

- `_execute_with_retry()`: reintentos con backoff para errores 429, 500, 502, 503 y 504.
- `_sheets_service()`: crea cliente Google Sheets.
- `load_registro()`: lee el rango de registro.
- `save_registro(df)`: limpia el rango y reescribe toda la tabla.
- `load_lists()`: usa el template local y puede reemplazar facultades/programas desde el rango `UM!A:ZZ`.
- `_format_value(value)`: serializa fechas, nulos y tipos Python.
- `_match_column()`: busqueda flexible de columnas.

Limitaciones:

- Cada guardado borra y reescribe el rango completo.
- No hay control optimista de concurrencia.
- Si dos usuarios guardan al tiempo, gana la ultima escritura.
- Google Sheets es util para operacion pequena/mediana, no para alta concurrencia.

### `asesorias_app/services/registro_service.py`

Capa principal de negocio.

Responsabilidades:

- Seleccionar repositorio: Google Sheets si hay `GOOGLE_SHEETS_SPREADSHEET_ID`, Excel si no.
- Cargar listas y registros.
- Guardar, actualizar, eliminar e importar registros.
- Distribuir tesis entre responsables.
- Gestionar normalizacion.
- Gestionar publicacion.
- Calcular metricas del dashboard.

Concurrencia:

- Usa `threading.RLock()` mediante `_write_locked`.
- Protege escrituras solo dentro de la misma instancia Python.
- No protege multiples servidores, multiples procesos ni ediciones externas en Google Sheets.

Funciones de registro:

- `find_student_index(df, cedula, nombre)`: busca por cedula o nombre.
- `add_registro(base_row, asesorias_payload)`: agrega estudiante si no existe.
- `update_registro(base_row, asesorias_payload)`: actualiza estudiante existente.
- `delete_registro(index_to_delete)`: elimina por indice.
- `update_row_by_index(index_to_update, row_data)`: actualiza campos por indice.
- `bulk_import(df_upload)`: importa Excel masivo y hace upsert por cedula/nombre.

Funciones de tesis:

- `_tesis_column(df)`: detecta columna de titulo de tesis.
- `_build_tesis_groups(df, thesis_col)`: agrupa estudiantes por tesis.
- `update_fields_for_tesis(thesis_value, field_values)`: actualiza campos compartidos de una tesis.

Distribucion:

- `distribute_registros(responsables, seed=None)`: reparte grupos de tesis entre responsables.
- Agrupa por titulo para mantener estudiantes de la misma tesis juntos.
- Asigna en round-robin despues de mezclar.

Normalizacion:

- `_load_registro_for_normalizacion()`: asegura columnas y defaults.
- `list_responsables()`: combina responsables por defecto y existentes.
- `get_registros_por_responsable(responsable)`: filtra asignados.
- `build_responsable_excel(responsable)`: exporta asignados.
- `summarize_normalizacion(df)`: total, OK y pendientes.
- `update_normalizacion_estado(responsable, updates)`: actualiza estado, observacion, revisor y fecha.

Publicacion:

- `_ensure_publicacion_columns(df)`: crea/rellena columnas.
- `_load_registro_for_publicacion()`: solo deja listos registros con normalizacion OK.
- `build_publicacion_tesis_dataframe(...)`: agrupa por tesis y calcula estado publicado.
- `build_publicacion_excel(...)`: exporta tesis para publicacion.
- `assign_publicacion(assigner, ids, target)`: reasigna tesis; solo responsable principal.
- `update_publicacion_estado(responsable, updates)`: marca tesis completas como publicadas o pendientes.
- `summarize_publicacion(df)`: total, publicadas, pendientes y asignadas.

Dashboard:

- `build_dashboard_dataframe()`: carga registros y convierte fechas.
- `filter_dashboard_dataframe(...)`: filtra por fecha, responsable y estados.
- `calculate_dashboard_metrics(df)`: calcula KPIs, pipeline, productividad, calidad y tiempos.
- `dashboard_stage_masks(df)`: mascaras por etapa.

### `asesorias_app/auth/service.py`

Autenticacion y autorizacion.

Responsabilidades:

- Cargar usuarios desde Google Sheets.
- Autenticar usuario y clave.
- Hashear claves con PBKDF2-HMAC-SHA256.
- Soportar claves legacy en texto plano cuando no parecen hash PBKDF2.
- Gestionar cambio de clave, token de recuperacion y clave inicial.
- Definir permisos por rol.

Constantes:

- `PASSWORD_ITERATIONS = 390_000`.
- `RESET_TOKEN_TTL = 3600`.
- `ROLE_FEATURES`: matriz de acceso por rol.

Roles:

- `administrador`: todo.
- `direccion` / `dirección`: registro, consulta, normalizacion, publicacion y dashboard.
- `normalizacion`: registro, consulta, normalizacion y dashboard.
- `referencista`: registro, consulta, normalizacion, publicacion y dashboard.
- `publicacion`: registro, consulta, publicacion y dashboard.
- `servicios`: registro, consulta y dashboard.
- `colaborador`: registro y consulta.

Punto importante: la autenticacion depende de Google Sheets. Si no existe `GOOGLE_SHEETS_SPREADSHEET_ID`, el registro puede caer a Excel, pero el login no tiene repositorio funcional.

### `asesorias_app/auth/user_sheet_repository.py`

Repositorio de usuarios en Google Sheets.

Columnas esperadas:

```text
email | name | role | password_hash | must_reset | reset_token | reset_token_expire
```

Funciones:

- `_normalize_header(name)`: acepta alias como `correo`, `contraseña`, `clave`, `rol`.
- `load_users()`: lee usuarios desde `User!A:ZZ`.
- `save_users(records)`: reescribe usuarios.

Riesgos:

- Reescribe toda la hoja.
- No hay auditoria.
- Google Sheets no es ideal como almacen de identidad a largo plazo.

### `asesorias_app/ui/login.py`

Interfaz de login y sesion.

Responsabilidades:

- Renderizar login.
- Guardar usuario autenticado en `st.session_state`.
- Expirar sesion por inactividad.
- Bloquear temporalmente despues de intentos fallidos.
- Renderizar header/footer de sesion.

Constantes:

- `SESSION_TIMEOUT_SECONDS = 3600`.
- `MAX_LOGIN_ATTEMPTS = 5`.
- `LOGIN_LOCK_SECONDS = 15 * 60`.

Limitacion: `LOGIN_FAILURES` vive en memoria. Si la app reinicia o hay multiples replicas, los bloqueos no son globales.

### `asesorias_app/ui/theme.py`

Carga `assets/styles.css` e inyecta CSS global con Streamlit.

### `asesorias_app/ui/app_shell.py`

Archivo principal de UI. Contiene navegacion, formularios y llamadas a `RegistroService`.

Menus:

- Registrar tesis.
- Consultar registros.
- Normalizacion.
- Publicacion.
- Metricas.

El menu se filtra con `auth_service.can_access_feature(user, feature)`.

Funciones internas relevantes:

- `_reset_form(meta)`: limpia widgets.
- `_ensure_dynamic_defaults(meta)`: defaults para asesorias y estudiantes adicionales.
- `_prefill_form_from_registro(...)`: precarga datos al editar.
- `_load_existing_registro_for_edit(...)`: busca registro existente.
- `_autofill_by_cedula(...)`: autocompleta por documento.
- `_merge_form_values_over_existing(...)`: evita pisar datos existentes con vacios.
- `_with_shared_tesis_values(...)`: trae datos compartidos desde filas con la misma tesis.

## 7. Funcionalidades por modulo

### Registrar tesis

Funcion: `_tab_registro()`.

Capacidades:

- Seleccionar facultad y programa dependiente.
- Seleccionar modalidad del programa.
- Agregar estudiantes adicionales.
- Capturar documento, nombre, correo, asesor metodologico, titulo y fecha.
- Capturar revision inicial, revision plantilla, Turnitin, OK servicios, OK referencistas, similitud, aprobacion, observaciones y paz y salvo.
- Guardar nuevo registro.
- Cargar registro existente para modificar.
- Descargar tutorial PDF si existe `Tutorial Control Tesis.pdf`.

Reglas:

- Documento, nombre y correo del estudiante principal son obligatorios.
- Estudiantes adicionales requieren documento, nombre y correo si se empiezan a llenar.
- Si varios estudiantes comparten tesis, se crean filas separadas con datos comunes.

### Consultar registros

Funcion: `_tab_consulta()`.

Capacidades:

- Cargar registro completo.
- Buscar por texto.
- Mostrar resultados.
- Descargar registro actual.
- Descargar plantilla de importacion masiva.
- Importar archivo Excel masivo.
- Eliminar registros.
- Enviar registros a edicion.
- Distribuir registros entre responsables de normalizacion.

Nota: la busqueda trabaja sobre el DataFrame cargado completo en memoria.

### Normalizacion

Funcion: `_tab_normalizacion()`.

Capacidades:

- Seleccionar responsable.
- Ver metricas total/pendiente/OK.
- Descargar registros asignados.
- Editar tabla con check `Revisado` y observacion.
- Guardar avances.

Reglas:

- Solo actualiza filas asignadas al responsable seleccionado.
- Si marca OK, registra `Revisado_por` y `Fecha_revision`.
- Si desmarca OK, limpia revisor y fecha.

### Publicacion

Funcion activa: `_tab_publicacion_v3()`.

Tambien existen `_tab_publicacion()` y `_tab_publicacion_v2()`, pero el enrutador usa `v3`.

Capacidades:

- Muestra solo tesis con `Estado_Normalizacion = OK`.
- Agrupa por tesis, no por estudiante individual.
- Muestra total listo, pendientes, publicados y asignaciones.
- Permite seleccionar responsable activo.
- La responsable principal puede ver todos los pendientes.
- Permite descargar Excel de publicacion.
- Permite marcar tesis como publicada o pendiente.
- Permite registrar observacion.
- Permite reasignar tesis pendientes desde responsable principal a responsable secundaria.

Reglas:

- Publicar una tesis actualiza todas las filas asociadas a esa tesis.
- Solo el responsable asignado puede guardar cambios.
- Solo `PUBLICATION_PRIMARY` puede reasignar.

### Metricas

Funcion: `_tab_dashboard()`.

Capacidades:

- Filtrar por rango de fechas.
- Filtrar por responsable.
- Filtrar por etapa: registradas, en proceso, normalizadas, con observaciones, publicadas.
- Mostrar KPIs.
- Graficar distribucion por etapa con Plotly.
- Descargar metricas en Excel y CSV.

Metricas:

- Total registradas.
- En proceso.
- Normalizadas.
- Con observaciones.
- Publicadas.
- Porcentaje de avance.
- Pipeline.
- Productividad de normalizacion/publicacion.
- Calidad y retrabajos.
- Tiempos promedio.

## 8. Modelo de datos operativo

La fuente principal es una tabla plana. Cada fila representa principalmente un estudiante asociado a una tesis.

Cuando una tesis tiene varios estudiantes:

- Se crean varias filas.
- Comparten campos de tesis, programa, revision y publicacion.
- Las operaciones de publicacion agrupan por titulo de tesis.

Columnas de identidad:

- `Cédula`.
- `Nombre_Usuario`.
- `Correo_Electronico`.

Columnas academicas:

- `Nombre_Facultad`.
- `Nombre_Programa`.
- `Modalidad del Programa`.
- `Asesor metodológico`.
- `Título_Trabajo_Grado`.
- `Fecha`.

Columnas de revision:

- `Revisión Inicial`.
- `Revisión plantilla`.
- `Ok_Referencistas`.
- `OK_Servicios`.
- `Observaciones`.
- `Escaneado Turnitin`.
- `% similitud`.
- `Aprobación_Similitud`.
- `Paz_y_Salvo`.

Columnas de normalizacion:

- `Asignado_a`.
- `Estado_Normalizacion`.
- `Revisado_por`.
- `Fecha_revision`.
- `Observacion_Normalizacion`.

Columnas de publicacion:

- `Asignado_Publicacion`.
- `Estado_Publicacion`.
- `Publicado_por`.
- `Fecha_Publicacion`.
- `Observacion_Publicacion`.

Estados:

- Normalizacion pendiente: `Pendiente`.
- Normalizacion aprobada: `OK`.
- Publicacion pendiente: `Pendiente`.
- Publicacion completa: `Publicado`.

## 9. Flujo de datos

Carga inicial:

```text
app.py
  -> configure_google_credentials()
  -> render_app()
  -> load_theme()
  -> login_ui.get_current_user()
  -> si no hay usuario: render_login_page()
  -> si hay usuario: RegistroService()
  -> service.load_lists()
  -> _render_tabs()
```

Seleccion de repositorio:

```text
RegistroService.__init__()
  -> si config.GOOGLE_SHEETS_SPREADSHEET_ID existe: GoogleSheetsRepository()
  -> si no existe: ExcelRepository()
```

Guardado de registro:

```text
_tab_registro()
  -> construye base_row_template
  -> valida documento, nombre y correo
  -> service.add_registro() o service.update_row_by_index()
  -> repo.save_registro()
```

Importacion masiva:

```text
_tab_consulta()
  -> st.file_uploader()
  -> pandas.read_excel(uploaded_file)
  -> service.bulk_import(df_upload)
  -> normalize_registro_df()
  -> upsert por cedula/nombre
  -> save_registro()
```

Distribucion:

```text
_tab_consulta()
  -> service.distribute_registros(responsables)
  -> valida filas con cedula o nombre
  -> detecta columna de tesis
  -> agrupa estudiantes por tesis
  -> asigna responsable en round-robin
  -> guarda Asignado_a
```

Normalizacion:

```text
_tab_normalizacion()
  -> service.get_registros_por_responsable()
  -> st.data_editor()
  -> service.update_normalizacion_estado(responsable, updates)
```

Publicacion:

```text
_tab_publicacion_v3()
  -> service.build_publicacion_tesis_dataframe()
  -> solo Estado_Normalizacion = OK
  -> agrupa por tesis
  -> st.data_editor()
  -> service.update_publicacion_estado(responsable, updates)
```

Dashboard:

```text
_tab_dashboard()
  -> service.build_dashboard_dataframe()
  -> filtros UI
  -> service.filter_dashboard_dataframe()
  -> service.calculate_dashboard_metrics()
```

## 10. Autenticacion y autorizacion

La autenticacion usa una hoja `User` de Google Sheets.

Campos requeridos:

```text
email | name | role | password_hash | must_reset | reset_token | reset_token_expire
```

Flujo:

```text
render_login_page()
  -> auth_service.authenticate(email, password)
  -> UserSheetRepository.load_users()
  -> _password_matches()
  -> AuthUser
  -> st.session_state[tf_auth_user]
```

Seguridad actual:

- PBKDF2 con 390.000 iteraciones para claves nuevas.
- Tokens de reseteo con `secrets.token_urlsafe(32)`.
- Sesion expira por inactividad de 1 hora.
- Bloqueo de 15 minutos despues de 5 intentos fallidos.
- Autorizacion por rol en menu.

Limitaciones:

- No hay 2FA.
- No hay auditoria de login.
- Bloqueos de login viven en memoria.
- Google Sheets no es ideal como almacen de identidad.
- No hay SSO institucional.

## 11. Configuracion y secretos

Variables/secretos esperados:

- `GOOGLE_SERVICE_ACCOUNT_JSON`: JSON completo de cuenta de servicio.
- `GOOGLE_APPLICATION_CREDENTIALS`: ruta local al JSON, alternativa a `GOOGLE_SERVICE_ACCOUNT_JSON`.
- `GOOGLE_SHEETS_SPREADSHEET_ID`: ID de hoja.
- `GOOGLE_SHEETS_REGISTRO_RANGE`: default `Registro asesorias!A:ZZ`.
- `GOOGLE_SHEETS_USERS_RANGE`: default `User!A:ZZ`.
- `GOOGLE_SHEETS_FACULTIES_RANGE`: default `UM!A:ZZ`.

Buenas practicas:

- No versionar `.streamlit/secrets.toml`.
- No versionar `.streamlit/service-account.json`.
- No versionar archivos `asesorias-*.json`.
- Compartir el Google Sheet con el email de la cuenta de servicio.
- Dar permisos minimos necesarios.

## 12. Escalabilidad actual

Escala razonablemente para:

- Pocos o moderados usuarios internos.
- Cientos o algunos miles de filas.
- Reportes y descargas ocasionales.
- Google Sheets como backend de bajo costo.
- Excel local para pruebas/desarrollo.

No escala bien para:

- Muchas escrituras concurrentes.
- Decenas de miles de registros.
- Multiples instancias escribiendo al mismo Google Sheet.
- Auditoria robusta.
- Permisos granulares por registro.
- Integraciones externas o API publica.

Cuellos de botella:

- `save_registro()` en Google Sheets borra y reescribe todo el rango.
- Los DataFrames se cargan completos en memoria.
- Se usa indice de fila como identificador temporal.
- No hay ID persistente activo por tesis/registro.
- No hay locks distribuidos.

## 13. Ambicion del proyecto

El proyecto ya cubre un flujo operativo completo:

- Captura.
- Consulta.
- Edicion.
- Importacion/exportacion.
- Asignacion de trabajo.
- Estados de proceso.
- Control por responsables.
- Agrupacion por tesis.
- Dashboard ejecutivo.
- Login por roles.

La arquitectura modular permite evolucionar, pero Excel/Google Sheets limitan el crecimiento. La version actual debe verse como MVP interno funcional, no como arquitectura institucional final.

## 14. Migracion a base de datos real

Recomendacion: PostgreSQL.

Modelo relacional propuesto:

```text
users
- id uuid pk
- email unique
- name
- role
- password_hash
- must_reset
- reset_token_hash
- reset_token_expire
- created_at
- updated_at

faculties
- id uuid pk
- code unique
- name

programs
- id uuid pk
- faculty_id fk
- code
- name

theses
- id uuid pk
- title
- faculty_id fk
- program_id fk
- program_modality
- methodological_advisor
- registration_date
- revision_initial
- revision_template
- ok_referencistas
- ok_servicios
- observations
- turnitin_scanned
- similarity_percent
- similarity_approval
- paz_y_salvo
- created_at
- updated_at

students
- id uuid pk
- document unique
- full_name
- email
- created_at
- updated_at

thesis_students
- thesis_id fk
- student_id fk
- primary key(thesis_id, student_id)

normalization_assignments
- id uuid pk
- thesis_id fk
- assigned_to_user_id fk
- status
- reviewed_by_user_id fk
- reviewed_at
- observation
- created_at
- updated_at

publication_assignments
- id uuid pk
- thesis_id fk
- assigned_to_user_id fk
- status
- published_by_user_id fk
- published_at
- observation
- created_at
- updated_at

audit_events
- id uuid pk
- actor_user_id fk
- entity_type
- entity_id
- action
- before_json
- after_json
- created_at
```

Estrategia de migracion:

1. Crear `PostgresRepository` con metodos equivalentes a los repositorios actuales.
2. Agregar IDs persistentes: `registro_id`, `thesis_id` o ambos.
3. Migrar datos desde Excel/Google Sheets normalizando con `normalize_registro_df()`.
4. Cambiar escrituras completas por `INSERT`, `UPDATE`, `DELETE` o soft delete.
5. Usar transacciones para importacion masiva.
6. Agregar migraciones con Alembic.
7. Agregar auditoria.

Herramientas recomendadas:

- SQLAlchemy.
- Alembic.
- Pydantic.
- pytest.

## 15. Migracion a servidor real

### Opcion A: Streamlit + PostgreSQL

```text
Usuario -> Streamlit App -> PostgreSQL
```

Ventajas:

- Menos reescritura.
- Rapido de implementar.
- Suficiente para herramienta interna.

Requisitos:

- Hosting Python persistente.
- Variables de entorno seguras.
- HTTPS.
- PostgreSQL gestionado.
- Backups automaticos.

### Opcion B: Frontend + API + PostgreSQL

```text
Usuario -> Frontend web -> FastAPI -> PostgreSQL
```

Ventajas:

- Escala mejor.
- Permite integraciones.
- Mejor autenticacion.
- Mejor testabilidad.
- Separacion clara de permisos.

### Opcion C: Hibrida

```text
Streamlit -> FastAPI -> PostgreSQL
```

Es la ruta pragmatica si se quiere conservar la UI actual mientras se robustecen datos y seguridad.

## 16. Pruebas recomendadas

Actualmente no se detecta suite de tests formal.

Pruebas unitarias prioritarias:

- `normalize_registro_df()`.
- `fix_text_encoding()`.
- `find_student_index()`.
- `_tesis_column()`.
- `_build_tesis_groups()`.
- `distribute_registros()`.
- `bulk_import()`.
- `update_normalizacion_estado()`.
- `update_publicacion_estado()`.
- `calculate_dashboard_metrics()`.
- `auth_service._hash_password()` y `_verify_password()`.

Pruebas de integracion:

- Repositorio Excel con archivo temporal.
- Repositorio Google Sheets mockeando cliente Google.
- Flujo registro -> normalizacion -> publicacion -> dashboard.

## 17. Riesgos tecnicos actuales

1. Concurrencia: Google Sheets/Excel no garantizan transacciones.
2. Identidad de filas: se usa indice de DataFrame en varias operaciones.
3. Escritura completa: cada guardado reescribe la tabla completa.
4. Encoding: hay mojibake visible en codigo y posiblemente datos.
5. Secretos: existen archivos de credenciales locales.
6. UI grande: `app_shell.py` concentra demasiadas responsabilidades.
7. Funciones duplicadas: hay tres versiones de publicacion.
8. Archivos temporales: hay `tmp_*.py`, `temp*.txt` y backups.
9. Sin tests automatizados.
10. Sin auditoria.

## 18. Recomendaciones de mantenimiento

Prioridad alta:

1. Verificar `.gitignore` para excluir secretos, temporales y archivos Office lock (`~$*.xlsm`).
2. Eliminar o archivar `tmp_*.py`, `temp*.txt`, `bytes.txt` y backups no necesarios.
3. Crear tests para `RegistroService` y repositorios.
4. Agregar un ID persistente por registro o tesis.
5. Normalizar encoding de archivos fuente a UTF-8.

Prioridad media:

1. Separar `app_shell.py` en `registro.py`, `consulta.py`, `normalizacion.py`, `publicacion.py`, `dashboard.py`.
2. Eliminar versiones no usadas de publicacion si `v3` es definitiva.
3. Crear script real de datos de prueba.
4. Documentar estructura exacta de Google Sheets requerida.
5. Agregar logs estructurados.

Prioridad futura:

1. Migrar a PostgreSQL.
2. Separar backend/API.
3. Integrar SSO.
4. Agregar auditoria.
5. Implementar CI/CD.

## 19. Guia para agregar una nueva funcionalidad

Ejemplo: agregar `Repositorio_URL` para tesis.

1. Agregar columna en `config.REGISTRO_COLUMNS`.
2. Agregar alias en `COLUMN_ALIASES` si hay nombres alternos.
3. Agregar input en `_tab_registro()`.
4. Incluir campo en `base_row_template`.
5. Agregar a `_shared_tesis_form_fields()` si aplica a toda la tesis.
6. Actualizar consulta/exportacion si debe mostrarse.
7. Actualizar importacion masiva si requiere validacion.
8. Agregar pruebas.
9. Si se usa Google Sheets, agregar columna en la hoja.
10. Si se usa Excel, actualizar plantilla o dejar que `normalize_registro_df()` cree la columna.

## 20. Problemas comunes

### La app no inicia

Revisar:

- Dependencias instaladas.
- Version de Python.
- Existencia de `data/Control_Asesorias_Tesis_template.xlsm`.
- Errores de encoding.

### No carga login

Revisar:

- `GOOGLE_SHEETS_SPREADSHEET_ID`.
- Cuenta de servicio compartida con la hoja.
- Rango `User!A:ZZ`.
- Columnas de usuarios.

### No guarda registros

Revisar:

- Permisos de escritura en Google Sheets.
- Permisos sobre `data/registro_actual.xlsx` si usa Excel.
- Archivo Excel no abierto en otra aplicacion.
- Errores por columnas faltantes.

### No aparecen programas

Revisar:

- `Data_Facultades`.
- `Data_Programas`.
- Columna `Codigo_Facultad` o variante con tilde.
- `GOOGLE_SHEETS_FACULTIES_RANGE`.

### Publicacion no muestra registros

Revisar:

- `Estado_Normalizacion` debe ser `OK`.
- Debe existir titulo de tesis detectable.
- Columnas de publicacion deben existir o poder crearse.
- Responsable seleccionado debe coincidir con `Asignado_Publicacion`.

### Dashboard vacio

Revisar:

- Hay registros en la fuente.
- `Fecha` se puede convertir a fecha.
- Filtros no excluyen todo.

## 21. Contrato minimo de Google Sheets

Hojas recomendadas:

```text
Registro asesorias
User
UM
```

`Registro asesorias`:

- Primera fila: encabezados.
- Debe contener o permitir crear las columnas de `config.REGISTRO_COLUMNS`.

`User`:

- Primera fila: encabezados.
- Debe incluir email, nombre, rol y password/hash.

`UM`:

- Debe contener facultades y programas.
- Columnas detectables: `Nombre_Facultad`, `Codigo_Facultad`, `Nombre_Programa`.

Permisos:

- Compartir el Google Sheet con el email de la cuenta de servicio.
- Permiso de editor si la app debe escribir.

## 22. Estado de calidad

Fortalezas:

- Separacion por capas ya iniciada.
- Repositorios intercambiables Excel/Google Sheets.
- Normalizacion de columnas centralizada.
- Reparacion de encoding de datos.
- Hasheo de claves nuevas con PBKDF2.
- Roles y menu filtrado.
- Flujo completo de proceso institucional.

Debilidades:

- UI muy concentrada en un archivo.
- Persistencia no transaccional.
- Sin tests automatizados.
- Sin auditoria.
- Sin IDs persistentes robustos.
- Secretos locales presentes en el workspace.
- Archivos temporales y backups en raiz.

## 23. Handoff para ingeniero junior

Antes de tocar codigo:

1. Ejecutar la app localmente.
2. Revisar `config.py`.
3. Leer `RegistroService`; ahi estan las reglas reales.
4. Leer `ExcelRepository` y `GoogleSheetsRepository`.
5. Leer `_render_tabs()` en `app_shell.py`.
6. No modificar credenciales ni secretos.
7. No borrar columnas de Google Sheets sin actualizar `config.REGISTRO_COLUMNS`.
8. No confiar en indices de DataFrame como IDs permanentes.
9. Crear backup de la hoja antes de cambios masivos.
10. Agregar tests antes de refactorizaciones grandes.

Para cambios pequenos:

- Visuales: `assets/styles.css` y funciones `_inject_*` en `app_shell.py`.
- Campos: `config.py`, `_tab_registro()`, servicios y repositorios.
- Permisos: `auth/service.py`, `ROLE_FEATURES`.
- Responsables: `config.DEFAULT_ASSIGNMENT_PEOPLE` y `config.PUBLICATION_RESPONSIBLES`.
- Google Sheets: variables de entorno/secrets y rangos en `config.py`.

## 24. Proxima arquitectura recomendada

Ruta pragmatica:

1. Limpiar repositorio y secretos.
2. Agregar tests.
3. Agregar IDs persistentes.
4. Dividir UI por modulo.
5. Crear `PostgresRepository` manteniendo interfaz DataFrame.
6. Migrar datos desde Google Sheets.
7. Cambiar guardados completos por updates por ID.
8. Agregar auditoria.
9. Evaluar FastAPI si aparecen integraciones o mayor concurrencia.

## 25. Conclusion tecnica

ControlTesis esta bien encaminado como aplicacion interna Streamlit para controlar el ciclo de tesis. La separacion entre UI, servicios y repositorios permite evolucionar sin reescribir todo desde cero. Su principal deuda tecnica esta en la persistencia: Excel/Google Sheets son practicos, pero no ofrecen garantias suficientes para concurrencia, auditoria y crecimiento institucional.

El siguiente salto de madurez es conservar la logica de negocio existente, introducir identificadores persistentes, agregar pruebas y reemplazar gradualmente la fuente tabular por PostgreSQL.
