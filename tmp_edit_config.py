from pathlib import Path
path = Path('asesorias_app/config.py')
text = path.read_text(encoding='utf-8')
if 'ASSIGNMENT_COLUMN = "Asignado_a"' not in text:
    marker = "GOOGLE_SHEETS_SCOPES = [\n    \"https://www.googleapis.com/auth/spreadsheets\",\n    \"https://www.googleapis.com/auth/drive\",\n]\n"
    insert = ("\nASSIGNMENT_COLUMN = \"Asignado_a\"\n"\
              "DEFAULT_ASSIGNMENT_PEOPLE = [\n"\
              "    \"Harold Estiven Gar\u00eda\",\n"\
              "    \"Luz Andrea Sep\u00falveda\",\n"\
              "    \"Juan Pablo Charry\",\n"\
              "    \"Maria Eugenia Nieto\",\n"\
              "]\n")
    if marker in text:
        text = text.replace(marker, marker + insert, 1)
reg_section = text.split('REGISTRO_COLUMNS = [',1)[1]
inside, after = reg_section.split(']\n',1)
if 'ASSIGNMENT_COLUMN' not in inside:
    inside = inside + '    ASSIGNMENT_COLUMN,\n'
    text = text.split('REGISTRO_COLUMNS = [',1)[0] + 'REGISTRO_COLUMNS = [\n' + inside + ']\n' + after
path.write_text(text, encoding='utf-8')
