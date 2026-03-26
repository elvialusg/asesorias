from pathlib import Path
path = Path('asesorias_app/ui/app_shell.py')
lines = path.read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(lines,1):
    if 'normalizacion' in line or 'Normaliz' in line or 'normalize_registro_df' in line:
        print(f"{idx}: {line}")
