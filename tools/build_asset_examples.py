"""Build the generic modular asset prototype and its local GLB preview."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills'/'proyecciones-svg'
NAMES=('rampa','bloque','escalera')


def build(output):
    three=ROOT/'node_modules'/'three'
    if not (three/'build'/'three.module.js').is_file():
        raise ValueError('Ejecuta npm ci para construir la previsualización; el generador Python no necesita Node.')
    output.mkdir(parents=True,exist_ok=True)
    catalog=[]
    for name in NAMES:
        subprocess.run([sys.executable,'-B',str(SKILL/'scripts'/'generar.py'),str(SKILL/'assets'/'modulos'/(name+'.json')),
            '--output-dir',str(output/name),'--viewer','--frames','24','--seconds','6','--export-cota',
            '--export-glb','--export-3mf','--export-stl','--force'],check=True)
        report=json.loads((output/name/'informe.json').read_text(encoding='utf-8'))
        model=json.loads((output/name/'modelo.json').read_text(encoding='utf-8'))
        catalog.append({'id':name,'name':model['name'],'triangles':report['meshes']['triangles'],
            'volumeMm3':report['meshes']['volume_mm3'],'dimensionsMm':[40,40,20],
            'files':report['files']})
    (output/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,target in (('asset_preview.html','index.html'),('asset_preview.js','preview.js')):
        shutil.copyfile(ROOT/'tools'/name,output/target)
    for source,target in (('build/three.module.js','three.module.js'),('examples/jsm/loaders/GLTFLoader.js','addons/loaders/GLTFLoader.js'),
                          ('examples/jsm/utils/BufferGeometryUtils.js','addons/utils/BufferGeometryUtils.js'),
                          ('examples/jsm/controls/OrbitControls.js','addons/controls/OrbitControls.js'),('LICENSE','LICENSE.three.txt')):
        path=output/'vendor'/target;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(three/source,path)
    shutil.copyfile(ROOT/'LICENSE',output/'LICENSE.txt')
    (output/'LEEME.txt').write_text('Biblioteca modular de prueba: rampa, bloque y escalera.\n'
        'Cada modulo ocupa 40 x 40 mm y tiene 20 mm de altura maxima.\n'
        'GLB: metros, Y arriba. 3MF: milimetros, Z arriba. STL: coordenadas en milimetros por convencion.\n'
        'Los modelos no incluyen perfil de impresora, parametros de laminado ni G-code.\n'
        'Los SVG, JSON y Cota conservan su propia documentacion geometrica.\n'
        'Para la previsualizacion: python -m http.server 8780 y abrir http://127.0.0.1:8780/\n'
        'Three.js se incluye solo para abrir los GLB; licencia en vendor/LICENSE.three.txt.\n'
        'Ejemplos de la skill; revisar el resultado antes de fabricar.\n',encoding='utf-8')
    files=[output/name for name in ('index.html','preview.js','catalog.json','LICENSE.txt','LEEME.txt')]
    files+=sorted((output/'vendor').rglob('*'))
    for item in catalog:
        files += [output/item['id']/name for name in item['files']]
    with zipfile.ZipFile(output/'kit-modular.zip','w',compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(p for p in files if p.is_file()):
            info=zipfile.ZipInfo(path.relative_to(output).as_posix(),date_time=(2020,1,1,0,0,0))
            info.create_system=3;info.external_attr=0o100644<<16;archive.writestr(info,path.read_bytes())
    print(output/'index.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'build'/'prototipo-assets')
    args=parser.parse_args();build(args.output_dir)
