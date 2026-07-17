# Auditoría de arquitectura

**Proyecto:** ControlTesis  
**Fecha:** 2026-07-16  
**Rama de trabajo:** `refactor/arquitectura-profesional`  
**Base:** `main` actualizada desde `origin/main` hasta `7edd3ad`  
**Alcance de esta fase:** diagnóstico y plan. No se modificó código funcional, no se eliminó ningún archivo y no se escribieron datos en Google Sheets.

## 1. Resumen ejecutivo

La aplicación ya tiene una separación inicial entre entrada, autenticación, repositorios, servicios y UI. El punto de entrada es único (`app.py`) y la UI no llama directamente a Google Sheets. Sin embargo, la separación no llega todavía a los casos de uso:

- `asesorias_app/ui/app_shell.py` tiene 2.428 líneas y contiene navegación, estado de sesión, validación, búsquedas, composición de registros, reglas de edición, métricas, HTML/CSS/JavaScript y siete páginas funcionales.
- `asesorias_app/services/registro_service.py` tiene 1.254 líneas y reúne registro, consulta parcial, importación, distribución, normalización, publicación, exportación y métricas.
- Los servicios dependen de repositorios concretos y de `pandas`; no existe un contrato de repositorio que permita aislar la infraestructura.
- Las escrituras de Google Sheets reemplazan el rango completo mediante `clear` y `update`. Esto crea una ventana en la que la hoja puede quedar vacía y permite pérdida de actualizaciones concurrentes.
- Hay datos personales y artefactos temporales versionados. `.streamlit/secrets.toml` estuvo versionado en el historial, por lo que la credencial asociada debe rotarse.
- No hay carpeta `tests/`, `pytest` no está instalado y no existe cobertura automática de los flujos críticos.

La refactorización debe ser incremental. Antes de dividir archivos se necesita congelar el comportamiento con pruebas de caracterización y proteger el repositorio y las escrituras.

## 2. Estado de Git al iniciar

Se ejecutó la secuencia solicitada:

```text
git switch main
git pull origin main
git switch -c refactor/arquitectura-profesional
```

`main` estaba 17 commits por detrás de `origin/main` y se actualizó por *fast-forward*. La rama nueva quedó limpia. No se trabajó sobre `main`.

## 3. Estructura actual

```text
.
├── app.py
├── app_old_backup.py
├── asesorias_app/
│   ├── auth/
│   │   ├── service.py
│   │   └── user_sheet_repository.py
│   ├── core/utils.py
│   ├── domains/models.py
│   ├── repositories/
│   │   ├── excel_repository.py
│   │   └── google_sheets_repository.py
│   ├── services/registro_service.py
│   ├── ui/
│   │   ├── app_shell.py
│   │   ├── login.py
│   │   └── theme.py
│   └── config.py
├── assets/
├── data/
├── scripts/
├── .streamlit/
├── README.md
├── MANUAL_TECNICO.md
├── requirements.txt
├── bytes.txt
├── temp.txt
├── temp_dashboard_block.txt
└── tmp_*.py
```

No existe `tests/`. Los directorios no contienen `__init__.py` de forma consistente fuera de `auth`, aunque funcionan como paquetes de espacio de nombres en Python moderno.

## 4. Responsabilidad actual por archivo

### Código de ejecución

