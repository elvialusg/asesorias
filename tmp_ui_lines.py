# -*- coding: utf-8 -*-
from pathlib import Path
lines = Path('asesorias_app/ui/app_shell.py').read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(lines,1):
    if 'Normaliz' in line or 'assignment' in line or 'Distribuir registros' in line:
        print(f"{idx}: {line}")
