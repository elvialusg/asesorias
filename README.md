# Tablero de Asesorías (Tesis) – Streamlit

## Qué hace
- Formulario web con listas desplegables (dependientes: Facultad -> Programa)
- Guarda los registros (se almacena en `data/registro_actual.xlsx`)
- Consulta por usuario (nombre o cédula) y muestra todas sus asesorías
- Descarga un XLSM actualizado conservando la estructura del template

## Cómo ejecutar local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo publicar con URL
Opciones comunes:
- **Streamlit Community Cloud** (gratis para proyectos públicos)
- **Render** / **Railway** (pago/ gratis limitado)

Asegúrate de incluir en tu repo:
- `app.py`
- `requirements.txt`
- carpeta `data/` con `Control_Asesorias_Tesis_template.xlsm`

> Nota: en despliegues gratuitos, el almacenamiento puede ser efímero. Para producción, conecta una BD (PostgreSQL, SQLite persistente, etc.).