| Archivo | Responsabilidad observada | Observación |
|---|---|---|
| `app.py` | Configura Streamlit, lee `st.secrets`, materializa la credencial de Google y llama a `render_app()` | Punto de entrada correcto, pero mezcla *bootstrap* con manejo de secretos y escribe una clave privada en disco. Importa `auth_service` sin usarlo. |
| `asesorias_app/config.py` | Rutas, rangos, nombres de hojas/columnas, roles operativos y valores de estados | Mezcla configuración de infraestructura, esquema persistente y constantes de negocio. Tiene una ruta predeterminada con nombre específico de credencial. |
| `asesorias_app/core/utils.py` | Fechas de Bogotá, reparación de texto, normalización, historial y serialización de fechas | Responsabilidad amplia pero reutilizable. Los `except Exception` de conversión ocultan causas. |
| `asesorias_app/domains/models.py` | Cuatro `dataclass` de asesoría, filtro e historial | Ninguna clase es usada fuera del propio archivo; hoy es código muerto o un diseño abandonado. |
| `asesorias_app/repositories/excel_repository.py` | Lee plantilla/listas, crea y reemplaza el Excel local, exporta archivos | Combina catálogo/listas, almacenamiento local, normalización de esquema y exportación. Es también clase base del repositorio de Sheets. |
| `asesorias_app/repositories/google_sheets_repository.py` | Autentica con Google, lee registro y facultades, reemplaza el registro completo | Hereda detalles Excel que no pertenecen a Sheets. No ofrece operaciones granulares ni control de concurrencia. |
| `asesorias_app/auth/user_sheet_repository.py` | Lee y reemplaza la hoja de usuarios | Duplica creación del cliente Google y reintentos. Reescribe la hoja completa. |
| `asesorias_app/auth/service.py` | Hash/verificación de contraseñas, autenticación, recuperación, usuarios y permisos | Usa un repositorio global concreto. Admite contraseñas no hasheadas por compatibilidad. Los tokens de recuperación se guardan directamente en Sheets. |
| `asesorias_app/services/registro_service.py` | Todos los flujos y exportaciones del registro | Monolito de 1.254 líneas; depende de repositorios concretos y contiene trazas con datos sensibles. |
| `asesorias_app/ui/login.py` | Login, bloqueo de intentos, sesión, logout y pie de usuario | Autenticación y presentación están parcialmente separadas, pero el bloqueo es memoria local del proceso y el logout no limpia el estado funcional. |
| `asesorias_app/ui/theme.py` | Inyecta el CSS activo | Responsabilidad clara. |
| `asesorias_app/ui/app_shell.py` | Navegación, páginas, widgets, estado, reglas de formulario, búsquedas, métricas, HTML/CSS/JS | Monolito de 2.428 líneas. Contiene reglas de negocio y tres versiones de Publicación; solo `v3` está enrutada. |
| `asesorias_app/__init__.py`, `auth/__init__.py` | Marcadores de paquete | Sin lógica. |

### Datos, recursos y documentación

| Archivo | Responsabilidad / estado | Observación |
|---|---|---|
| `assets/styles.css` | Estilo activo | Debe preservarse sin cambios visuales. |
| `assets/*.png` | Logos de login y menú | Activos; no eliminar. |
| `assets/*.pdf` | Dos descargas visibles desde Registro | Activos; no eliminar. |
| `data/Control_Asesorias_Tesis_template.xlsm` | Plantilla, listas y respaldo de esquema | Activo, pero su hoja de registro contiene 296 filas no vacías y datos personales; debe producirse una plantilla sanitizada equivalente. |
| `data/registro_actual.xlsx` | Fallback/local de registro | Está versionado pese a estar en `.gitignore`; contiene 100 filas con datos personales. |
| `data/users.json` | Almacén histórico/local de usuarios | Está versionado pese a estar en `.gitignore`; contiene 11 perfiles con nombres/correos y hashes PBKDF2. El código actual no lo usa. |
| `data/~$Control_Asesorias_Tesis_template.xlsm` | Archivo temporal de Office | Versionado; candidato claro a retiro tras la fase formal de limpieza. |
| `README.md` | Instalación y arquitectura anterior | Desactualizado: describe Excel como persistencia principal y no documenta todos los flujos actuales. |
| `MANUAL_TECNICO.md` y `.docx` | Manual técnico amplio | Reconoce varios problemas actuales, pero no sustituye documentación modular y operativa. |
| `TUTORIAL_USO_APP.docx`, `Tutorial Control Tesis.docx` | Fuentes editables de documentación | No son las descargas usadas por la aplicación; confirmar su proceso de mantenimiento antes de decidir si permanecen. |
| `.streamlit/config.toml` | Tema/configuración Streamlit | Activo. |
| `.devcontainer/devcontainer.json`, `.pythonrc` | Entorno de desarrollo | Revisar vigencia; no son código funcional. |
| `requirements.txt` | Dependencias de producción | No incluye herramientas de prueba. `altair` se importa directamente pero solo llega de forma transitiva a través de Streamlit. |

### Temporales, respaldo y scripts

