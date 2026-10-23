"""Prepare stable assets and an optional GitHub draft from an approved CI commit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import release
from verify import source_checks

ROOT=Path(__file__).resolve().parents[1]


def command(args):
    return subprocess.check_output(args,cwd=ROOT,text=True,encoding='utf-8',errors='strict').strip()


def gh_json(args):
    return json.loads(command(['gh',*args]))


def approved_run(runs,commit):
    return next((run for run in runs if run['headSha']==commit and run['conclusion']=='success'
                 and run['event'] in ('push','workflow_dispatch')),None)


def check_proof(proof,commit,version,digest):
    if (proof.get('commit')!=commit or proof.get('version')!=version
        or proof.get('status')!='success' or proof.get('package_sha256')!=digest
        or len(proof.get('python_jobs',[]))!=6 or len(proof.get('browsers',[]))!=6):
        raise ValueError('La evidencia de CI no aprueba este commit, versión o paquete.')


def write_assets(output,package,commit,version,digest,evidence):
    output.mkdir(parents=True,exist_ok=True)
    approved=evidence.get('status')=='success'
    evidence_path=output/('release-readiness.json' if approved else 'ci-status.json')
    evidence_path.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    shutil.copyfile(ROOT/'tools'/'install_skill.py',output/'install_skill.py')
    shutil.copyfile(ROOT/'LICENSE',output/'LICENSE')
    notes=(ROOT/'releases'/(version+'.md')).read_text(encoding='utf-8')
    notes+='\n## Validación de esta entrega\n\nCommit: `'+commit+'`. '
    if approved:
        notes+='[CI aprobada]('+evidence['workflow_run']['url']+').\n\n'
    else:
        notes+='**CI remota pendiente. Esta preparación local todavía no está aprobada para publicación.**\n\n'
    notes+='SHA-256 del ZIP: `'+digest+'`.\n'
    notes_path=output/'RELEASE_NOTES.md'
    notes_path.write_text(notes,encoding='utf-8')
    assets=[package,package.with_suffix('.zip.sha256'),output/'install_skill.py',output/'LICENSE',evidence_path,notes_path]
    sums=''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.name+'\n' for path in assets)
    (output/'SHA256SUMS').write_text(sums,encoding='ascii')
    assets.append(output/'SHA256SUMS')
    return assets


def prepare(repo,create_draft=False,local_only=False):
    if create_draft and local_only:
        raise ValueError('--local-only no permite crear un borrador.')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise ValueError('Repositorio inválido; usa owner/repo.')
    if command(['git','status','--porcelain']):
        raise ValueError('Hay cambios locales sin confirmar; CI debe verificar el mismo contenido.')
    commit=command(['git','rev-parse','HEAD'])
    if command(['git','branch','--show-current'])!='main' or command(['git','rev-parse','origin/main'])!=commit:
        raise ValueError('Prepara la release desde main y el commit enviado a origin/main.')
    remote=command(['git','remote','get-url','origin'])
    if remote not in ('https://github.com/'+repo+'.git','https://github.com/'+repo,'git@github.com:'+repo+'.git'):
        raise ValueError('El repositorio solicitado no coincide con origin.')
    version=source_checks()
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):
        raise ValueError('La versión aún no es estable.')
    if local_only:
        package,digest=release.build()
        evidence={'commit':commit,'version':version,'status':'pending','package_sha256':digest,
                  'reason':'Remote CI has not been approved; no draft or publication was created.'}
        assets=write_assets(ROOT/'dist',package,commit,version,digest,evidence)
        result={'version':version,'commit':commit,'status':'pending_ci','package_sha256':digest,'assets':[str(p) for p in assets]}
        (ROOT/'dist'/'release-preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result
    identity=gh_json(['repo','view',repo,'--json','nameWithOwner,isPrivate'])
    if identity['nameWithOwner'].lower()!=repo.lower() or not identity['isPrivate']:
        raise ValueError('El destino debe ser el repositorio privado elegido.')
    runs=gh_json(['run','list','--repo',repo,'--workflow','verify.yml','--branch','main',
        '--commit',commit,'--status','success','--limit','10','--json','databaseId,headSha,conclusion,url,event'])
    run=approved_run(runs,commit)
    if run is None:
        raise ValueError('Todavía no hay una ejecución satisfactoria de CI para este commit.')
    jobs=gh_json(['run','view',str(run['databaseId']),'--repo',repo,'--json','jobs'])['jobs']
    if not any(job['name']=='Ready for release' and job['conclusion']=='success' for job in jobs):
        raise ValueError('No se aprobó Ready for release.')
    output=ROOT/'dist'
    output.mkdir(exist_ok=True)
    (ROOT/'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-proof-',dir=ROOT/'build') as temporary:
        command(['gh','run','download',str(run['databaseId']),'--repo',repo,'--name','release-readiness','--dir',temporary])
        proof=json.loads((Path(temporary)/'release-readiness.json').read_text(encoding='utf-8'))
    package,digest=release.build()
    check_proof(proof,commit,version,digest)
    proof['workflow_run']={'id':run['databaseId'],'url':run['url']}
    assets=write_assets(output,package,commit,version,digest,proof)
    notes_path=output/'RELEASE_NOTES.md'
    result={'version':version,'commit':commit,'status':'ci_approved','ci_url':run['url'],'package_sha256':digest,'assets':[str(p) for p in assets]}
    if create_draft:
        tag='v'+version
        existing=gh_json(['release','list','--repo',repo,'--limit','100','--json','tagName,isDraft'])
        previous=next((row for row in existing if row['tagName']==tag),None)
        if previous:
            if not previous['isDraft']:
                raise ValueError('Esta versión ya está publicada; no se reemplaza.')
            info=gh_json(['release','view',tag,'--repo',repo,'--json','targetCommitish,url'])
            if info['targetCommitish']!=commit:
                raise ValueError('Ya existe un borrador de esta versión para otro commit.')
            command(['gh','release','upload',tag,'--repo',repo,'--clobber',*[str(p) for p in assets]])
            command(['gh','release','edit',tag,'--repo',repo,'--draft=true','--notes-file',str(notes_path)])
            result['draft_url']=info['url']
        else:
            result['draft_url']=command(['gh','release','create',tag,'--repo',repo,'--draft','--target',commit,
                '--title','Proyecciones SVG '+version,'--notes-file',str(notes_path),*[str(p) for p in assets]])
    (output/'release-preparation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--create-draft',action='store_true')
    parser.add_argument('--local-only',action='store_true',help='Prepara archivos locales marcados como pendientes; no consulta CI ni crea borradores.')
    args=parser.parse_args()
    try:
        result=prepare(args.repo,args.create_draft,args.local_only)
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        parser.exit(1,f'Error: {error}\n')
    print(json.dumps(result,indent=2))
