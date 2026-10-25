"""Optional Cota engine checks using an existing checkout and its installed dev dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

import release
from install_skill import install,verified_files
from validate_matrix import COTA_COMMIT

ROOT=Path(__file__).resolve().parents[1]


def check(cota_dir,output,node='node',package_path=None):
    web=cota_dir.resolve()
    if (web/'services'/'web').is_dir():
        web=web/'services'/'web'
    package=json.loads((web/'package.json').read_text(encoding='utf-8'))
    if package.get('name')!='cota' or package.get('version')!='1.0.0':
        raise ValueError('La referencia de esta comprobación es Cota 1.0.0.')
    cota_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=web,text=True).strip()
    if cota_commit!=COTA_COMMIT:
        raise ValueError('Usa la revisión fijada de Cota: '+COTA_COMMIT)
    runner=web/'node_modules'/'vitest'/'vitest.mjs'
    if not runner.is_file():
        raise ValueError('Instala primero las dependencias de desarrollo del checkout de Cota.')
    build=ROOT/'build'
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cota-interop-',dir=build) as temporary:
        fixtures=Path(temporary)
        archive=package_path.resolve() if package_path is not None else release.build(destination=fixtures/'skill.zip')[0]
        _,manifest=verified_files(archive)
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        skill,_=install(archive,fixtures/'skills')
        for name,asset in (('cuna','cuna.json'),('cuatro-taladros','cuatro-taladros.json')):
            subprocess.run([sys.executable,'-B',str(skill/'scripts'/'generar.py'),str(skill/'assets'/asset),
                            '--output-dir',str(fixtures/name),'--mode','sheet','--export-cota'],
                           check=True,capture_output=True,text=True,encoding='utf-8')
        # The harness imports Cota's own TypeScript modules. Create and remove
        # only this owned file, so no application code or dependencies change.
        with tempfile.NamedTemporaryFile(prefix='proyecciones-svg-',suffix='.test.ts',
                dir=web/'src'/'test',delete=False) as file:
            harness=Path(file.name)
        try:
            shutil.copyfile(ROOT/'tests'/'cota_interop.test.ts',harness)
            subprocess.run([node,str(runner),'run',str(harness),'--maxWorkers','1','--minWorkers','1'],
                cwd=web,env={**os.environ,'PROYECCIONES_SVG_COTA_OUTPUT':str(fixtures)},check=True,timeout=120)
            report=json.loads((fixtures/'cota-interop.json').read_text(encoding='utf-8'))
            report['exports']={name:{'sha256':hashlib.sha256((fixtures/name/'modelo.cota').read_bytes()).hexdigest(),
                'units':json.loads((fixtures/name/'modelo.cota').read_text(encoding='utf-8'))['units']}
                for name in ('cuna','cuatro-taladros')}
        finally:
            harness.unlink()
    report['status']='success'
    report['tests']=2
    report['commit']=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report['version']=manifest['version']
    report['package_sha256']=digest
    report['system']=platform.system()
    report['python']=platform.python_version()
    report['machine']=platform.machine()
    report['platform']=platform.platform()
    report['node']=subprocess.check_output([node,'--version'],text=True).strip()
    report['cota_version']=package['version']
    report['cota_commit']=cota_commit
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cota-dir',required=True,type=Path,help='Checkout de Cota o su carpeta services/web.')
    parser.add_argument('--output',type=Path,default=ROOT/'build'/'cota-interop.json')
    parser.add_argument('--node',default='node')
    parser.add_argument('--package',type=Path,help='ZIP exacto que se debe instalar y comprobar; si se omite se construye uno temporal.')
    args=parser.parse_args()
    try:
        print(check(args.cota_dir,args.output,args.node,args.package))
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        parser.exit(1,f'Error: {error}\n')
