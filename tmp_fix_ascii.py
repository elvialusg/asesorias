from pathlib import Path
path = Path('asesorias_app/config.py')
text = path.read_text(encoding='utf-8')
text = text.replace('Harold Estiven Gar\uFFFDa', 'Harold Estiven Garcia')
text = text.replace('Luz Andrea Sep\uFFFDlveda', 'Luz Andrea Sepulveda')
text = text.replace('\n\nREGISTRO_COLUMNS', '\nREGISTRO_COLUMNS')
path.write_text(text, encoding='utf-8')
