from pathlib import Path
text = Path('asesorias_app/config.py').read_text(encoding='utf-8')
text = text.replace('Gar\uFFFDa', 'Garcia')
text = text.replace('Sep\uFFFDlveda', 'Sepulveda')
path = Path('asesorias_app/config.py')
path.write_text(text, encoding='utf-8')
