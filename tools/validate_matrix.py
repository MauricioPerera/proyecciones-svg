"""Accept only a complete CI matrix of the same commit and byte-identical ZIPs."""
import argparse
import hashlib
import json
from pathlib import Path


EXPECTED={(system,python) for system in ('Linux','Windows','Darwin') for python in ('3.10','3.14')}


def validate(folder,commit):
    found={}
    digests=set()
    versions=set()
    for report_path in sorted(folder.glob('python-*/**/report.json')):
        report=json.loads(report_path.read_text(encoding='utf-8'))
        key=(report['system'],'.'.join(report['python'].split('.')[:2]))
        if key not in EXPECTED or key in found:
            raise ValueError('Plataforma duplicada o inesperada: '+str(key))
        if report['commit']!=commit or report['status']!='success':
            raise ValueError('Un informe no corresponde al commit o no fue satisfactorio.')
        for name,minimum in (('geometry',69),('distribution',7)):
            result=report['suites'][name]
            if result['tests']<minimum or any(result[field] for field in ('failures','errors','skipped')):
                raise ValueError('Suite incompleta o con fallos: '+name)
        artifact_root=folder/report_path.relative_to(folder).parts[0]
        packages=list(artifact_root.rglob(report['package']['name']))
        if len(packages)!=1:
            raise ValueError('Debe haber exactamente un ZIP por plataforma.')
        digest=hashlib.sha256(packages[0].read_bytes()).hexdigest()
        if digest!=report['package']['sha256']:
            raise ValueError('El ZIP no coincide con su informe.')
        digests.add(digest)
        versions.add(report['version'])
        found[key]=report
    if set(found)!=EXPECTED:
        raise ValueError('Faltan plataformas: '+str(EXPECTED-set(found)))
    if len(digests)!=1 or len(versions)!=1:
        raise ValueError('Las plataformas no generaron el mismo paquete/version.')
    browser_path=folder/'browser-evidence'/'report.json'
    browsers=json.loads(browser_path.read_text(encoding='utf-8'))
    expected={(engine,model) for engine in ('chromium','firefox') for model in ('cuna','bloque-taladrado','cuatro-taladros')}
    if len(browsers)!=len(expected) or {(r['browser'],r['model']) for r in browsers}!=expected:
        raise ValueError('Faltan casos de navegador.')
    if any(r.get('angles')!=24 or not all(r.get(k) for k in ('portable','reducedMotion','width320')) for r in browsers):
        raise ValueError('Comprobación de navegador incompleta.')
    return {'commit':commit,'version':versions.pop(),'package_sha256':digests.pop(),
            'status':'success','python_jobs':list(found.values()),'browsers':browsers}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts',type=Path)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--output',type=Path,default=Path('build/release-readiness.json'))
    args=parser.parse_args()
    try:
        result=validate(args.artifacts,args.commit)
    except (OSError,ValueError,KeyError) as error:
        parser.exit(1,f'Error: {error}\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(args.output)
