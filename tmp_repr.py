# -*- coding: utf-8 -*-
from pathlib import Path
text = Path('asesorias_app/config.py').read_text(encoding='utf-8')
print(repr(text.split('DEFAULT_ASSIGNMENT_PEOPLE',1)[1].split(']',1)[0]))
