# -*- coding: utf-8 -*-
from pathlib import Path
path = Path('asesorias_app/config.py')
lines = path.read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(lines,1):
    if 'ASSIGNMENT_COLUMN' in line or 'DEFAULT_ASSIGNMENT_PEOPLE' in line:
        print(f"{idx}: {line}")
