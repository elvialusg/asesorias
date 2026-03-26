from pathlib import Path
lines = Path('asesorias_app/services/registro_service.py').read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(lines,1):
    if 'distribute_registros' in line or '_is_valid_registro' in line:
        print(f"{idx}: {line}")