| Archivo | Hallazgo | Decisión en esta fase |
|---|---|---|
| `app_old_backup.py` | Copia monolítica antigua de 780 líneas; no es importada | Candidato a retiro, pendiente del reporte formal de limpieza. |
| `tmp_script.py` | Diagnóstico real de Sheets; incluye ID de hoja y muestra filas en consola | Candidato prioritario a retiro. |
| `tmp_sheet_test.py` | Prueba manual con ruta personal a una credencial e ID de hoja | Candidato prioritario a retiro. |
| `tmp_edit_config.py` | Script de reescritura puntual de `config.py` | Desechable; no forma parte del mantenimiento normal. |
| `tmp_fix_ascii.py`, `tmp_replace_fix.py` | Reparaciones puntuales de texto | Desechables. |
| `tmp_codes.py`, `tmp_print.py`, `tmp_repr.py` | Diagnóstico de codificación | Desechables. |
| `tmp_find_lines.py`, `tmp_line_extract.py`, `tmp_lines.py`, `tmp_service_lines.py`, `tmp_ui_lines.py` | Inspección puntual de archivos | Desechables. |
| `temp.txt`, `temp_dashboard_block.txt` | Fragmentos duplicados de UI | Desechables después de comparar contra la versión activa. |
| `bytes.txt` | Artefacto de 531 KB/60.315 líneas con valores numéricos | No tiene referencias; candidato a retiro tras verificar su origen. |
| `scripts/generate_test_data.py` | Una línea de comentario residual; no genera datos | Nombre engañoso y sin función. Retirar o reemplazar únicamente si se define un generador real de pruebas. |

La búsqueda global no encontró importaciones ni usos de estos temporales. `MANUAL_TECNICO.md` solo los enumera como deuda. No se eliminó ninguno durante la auditoría.

## 5. Archivos y funciones demasiado grandes

| Elemento | Tamaño | Problema |
|---|---:|---|
| `ui/app_shell.py` | 2.428 líneas | Siete páginas, componentes, navegación, estado y reglas en un archivo. |
| `_tab_registro` | 453 líneas | Validación, composición, creación, actualización y presentación inseparables. |
| `_tab_consulta` | 202 líneas | Búsqueda y métricas viven en widgets; hay filtros repetidos. |
| `_tab_publicacion`, `v2`, `v3` | 153/161/161 líneas | Tres implementaciones muy similares; dos no se usan. |
| `services/registro_service.py` | 1.254 líneas | Al menos seis servicios/casos de uso distintos en una clase. |
| `RegistroService` | 1.205 líneas, 48 métodos | Alta cohesión accidental alrededor de un `DataFrame`, no del dominio. |
| `app_old_backup.py` | 780 líneas | Respaldo obsoleto que duplica lógica anterior. |

## 6. Dependencias entre módulos

Flujo principal actual:

```text
app.py
 ├─ config
 └─ ui.app_shell
     ├─ ui.login ──> auth.service ──> auth.UserSheetRepository ──> Google API
     ├─ auth.service (permisos)
     ├─ core.utils
     └─ RegistroService
         ├─ config / core.utils / pandas
         ├─ ExcelRepository ──> openpyxl / archivos locales
         └─ GoogleSheetsRepository ──> ExcelRepository + Google API
```

Hallazgos:

- No se detectaron importaciones circulares estáticas.
- La UI no conoce llamadas, rangos ni credenciales de la API de Google; este límite actual debe conservarse.
- `RegistroService` instancia `GoogleSheetsRepository` o `ExcelRepository` según una variable global: selección de infraestructura y lógica de aplicación están acopladas.
- El repositorio de Google hereda de Excel para reutilizar listas y exportación. Un repositorio remoto queda así ligado a archivos locales y a `openpyxl`.
- Autenticación usa un singleton global de repositorio, difícil de sustituir en pruebas y sensible a cambios de configuración posteriores.
- La UI importa métodos estáticos de `RegistroService` y manipula `DataFrame`; el contrato entre capas es implícito.
- `domains/models.py` no participa en el grafo.

## 7. Duplicación y lógica fuera de capa

