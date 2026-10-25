"""Import prototype 3MF/STL files into a real slicer and check physical results."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def check(folder,slicer):
    reports=[]
    profile=folder/'slicer-test-profile'
    for item in json.loads((folder/'catalog.json').read_text(encoding='utf-8')):
        for extension in ('3mf','stl'):
            path=folder/item['id']/('modelo.'+extension)
            result=subprocess.run([str(slicer),'--datadir',str(profile),'--info',str(path)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
            if result.returncode:raise ValueError(result.stderr or result.stdout)
            values=dict(re.findall(r'^([a-z_]+)\s*=\s*(.+)$',result.stdout,re.M))
            if values.get('manifold','').strip()!='yes' or int(values.get('number_of_parts','0'))!=1:
                raise ValueError('El laminador no reconoce un sólido manifold único: '+str(path))
            for key,expected in zip(('size_x','size_y','size_z'),item['dimensionsMm']):
                if not math.isclose(float(values[key]),expected,rel_tol=1e-6):raise ValueError('Dimensiones incorrectas en '+str(path))
            if not math.isclose(float(values['volume']),item['volumeMm3'],rel_tol=1e-6):raise ValueError('Volumen incorrecto en '+str(path))
            reports.append({'model':item['id'],'format':extension,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'values':values,'stdout':result.stdout,'stderr':result.stderr})
    report={'status':'success','slicer_executable':str(slicer),'slicer_executable_sha256':hashlib.sha256(slicer.read_bytes()).hexdigest(),
            'scope':'Import and manifold/dimensions/volume checks. No printer profile, slicing or physical printing performed.','results':reports}
    (folder/'print-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'success','imports':len(reports),'checks':'manifold, dimensions, volume, connected parts'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=ROOT/'build'/'prototipo-assets')
    parser.add_argument('--slicer',type=Path,required=True)
    args=parser.parse_args();check(args.folder.resolve(),args.slicer.resolve())
