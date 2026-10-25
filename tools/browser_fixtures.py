"""Generate representative portable artifacts for browser verification."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills'/'proyecciones-svg'
for name in ('cuna','bloque-taladrado','cuatro-taladros'):
    subprocess.run([sys.executable,'-B',str(SKILL/'scripts'/'generar.py'),str(SKILL/'assets'/(name+'.json')),
        '--output-dir',str(ROOT/'build'/'browser'/name),'--viewer','--frames','24','--seconds','1',
        '--sections','--export-cota','--force'],check=True)