- Cliente de Google, credenciales, reintentos y `_format_value` están duplicados en los dos repositorios de Sheets.
- Normalización de columnas/texto aparece en `config`, `core.utils`, ambos repositorios, servicio y UI.
- Búsqueda por nombre, cédula y título está implementada directamente en `_tab_consulta`; hay tres filtros consecutivos para `q`, uno redundante, y la búsqueda de título usa una ruta separada.
- Composición y fusión parcial de filas se realiza en la UI (`_merge_form_values_over_existing`, `_with_shared_tesis_values`).
- Identificación de columnas por alias/tildes se repite en UI, servicio y repositorio.
- Agrupación, estados y construcción de editores de Normalización/Publicación mezclan reglas con `st.data_editor`.
- `_tab_publicacion`, `_tab_publicacion_v2` y `_tab_publicacion_v3` duplican casi todo el flujo; el enrutador solo usa `v3`.
- `_streamlit_rerun` está duplicado entre login y shell.
- Reintentos Google están duplicados.
- `app_old_backup.py` repite utilidades, repositorio, formulario e historial de una arquitectura anterior.
- `asesorias_payload` se recibe en `add_registro` y `update_registro`, pero no se utiliza en esos métodos; es un contrato engañoso que requiere prueba de caracterización antes de retirarlo.

## 8. Código muerto o temporal

Confirmado por referencias estáticas:

- Las cuatro clases de `domains/models.py` no se usan.
- Las funciones `_tab_publicacion` y `_tab_publicacion_v2` no se invocan.
- `app_old_backup.py` no se importa.
- Los `tmp_*.py`, `temp*.txt`, `bytes.txt` y el script `generate_test_data.py` no son parte de la ejecución.
- El import `auth_service` en `app.py` no se usa.

Esto no autoriza todavía su eliminación. En la fase de limpieza se registrará cada retiro en `docs/cleanup-report.md`, se repetirá la búsqueda de referencias y se ejecutará la regresión completa.

## 9. Configuración y riesgos de seguridad

### Prioridad crítica

1. `.streamlit/secrets.toml` estuvo versionado en al menos cuatro commits antes de ser retirado. El historial contiene objetos de ese archivo. **La clave de la cuenta de servicio debe rotarse**; ignorar o borrar el archivo actual no invalida la clave expuesta.
2. `data/users.json` sigue versionado y contiene 11 identidades (correo/nombre/rol), aunque las contraseñas observadas tienen forma de hash PBKDF2.
3. `data/registro_actual.xlsx` sigue versionado y contiene 100 registros con identificación, nombres, correos, tesis y observaciones.
4. La plantilla `.xlsm` activa contiene 296 filas de registro no vacías, incluidas columnas personales y observaciones. Debe mantenerse su estructura, macros, listas y estilos, pero sustituirse el contenido real por una plantilla sanitizada.

`.gitignore` no deja de seguir archivos ya versionados. En una fase posterior habrá que usar `git rm --cached` sobre los datos locales, conservar las copias locales y evaluar limpieza de historial coordinada; no se hará *force push* sin autorización y plan explícitos.

### Prioridad alta/media

- Existen tres copias locales ignoradas con material de cuenta de servicio (`.streamlit/secrets.toml`, `.streamlit/service-account.json` y el JSON de raíz). No se borrarán porque son necesarias localmente, pero debe quedar una sola fuente documentada y con permisos restrictivos.
- `app.py` escribe el JSON secreto en `.streamlit/service-account.json`. En despliegue es preferible usar `from_service_account_info` en memoria y no materializar la clave.
- `tmp_script.py` y `tmp_sheet_test.py` versionan un ID de hoja y una ruta personal de credencial; además pueden imprimir registros reales si alguien los ejecuta.
- Múltiples `print("DEBUG...")` registran usuario, índice, observación anterior/nueva y actualización completa. Esto expone contenido sensible en logs de plataforma.
- La UI presenta `str(exc)` al usuario en muchos bloques generales; una excepción puede revelar rutas o detalles internos.
- Los mensajes dinámicos de `search_modal` se insertan en HTML sin escape explícito. Debe caracterizarse y sanearse sin cambiar el texto visible.
- Autenticación conserva compatibilidad con contraseña en texto plano si la celda no parece PBKDF2. Debe migrarse de forma segura, sin bloquear usuarios existentes.
- Tokens de recuperación se guardan utilizables en la hoja. Conviene guardar solo su hash y registrar expiración con un reloj consistente.
- El bloqueo de login vive en memoria del proceso (`LOGIN_FAILURES`) y en la sesión; se pierde al reiniciar y no se comparte entre réplicas.
- El logout elimina identidad y claves de login, pero no limpia selección, formularios, edición ni filtros. En un navegador compartido, otro usuario podría heredar estado funcional anterior.
- No existe logging estructurado ni redacción central de secretos/PII.
- `.gitignore` carece de varias reglas solicitadas: entornos, IDE, cobertura, logs, temporales de Office y patrones amplios de credenciales.

