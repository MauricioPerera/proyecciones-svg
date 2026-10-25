"""Build the four-communicating-bores example and a local preview of its GLB."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills'/'proyecciones-svg'


def build(output):
    output.mkdir(parents=True,exist_ok=True)
    folder=output/'cuatro-taladros'
    subprocess.run([sys.executable,'-B',str(SKILL/'scripts'/'generar.py'),str(SKILL/'assets'/'cuatro-taladros.json'),
        '--output-dir',str(folder),'--frames','24','--viewer','--sections','--export-cota',
        '--export-glb','--export-3mf','--export-stl','--force'],check=True)
    report=json.loads((folder/'informe.json').read_text(encoding='utf-8'))
    bounds=report['meshes']['bounds_mm']
    catalog=[{'id':'cuatro-taladros','name':'Pieza irregular · cuatro conductos comunicados',
        'dimensionsMm':[b-a for a,b in zip(*bounds)],'volumeMm3':report['meshes']['volume_mm3'],
        'triangles':report['meshes']['triangles'],'files':report['files'],'mesh':report['meshes']}]
    (output/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for source,target in (('bored_asset_preview.html','index.html'),('bored_asset_preview.js','preview.js')):
        shutil.copyfile(ROOT/'tools'/source,output/target)
    three=ROOT/'node_modules'/'three'
    for source,target in (('build/three.module.js','three.module.js'),('examples/jsm/loaders/GLTFLoader.js','addons/loaders/GLTFLoader.js'),
            ('examples/jsm/utils/BufferGeometryUtils.js','addons/utils/BufferGeometryUtils.js'),
            ('examples/jsm/controls/OrbitControls.js','addons/controls/OrbitControls.js'),('LICENSE','LICENSE.three.txt')):
        path=output/'vendor'/target;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(three/source,path)
    shutil.copyfile(ROOT/'LICENSE',output/'LICENSE.txt')
    (output/'LEEME.txt').write_text('Pieza irregular con cuatro taladros cilindricos comunicados. Ejemplo de la version 1.2.0.\n'
        'GLB en metros y Y arriba; 3MF/STL en milimetros y Z arriba.\n'
        'Diametros nominales 12, 8, 6 y 4 mm. Cilindros facetados inscritos, flecha radial maxima 0.02 mm.\n'
        'Esta cota radial no es una tolerancia de fabricacion ni una cota de error de todas las intersecciones.\n'
        'Los archivos incluyen el cuerpo completo. El recorte del visor es solo de visualizacion.\n'
        'No se incluye perfil de impresora, laminado ni G-code. No hay impresion fisica comprobada.\n'
        'Para abrir el visor local: python -m http.server 8781, luego http://127.0.0.1:8781/\n'
        'Three.js se usa solo para previsualizar el GLB; licencia en vendor/LICENSE.three.txt.\n',encoding='utf-8')
    files=[output/name for name in ('index.html','preview.js','catalog.json','LEEME.txt','LICENSE.txt')]
    files+=sorted((output/'vendor').rglob('*'))
    files += [folder/name for name in report['files']]
    files.append(folder/'informe.json')
    # Timing belongs to the separate report; exclude it from the downloadable kit.
    files=[f for f in files if f.is_file() and f.name!='informe.json']
    target=output/'cuatro-taladros-kit.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED) as archive:
        for file in sorted(files):
            info=zipfile.ZipInfo(file.relative_to(output).as_posix(),date_time=(2020,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16;archive.writestr(info,file.read_bytes())
    print(json.dumps({'preview':str(output/'index.html'),'kit_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'build'/'cuatro-taladros-mallas')
    args=parser.parse_args();build(args.output_dir)
