# -*- coding: utf-8 -*-
from pathlib import Path
text = Path('asesorias_app/config.py').read_text(encoding='utf-8')
segment = text.split('DEFAULT_ASSIGNMENT_PEOPLE',1)[1].split(']',1)[0]
for ch in segment.splitlines()[1]:
    print(ord(ch))