## 10. Riesgos de pérdida o corrupción de datos

### Escritura completa no atómica

`GoogleSheetsRepository.save_registro()` y `UserSheetRepository.save_users()` hacen dos solicitudes independientes:

1. `values.clear(...)`
2. `values.update(...)`

Si la segunda falla después de la primera, el rango queda vacío. Los reintentos no convierten ambas llamadas en una transacción.

### Actualizaciones perdidas por concurrencia

Todos los cambios siguen el patrón leer todo → modificar `DataFrame` → reemplazar todo. El `threading.RLock` solo serializa escrituras dentro de un proceso Python. No protege dos procesos de Streamlit, dos réplicas ni una edición manual de la hoja. Dos usuarios pueden leer la misma versión y el último en guardar sobrescribe al primero.

### Índices inestables

- Edición, observaciones y normalización usan el índice de `DataFrame` como identidad de fila.
- `_load_registro_for_normalizacion()` elimina `Registro_ID` si existe.
- Si cambia el orden o se inserta/elimina una fila entre lectura y escritura, un índice puede apuntar a otro registro.

### Efectos de escritura durante lecturas

`_load_registro_for_publicacion()` agrega valores predeterminados y llama a `save_registro()` cuando detecta cambios. Por tanto, abrir Publicación, Métricas o algunos resúmenes puede escribir en la fuente aunque el usuario no pulse Guardar. Esto contradice el principio de que una consulta no debe mutar datos y aumenta las carreras.

### Normalización destructiva del esquema

`normalize_registro_df()` descarta automáticamente las columnas declaradas en `REMOVED_REGISTRO_COLUMNS`, agrega columnas y reordena el esquema. Al guardar, esos cambios se aplican a toda la hoja. Debe congelarse el esquema real y probarse antes de tocar esta función.

### Guardados parciales y defectos basales

- El formulario guarda estudiantes adicionales uno por uno. Una falla intermedia deja un grupo parcialmente creado.
- La prevención de duplicados se basa en primera coincidencia exacta de cédula o nombre, sin ID estable ni operación atómica.
- Las observaciones colaborativas son reemplazo de texto, no control de versión; dos editores pueden sobrescribirse.
- `assign_publicacion()` usa `assignment_col` sin definirlo en el método; la reasignación puede fallar en ejecución. Se registra como defecto basal y no se corrige en esta fase.
- Normalización y Publicación guardan `datetime.utcnow()` como texto sin zona. Esto no cumple de forma consistente `America/Bogota`, aunque las fechas generales sí usan `ZoneInfo`.
- El fallback Excel usa archivo temporal y reemplazo local, mejor que la escritura remota, pero tampoco ofrece control de versión entre procesos.

## 11. Caché y `session_state`

### Caché

- No hay decoradores `st.cache_data` ni `st.cache_resource` en el código actual.
- Cada *rerun* autenticado crea un `RegistroService`, vuelve a leer la plantilla/listas y varios flujos vuelven a consultar la hoja múltiples veces.
- `_install_streamlit_cache_modal_guard()` no gestiona datos en caché: inyecta JavaScript en el DOM padre para bloquear una tecla y cerrar el diálogo interno “Clear caches”. Depende de detalles internos de Streamlit y puede romperse con actualizaciones.

La futura caché debe ser solo de lectura, con TTL explícito e invalidación después de escribir. No se debe cachear el registro editable sin estrategia de consistencia.

### Estado de sesión

- `login.py` centraliza parcialmente las claves de identidad, actividad, intentos y bloqueo.
- `app_shell.py` usa al menos 36 claves estáticas y familias dinámicas (`extra_*`, `asesor_rec_*`, `nombre_asesoria_*`, editores, botones y menú).
- Se duplican cadenas para página actual, modo de edición, fila, registro, modal, guardado, filtros y campos.
- Estado y widgets son la misma fuente implícita; el orden de asignación antes de crear widgets es sensible a excepciones de Streamlit.
- Navegación se duplica entre `st.query_params` y `session_state`.
- `saving` evita doble clic dentro de la sesión, pero no idempotencia en el repositorio.

Se necesita un módulo de claves/operaciones de sesión que preserve exactamente nombres y transiciones durante la migración.

