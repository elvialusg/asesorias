from pathlib import Path
path = Path('asesorias_app/ui/app_shell.py')
lines = path.read_text(encoding='utf-8').splitlines()
for idx,line in enumerate(lines,1):
    if 'Evita mostrar' in line:
        for j in range(idx-5, idx+6):
            if 1 <= j <= len(lines):
                print(f"{j}: {lines[j-1]}")
        break
