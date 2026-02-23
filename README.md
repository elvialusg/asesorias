# Tablero de Asesorias (Tesis)

Aplicacion web construida con Streamlit para registrar, consultar y descargar el historial de asesorias de estudiantes de trabajo de grado. La app mantiene un archivo Excel maestro (basado en `Control_Asesorias_Tesis_template.xlsm`) y expone tres flujos principales: registro/modificacion, consulta y carga masiva.

## Caracteristicas
- Formulario guiado con autocompletado por cedula y listas dependientes Facultad -> Programa.
- Historial completo por estudiante con soporte para eliminar asesorias especificas o el registro completo.
- Descarga del Excel actualizado y generacion de plantillas para carga masiva.
- Procesos de carga masiva que crean o actualizan registros existentes respetando columnas adicionales.
- Preparada para migrar a almacenamiento centralizado (SharePoint / Microsoft Graph) reemplazando la fuente `data/registro_actual.xlsx`.

## Requisitos
- Python 3.10+.
- Dependencias listadas en `requirements.txt` (Streamlit, pandas, openpyxl, xlsxwriter).
- Archivo de plantilla `data/Control_Asesorias_Tesis_template.xlsm` (incluido en el repo).

## Estructura
```
.
|-- app.py                     # Aplicacion Streamlit
|-- data/
|   |-- Control_Asesorias_Tesis_template.xlsm
|   `-- registro_actual.xlsx   # Base local (se ignora en git)
|-- requirements.txt
`-- README.md
```

## Configuracion inicial
1. Crea un entorno virtual y activalo:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Verifica que `data/Control_Asesorias_Tesis_template.xlsm` exista. Si no, copia la version original usada por el equipo.
4. Si `data/registro_actual.xlsx` no existe, la app generara un archivo vacio basado en el template la primera vez que se ejecute.

## Ejecucion local
```bash
streamlit run app.py
```
La app expone tres pestanas:
1. **Registro / modificacion**: permite agregar filas nuevas o anexar asesorias a un estudiante existente.
2. **Consulta**: busca por nombre o cedula, muestra el historial y habilita eliminaciones puntuales.
3. **Carga masiva**: descarga una plantilla segun las columnas actuales y permite importar actualizaciones desde Excel.

## Administracion de datos
- `data/registro_actual.xlsx` actua como base de datos local. Se mantiene fuera de control de versiones para evitar subir informacion sensible. Puedes respaldarla manualmente o sincronizarla con SharePoint/OneDrive.
- Para restaurar desde cero, borra `data/registro_actual.xlsx`; la app recrea una version vacia al iniciar.

## Integracion con SharePoint / Microsoft Graph (opcional)
La aplicacion esta lista para usar un backend remoto si reemplazas las funciones `load_registro()` y `save_registro()` por llamadas a Microsoft Graph:
1. Registra una aplicacion en Azure AD y otorga permisos `Files.ReadWrite.All` / `Sites.ReadWrite.All`.
2. Usa MSAL (Python) para obtener tokens OAuth 2.0 hacia `https://graph.microsoft.com/.default`.
3. Sustituye la lectura/escritura de `data/registro_actual.xlsx` por requests `GET` / `PUT` al endpoint del archivo en SharePoint (`/sites/{site-id}/drive/items/{item-id}/content`).
4. Guarda las credenciales (tenant, client id, secret) como variables de entorno o en `.streamlit/secrets.toml` (no compartas el archivo real, solo un ejemplo).

## Despliegue
- **Streamlit Community Cloud**: conecta el repo de GitHub, incluye `data/Control_Asesorias_Tesis_template.xlsm` en el repo y usa el panel de Secrets para credenciales si activas almacenamiento remoto.
- **Render / Railway**: crea un servicio web con el comando `streamlit run app.py`. Configura variables de entorno y habilita persistencia externa (SharePoint/BD) para evitar perdida de datos tras reinicios.

## Buenas practicas
- No incluyas `data/registro_actual.xlsx` en commits (esta ignorado en `.gitignore`).
- Antes de abrir un PR, verifica que los flujos principales funcionen (crear registro, consultar, carga masiva, descarga).
- Documenta cambios en este README si agregas nuevas fuentes de datos o endpoints.