## 12. Acceso a Google Sheets

### Configuración actual

| Uso | Hoja/rango configurado |
|---|---|
| Registro | `Registro asesorías!A:ZZ` por defecto |
| Usuarios | `User!A:ZZ` |
| Facultades/programas | `UM!A:ZZ` más listas de la plantilla local |

Los nombres exactos y las columnas de `config.py` son parte del contrato y no deben cambiar durante la refactorización.

### Lecturas

- `GoogleSheetsRepository.load_registro()`: obtiene el rango completo y lo convierte a `DataFrame`.
- `GoogleSheetsRepository.load_lists()`: combina plantilla local con la hoja `UM`.
- `UserSheetRepository.load_users()`: obtiene usuarios completos y normaliza encabezados.
- La UI solo accede mediante servicios, lo cual es una base positiva.

### Escrituras y actualizaciones

| Punto | Disparador | Operación real |
|---|---|---|
| `GoogleSheetsRepository.save_registro` | Cualquier mutación del servicio | Limpia y reescribe todo el rango de registro. |
| `UserSheetRepository.save_users` | Cambio/restablecimiento/inicialización de contraseña | Limpia y reescribe toda la hoja de usuarios. |
| `ExcelRepository.ensure_db/save_registro` | Fallback sin ID de Sheets | Crea o reemplaza Excel local mediante archivo temporal. |
| `RegistroService.add_registro` | Guardar estudiante nuevo | Lee, verifica duplicado, concatena y guarda todo. |
| `update_registro`, `update_row_by_index` | Edición de formulario/consulta | Modifica campos parciales en memoria y guarda todo. |
| `update_observacion_colaborativa` | API de observación | Reemplaza observación y guarda todo; actualmente no se invoca desde UI. |
| `update_fields_for_tesis` | Propagación de datos compartidos | Actualiza todas las filas de una tesis y guarda todo. |
| `delete_registro` | Método disponible | Elimina por índice y guarda todo; no se observó disparador activo en la UI actual. |
| `bulk_import` | Método disponible | *Upsert* en memoria y guardado total; no se observó widget activo. |
| `distribute_registros` | Botón “Distribuir registros” | Agrupa por título, conserva asignaciones compatibles y guarda filas nuevas asignadas. |
| `update_normalizacion_estado` | “Guardar avances” | Actualiza estado/observación/revisor/fecha y guarda todo. |
| `_load_registro_for_publicacion` | Carga de Publicación/Métricas | Puede guardar valores predeterminados sin botón. |
| `assign_publicacion` | “Asignar a Diana” | Pretende actualizar tesis, pero contiene el defecto basal indicado. |
| `update_publicacion_estado` | “Guardar publicación” | Actualiza por tesis y guarda todo. |
| `auth._save_store` | Operaciones de contraseña | Ordena y reemplaza todos los usuarios. |
| `app.configure_google_credentials` | Inicio de la app | Escribe la credencial local, no la hoja. |

## 13. Manejo de errores y observabilidad

- Los repositorios convierten algunos `HttpError` en `RuntimeError`, pero no existe jerarquía propia de excepciones.
- La UI captura muchos `Exception` generales y muestra el detalle técnico directamente.
- Hay conversiones que silencian cualquier excepción y continúan con valores vacíos.
- No existe configuración de `logging`; se usan `print` de depuración con PII.
- Los reintentos de Google son razonables para 429/5xx, pero están duplicados y usan `sleep` bloqueante.
- No hay identificador de operación, auditoría de cambio, versión de fila ni métricas de fallos.

Arquitectura destino: excepciones de dominio/aplicación/repositorio, traducción única a mensajes visibles existentes y logging técnico con redacción de secretos, correos, documentos y observaciones.

## 14. Estado de pruebas y verificaciones basales

Verificaciones ejecutadas sin acceder a la hoja real:

- Compilación en memoria de los 29 archivos `.py`: correcta.
- Importación de los 12 módulos activos y `app.py`: correcta; Streamlit emitió únicamente la advertencia esperada por ejecución fuera de su contexto.
- Descubrimiento de pruebas: no fue posible porque `pytest` no está instalado y no existe `tests/`.
- No se inició una sesión funcional contra Google Sheets para evitar escrituras accidentales durante la auditoría.

Antes del primer movimiento funcional se deben añadir `pytest` y pruebas de caracterización con repositorios falsos. Las pruebas no deben instanciar el cliente Google.

