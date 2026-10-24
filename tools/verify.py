"""Run the same checks locally and in CI, recording machine-readable evidence."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

import release
from install_skill import verified_files

ROOT=Path(__file__).resolve().parents[1]


def check_platforms(platforms,version):
    systems=platforms.get('validated_systems',[])
    if (platforms.get('version')!=version or len(systems)!=3 or set(systems)!={'Windows','Linux','Darwin'}
        or platforms.get('pending_systems')!=[] or platforms.get('python_tested')!=['3.10','3.14']):
        raise ValueError('El alcance publicado debe declarar Windows/Linux/macOS y la matriz completa.')


def source_checks():
    source=release.SOURCE
    version=(source/'VERSION').read_text(encoding='utf-8').strip()
    package=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
    lock=json.loads((ROOT/'package-lock.json').read_text(encoding='utf-8'))
    if any(value!=version for value in (package['version'],lock['version'],lock['packages']['']['version'])):
        raise ValueError('Las versiones de la skill y las pruebas no coinciden.')
    platforms=json.loads((source/'PLATFORMS.json').read_text(encoding='utf-8'))
    check_platforms(platforms,version)
    license_text=(ROOT/'LICENSE').read_text(encoding='utf-8')
    if license_text!=(source/'LICENSE').read_text(encoding='utf-8') or not license_text.startswith('MIT License\n'):
        raise ValueError('El paquete y el repositorio deben incluir la licencia MIT elegida.')
    text=(source/'SKILL.md').read_text(encoding='utf-8')
    if not text.startswith('---\nname: proyecciones-svg\ndescription: ') or text.count('\n---\n')<1:
        raise ValueError('Identidad de la skill inválida.')
    import re
    for reference in re.findall(r'\]\((references/[^)]+)\)',text):
        if not (source/reference).is_file():
            raise ValueError('Referencia ausente: '+reference)
    return version


def verify(report_dir):
    start=time.monotonic()
    report_dir.mkdir(parents=True,exist_ok=True)
    sha=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report={'commit':sha,'system':platform.system(),'python':platform.python_version(),
            'machine':platform.machine(),'platform':platform.platform(),
            'created_at':datetime.now(timezone.utc).isoformat(),'status':'failure','suites':{}}
    try:
        report['version']=source_checks()
        for key,folder in (('geometry',ROOT/'skills'/'proyecciones-svg'/'scripts'),('distribution',ROOT/'tests')):
            suite=unittest.TestLoader().discover(str(folder),pattern='test_*.py')
            result=unittest.TextTestRunner(verbosity=1).run(suite)
            report['suites'][key]={'tests':result.testsRun,'failures':len(result.failures),
                'errors':len(result.errors),'skipped':len(result.skipped)}
            if not result.wasSuccessful() or result.skipped:
                raise ValueError('La suite '+key+' falló o dejó pruebas sin ejecutar.')
        package,digest=release.build(destination=report_dir/f"proyecciones-svg-{report['version']}.zip")
        _,manifest=verified_files(package)
        report['package']={'name':package.name,'sha256':digest,'bytes':package.stat().st_size,'files':len(manifest['files'])}
        report['status']='success'
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        report['seconds']=round(time.monotonic()-start,3)
        (report_dir/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path,default=ROOT/'build'/'ci')
    args=parser.parse_args()
    try:
        result=verify(args.report_dir)
    except (OSError,ValueError) as error:
        parser.exit(1,f'Error: {error}\n')
    print(json.dumps(result,ensure_ascii=False))
