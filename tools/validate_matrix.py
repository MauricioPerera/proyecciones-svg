"""Validate a complete declared platform profile and byte-identical ZIPs."""
import argparse
import hashlib
import json
import math
from pathlib import Path


EXPECTED={(system,python) for system in ('Linux','Windows','Darwin') for python in ('3.10','3.14')}
PROFILES={'all':EXPECTED,'windows-linux':{pair for pair in EXPECTED if pair[0]!='Darwin'}}
COTA_COMMIT='e43e37de4017e6b87f72180b0f4e6162943f4880'


def requires_cota(version):
    return tuple(int(v) for v in version.split('.')[:2])>=(1,1)


def check_cota(report,python_report):
    if (report.get('status')!='success' or report.get('tests')!=2
        or any(report.get(k)!=python_report[k] for k in ('commit','version','system','python'))
        or report.get('package_sha256')!=python_report['package']['sha256']
        or report.get('cota_version')!='1.0.0' or report.get('cota_commit')!=COTA_COMMIT):
        raise ValueError('La evidencia Cota no aprueba el mismo paquete, entorno o revisión.')
    cases={case['model']:case for case in report.get('cases',[])}
    if len(report.get('cases',[]))!=2 or set(cases)!={'cuna','cuatro-taladros'}:
        raise ValueError('Faltan casos de intercambio Cota.')
    wedge,four=cases['cuna'],cases['cuatro-taladros']
    if (wedge.get('views_mm')!=[[60,30],[60,40],[40,30]] or wedge.get('material_checks')!=3
        or not math.isclose(wedge.get('volume_mm3',0),36000,abs_tol=0.05)):
        raise ValueError('La cuña Cota no conserva vistas, volumen o comprobaciones de material.')
    expected,actual=four.get('body_volume_expected_mm3',0),four.get('body_volume_actual_mm3',0)
    checks=four.get('material_checks',[])
    if (not math.isfinite(expected) or expected<=0 or not math.isfinite(actual)
        or abs(actual-expected)>0.05 or four.get('faces',0)<=0 or len(checks)!=15
        or sum(row.get('material') is False for row in checks)!=12
        or sum(row.get('material') is True for row in checks)!=3):
        raise ValueError('La pieza Cota no conserva cubierta, material y cuatro conductos.')
    exports=report.get('exports',{})
    if set(exports)!={'cuna','cuatro-taladros'} or any(
            item.get('units')!='mm' or len(item.get('sha256',''))!=64 for item in exports.values()):
        raise ValueError('Faltan los archivos Cota comprobados y sus unidades.')


def validate(folder,commit,profile='all'):
    if profile not in PROFILES:
        raise ValueError('Perfil de validación desconocido.')
    required=PROFILES[profile]
    found={}
    digests=set()
    versions=set()
    cota_jobs=[]
    for report_path in sorted(folder.glob('python-*/**/report.json')):
        report=json.loads(report_path.read_text(encoding='utf-8'))
        key=(report['system'],'.'.join(report['python'].split('.')[:2]))
        if key not in required or key in found:
            raise ValueError('Plataforma duplicada o inesperada: '+str(key))
        if report['commit']!=commit or report['status']!='success':
            raise ValueError('Un informe no corresponde al commit o no fue satisfactorio.')
        minimums=(('geometry',77),('distribution',22)) if requires_cota(report['version']) else (('geometry',69),('distribution',16))
        for name,minimum in minimums:
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
        if requires_cota(report['version']):
            cota_path=report_path.parent/'cota-interop.json'
            if not cota_path.is_file():
                raise ValueError('Falta la comprobación Cota del paquete en '+str(key))
            cota=json.loads(cota_path.read_text(encoding='utf-8'))
            check_cota(cota,report)
            cota_jobs.append(cota)
        digests.add(digest)
        versions.add(report['version'])
        found[key]=report
    if set(found)!=required:
        raise ValueError('Faltan plataformas: '+str(required-set(found)))
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
            'cota_jobs':cota_jobs,
            'status':'success','validation_profile':profile,
            'validated_systems':sorted({pair[0] for pair in required}),
            'pending_systems':sorted({pair[0] for pair in EXPECTED}-{pair[0] for pair in required}),
            'python_jobs':list(found.values()),'browsers':browsers}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts',type=Path)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--profile',choices=tuple(PROFILES),default='all')
    parser.add_argument('--output',type=Path,default=Path('build/release-readiness.json'))
    args=parser.parse_args()
    try:
        result=validate(args.artifacts,args.commit,args.profile)
    except (OSError,ValueError,KeyError) as error:
        parser.exit(1,f'Error: {error}\n')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(args.output)