## 15. Arquitectura destino propuesta

Se propone mantener compatibilidad temporal mediante adaptadores y un *bootstrap* único:

```text
asesorias_app/
├── application/
│   ├── ports/
│   │   ├── registro_repository.py
│   │   └── user_repository.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── registro_service.py
│   │   ├── consulta_service.py
│   │   ├── distribucion_service.py
│   │   ├── normalizacion_service.py
│   │   ├── publicacion_service.py
│   │   └── metricas_service.py
│   └── dto/
├── domain/
│   ├── entities/
│   ├── policies/
│   └── exceptions.py
├── infrastructure/
│   ├── google_sheets/
│   │   ├── client.py
│   │   ├── registro_repository.py
│   │   └── user_repository.py
│   ├── excel/
│   ├── files/
│   ├── logging/
│   └── settings.py
├── presentation/
│   └── streamlit/
│       ├── pages/
│       │   ├── registrar_editar.py
│       │   ├── consultar.py
│       │   ├── distribuir_normalizar.py
│       │   ├── publicacion.py
│       │   └── metricas.py
│       ├── components/
│       ├── session.py
│       ├── navigation.py
│       ├── login.py
│       └── theme.py
├── shared/
│   ├── constants.py
│   ├── date_utils.py
│   ├── text_utils.py
│   └── validation.py
└── bootstrap.py
app.py
```

Reglas de transición:

- `app.py` seguirá siendo el único punto de entrada y solo configurará Streamlit y llamará a `bootstrap`.
- Los contratos de repositorio no expondrán `DataFrame`, rangos, credenciales ni índices de Sheets a la presentación.
- Durante la transición, adaptadores de compatibilidad podrán conservar las firmas actuales para no mover todo a la vez.
- Las páginas conservarán literalmente textos, claves de widgets, orden, CSS y condiciones de permisos.
- Google Sheets seguirá siendo la persistencia principal; Excel quedará como exportación/fallback explícito, no como superclase del adaptador Google.
- Se introducirá un ID estable solo si puede hacerse sin cambiar columnas/datos; mientras no exista autorización, se deberá validar la fila por su contenido/versión antes de actualizar.

## 16. Plan de migración incremental

Cada paso debe terminar con pruebas, arranque de la app con repositorio falso, checklist aplicable, documento de movimientos y commit independiente. No se continúa si cambia el comportamiento.

### Paso 0 — Congelar comportamiento

1. Añadir infraestructura de pruebas y un `FakeRegistroRepository`/`FakeUserRepository`.
2. Crear pruebas de caracterización para búsquedas, fusión parcial, agrupación, distribución, observaciones, creación/actualización, serialización y zona horaria.
3. Registrar el defecto basal de reasignación de Publicación antes de corregirlo en un commit separado.
4. Capturar nombres de columnas, hojas, textos, roles, claves de estado y estructura de exportaciones como contratos.

### Paso 1 — Configuración y seguridad

1. Completar `.gitignore` con todos los patrones requeridos.
2. Sacar del índice, sin borrar copias locales, usuarios, registro real, temporal Office y otros sensibles.
3. Crear plantillas sin valores (`.env.example` y ejemplo de secrets).
4. Sanitizar la plantilla `.xlsm` preservando macros, hojas, estilos, validaciones y encabezados; validar binariamente/funcionalmente.
5. Rotar la cuenta de servicio expuesta y documentar el incidente. La limpieza de historial será una operación separada y coordinada, nunca un *force push* automático.
6. Evitar materializar credenciales en disco cuando se proporcionan como secreto estructurado.

Commit sugerido: `chore: secure repository and remove generated files`.

### Paso 2 — Utilidades compartidas

1. Separar fecha Bogotá, texto, columnas/alias, validación y serialización.
2. Mantener funciones puente en `core.utils` mientras migran los imports.
3. Unificar reglas de comparación sin modificar tildes, ñ, mayúsculas ni resultados actuales.

Commit sugerido: `refactor: extract shared configuration and utilities`.

### Paso 3 — Repositorios Google Sheets

1. Definir `Protocol` para registro y usuarios.
2. Extraer cliente/credenciales/reintentos comunes.
3. Desacoplar Google de `ExcelRepository`.
4. Implementar operaciones granulares o una escritura única segura; incorporar control optimista antes de reemplazar filas.
5. Eliminar escrituras desde funciones de lectura.
6. Preservar rangos, hojas, columnas, orden y serialización con pruebas de contrato.

