"""Install the exact ZIP and independently inspect its exported bored surfaces."""
import argparse
import hashlib
from importlib.metadata import version
import io
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from install_skill import install,verified_files

ROOT=Path(__file__).resolve().parents[1]


def read_surface(path):
    raw=path.read_bytes()
    if path.suffix=='.3mf':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            root=ET.fromstring(archive.read('3D/3dmodel.model'))
        ns='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
        if root.get('unit')!='millimeter':raise ValueError('Unidades 3MF incorrectas.')
        vertices=[tuple(float(n.get(k)) for k in ('x','y','z')) for n in root.iter(ns+'vertex')]
        return [[vertices[int(n.get(k))] for k in ('v1','v2','v3')] for n in root.iter(ns+'triangle')]
    if path.suffix=='.stl':
        count=struct.unpack_from('<I',raw,80)[0]
        if len(raw)!=84+50*count:raise ValueError('Longitud STL incorrecta.')
        return [[struct.unpack_from('<3f',raw,84+50*i+j) for j in (12,24,36)] for i in range(count)]
    magic,ver,length=struct.unpack_from('<III',raw)
    if (magic,ver,length)!=(0x46546c67,2,len(raw)):raise ValueError('Cabecera GLB incorrecta.')
    size,kind=struct.unpack_from('<II',raw,12)
    if kind!=0x4e4f534a:raise ValueError('GLB sin bloque JSON.')
    doc=json.loads(raw[20:20+size]);accessor=doc['accessors'][0]
    if accessor['componentType']!=5126 or accessor['type']!='VEC3':raise ValueError('Accesor GLB incorrecto.')
    view=doc['bufferViews'][accessor['bufferView']]
    start=28+size+view.get('byteOffset',0)+accessor.get('byteOffset',0)
    points=[struct.unpack_from('<3f',raw,start+12*i) for i in range(accessor['count'])]
    points=[(x*1000,-z*1000,y*1000) for x,y,z in points]
    return [points[i:i+3] for i in range(0,len(points),3)]


def check(package,output):
    _,manifest=verified_files(package)
    (ROOT/'build').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mesh-interop-',dir=ROOT/'build') as temp:
        folder=Path(temp);skill,_=install(package,folder/'skills')
        subprocess.run([sys.executable,'-B',str(skill/'scripts'/'generar.py'),str(skill/'assets'/'cuatro-taladros.json'),
            '--output-dir',str(folder/'model'),'--mode','sheet','--sections','--export-cota',
            '--export-glb','--export-3mf','--export-stl'],check=True,capture_output=True,text=True,encoding='utf-8')
        sys.path.insert(0,str(skill/'scripts'))
        # The packaged test helpers audit surfaces by winding and shared edges,
        # independently of the Manifold boolean implementation.
        from test_mallas_taladradas import winding,audit_edges
        from test_exportar_mallas import volume
        info=json.loads((folder/'model'/'informe.json').read_text(encoding='utf-8'))['meshes']
        checks=[]
        voids=[(40,30,15),(32,28.5,5),(48,28.5,5),(40,20.5,5),(40,39.5,5)]
        material=[(5,5,5),(70,45,10),(10,50,10)]
        for extension in ('glb','3mf','stl'):
            file=folder/'model'/('modelo.'+extension);surface=read_surface(file)
            euler=audit_edges(surface);actual=volume(surface)
            sizes=[max(v[i] for tri in surface for v in tri)-min(v[i] for tri in surface for v in tri) for i in range(3)]
            if euler!=-12 or not math.isclose(actual,info['volume_mm3'],rel_tol=1e-6):raise ValueError('Topología o volumen de malla incorrectos.')
            if any(not math.isclose(a,b,rel_tol=1e-6) for a,b in zip(sizes,(80,60,36))):raise ValueError('Escala de malla incorrecta.')
            for point in voids:
                if abs(winding(surface,point))>1e-6:raise ValueError('Conducto obstruido.')
            for point in material:
                if abs(winding(surface,point)-1)>1e-6:raise ValueError('Se perdió material.')
            checks.append({'format':extension,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                'euler':euler,'triangles':len(surface),'bounds_mm':sizes,'volume_mm3':actual,
                'void_checks':len(voids),'material_checks':len(material)})
    report={'status':'success','commit':os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'version':manifest['version'],'package_sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
        'system':platform.system(),'python':platform.python_version(),'machine':platform.machine(),
        'dependencies':{name:version(name) for name in ('manifold3d','numpy')},'model':'cuatro-taladros','genus':info['genus'],
        'mouths':info['tessellation']['mouths'],'radial_sagitta_mm':info['tessellation']['max_radial_sagitta_mm'],'formats':checks}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(check(args.package,args.output))