Commit sugerido: `refactor: isolate google sheets repositories`.

### Paso 4 — Servicios por flujo

1. Extraer, en este orden, Consulta, Distribución, Normalización, Publicación y Métricas.
2. Mover búsqueda/filtros y composición parcial desde UI.
3. Mantener fachadas compatibles en `RegistroService` hasta que cada página migre.
4. Agregar excepciones tipadas y eliminar `print` sensibles.
5. Corregir defectos basales solo con prueba que demuestre el comportamiento esperado.

Commit sugerido: `refactor: separate application services by workflow`.

### Paso 5 — Autenticación y usuarios

1. Inyectar `UserRepository` en `AuthService`.
2. Separar política de roles, hashing/tokens y orquestación.
3. Migrar contraseñas antiguas al hash de manera compatible.
4. Hash de tokens, bloqueo consistente y limpieza segura de sesión al logout.
5. Verificar todos los roles y permisos visibles sin alterarlos.

### Paso 6 — Session state y navegación

1. Inventariar y declarar constantes para todas las claves actuales, incluidas familias dinámicas.
2. Crear operaciones `initialize`, `begin_edit`, `finish_save`, `reset_form`, `logout` sin renombrar inicialmente las claves reales.
3. Encapsular sincronización con `query_params`.
4. Probar reruns, edición, guardado, retorno de página y logout.

### Paso 7 — Páginas Streamlit

1. Extraer una página por commit, empezando por Métricas y terminando por Registro.
2. Conservar exactamente llamadas de widgets, claves, etiquetas, orden y contenedores.
3. Sustituir las tres páginas de Publicación por la variante `v3` activa solo después de pruebas.
4. La UI recibirá servicios desde `bootstrap`; no creará repositorios.

Commit sugerido: `refactor: split streamlit pages and reusable components`.

### Paso 8 — Componentes visuales

Extraer componentes repetidos (botones, métricas, descargas, editores, mensajes) sin mover ni reescribir `assets/styles.css` salvo necesidad demostrada. Añadir comparación visual/manual.

### Paso 9 — Limpieza final

1. Repetir búsqueda de referencias para cada candidato.
2. Crear `docs/cleanup-report.md` antes de retirar cada archivo.
3. Eliminar temporales, respaldo y variantes muertas confirmadas.
4. Conservar PDFs, logos, CSS, plantilla activa sanitizada y scripts reales de mantenimiento.

### Paso 10 — Documentación y regresión

Crear/actualizar `README.md`, `docs/architecture.md`, `development.md`, `deployment-streamlit.md`, `google-sheets-schema.md`, `security.md`, `testing.md` y `cleanup-report.md`. Ejecutar pruebas automatizadas y el checklist manual de 20 puntos con una hoja de ensayo, nunca con producción.

Commits sugeridos:

```text
test: add regression coverage for critical workflows
docs: document architecture and deployment
```

## 17. Criterios de control y reversión

Para cada fase:

1. Árbol Git limpio antes de comenzar.
2. Pruebas unitarias y de contrato sin red.
3. Arranque Streamlit con configuración de ensayo.
4. Comparación de columnas, cantidad de filas y hash lógico antes/después de toda prueba de escritura.
5. Checklist manual del flujo afectado.
6. Un commit acotado; si falla una comprobación, revertir solo ese commit y no avanzar.
7. Nunca ejecutar pruebas de mutación contra la hoja real.

## 18. Diagnóstico y prioridad recomendada

Orden inmediato recomendado antes de reestructurar UI:

1. Rotar la credencial expuesta y desindexar/sanitizar datos personales.
2. Crear pruebas de caracterización y repositorios falsos.
3. Eliminar el patrón remoto `clear` + `update` y las escrituras en rutas de lectura.
4. Introducir contratos e inyección de repositorios.
5. Extraer servicios por flujo.
6. Centralizar sesión/navegación.
7. Dividir páginas y componentes preservando la interfaz.
8. Limpiar temporales y completar documentación.

No se recomienda empezar cortando `app_shell.py` por líneas: sin pruebas y con las reglas aún dentro de widgets, ese movimiento aumentaría el riesgo de regresión y pérdida de datos.
