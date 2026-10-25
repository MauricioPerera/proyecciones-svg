"""Build public, static examples with the stable SVG skill (standard library only)."""
import argparse
from copy import deepcopy
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
STYLE='''
.site-model{--paper:#fffef9;--ink:#193c36;--faint:#718274}
.site-model .paper,.site-model .face{fill:var(--paper);stroke:none}
.site-model .edge{fill:none;stroke:var(--ink);stroke-width:1.65;stroke-linecap:round;stroke-linejoin:round}
.site-model .hidden-edge{fill:none;stroke:var(--faint);stroke-width:1;stroke-dasharray:5 4}
.site-model .dimension{fill:none;stroke:var(--faint);stroke-width:1}
.site-model .curve{vector-effect:non-scaling-stroke}
.site-model .bore-wall{fill:var(--ink);fill-opacity:.12}
.site-model .axis{fill:none;stroke:var(--faint);stroke-width:1;stroke-dasharray:10 3 2 3}
'''

def tag(name):
    return '{'+NS+'}'+name

def clean(root,prefix):
    for parent in root.iter():
        for child in list(parent):
            if child.tag in {tag('metadata'),tag('style'),tag('animate'),tag('text')} or child.get('class') in {'paper','still-frame'}:
                parent.remove(child)
    for node in root.iter():
        for key,value in list(node.attrib.items()):
            if key=='id':
                node.set(key,prefix+value)
            elif 'url(#' in value:
                node.set(key,value.replace('url(#','url(#'+prefix))
    root.attrib.pop('aria-labelledby',None)
    root.set('class','site-model')
    ET.SubElement(root,tag('style')).text=STYLE
    return root

def save(root,path):
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def bounds(group):
    xs=[];ys=[]
    for node in group.iter():
        if node.get('class')=='face' and node.tag==tag('path'):
            values=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',node.get('d',''))]
            xs.extend(values[::2]);ys.extend(values[1::2])
    if not xs:
        raise ValueError('No exterior face bounds in projection.')
    return min(xs),min(ys),max(xs),max(ys)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-dir',type=Path,default=ROOT/'skills'/'proyecciones-svg')
    args=parser.parse_args()
    skill=args.skill_dir.resolve()
    version=(ROOT/'skills'/'proyecciones-svg'/'VERSION').read_text().strip()
    if (skill/'VERSION').read_text().strip()!=version:
        raise ValueError('Use the documented stable version '+version+'.')
    output=ROOT/'docs'/'assets'/'models'
    source_models={'cuna':skill/'assets'/'cuna.json','escalon':skill/'assets'/'escalon.json',
                   'taladro':skill/'assets'/'bloque-taladrado.json',
                   'irregular':output/'irregular'/'modelo.json'}
    (ROOT/'build').mkdir(exist_ok=True)
    for key,source in source_models.items():
        folder=output/key
        folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='site-'+key+'-',dir=ROOT/'build') as temporary:
            target=Path(temporary)/'generated'
            command=[sys.executable,'-B',str(skill/'scripts'/'generar.py'),str(source),
                '--output-dir',str(target),'--mode','all','--frames','24','--seconds','8',
                '--viewer','--export-cota','--elevation','50','--hidden','dash']
            subprocess.run(command,check=True,capture_output=True,text=True,encoding='utf-8')
            for name in ('vistas.svg','giro.svg','modelo.json','modelo.cota','visor.html'):
                shutil.copyfile(target/name,folder/name)
            oblique=clean(ET.parse(target/'angulo.svg').getroot(),key+'-angle-')
            x0,y0,x1,y1=bounds(oblique)
            oblique.set('viewBox',f'{x0-35:.4f} {y0-25:.4f} {x1-x0+70:.4f} {y1-y0+50:.4f}')
            oblique.find(tag('style')).text+='\n.site-model .hidden-edge{display:none}\n'
            save(oblique,folder/'angulo.svg')
            rotation=clean(ET.parse(target/'giro.svg').getroot(),key+'-rotation-')
            rotation.set('viewBox','0 65 640 375')
            rotation.set('aria-label','Giro ortográfico de '+key)
            for i,node in enumerate(rotation.findall('.//'+tag('g')+'[@data-frame]')):
                node.set('visibility','visible' if i==0 else 'hidden')
            save(rotation,folder/'rotation.svg')
            sheet=ET.parse(target/'vistas.svg').getroot()
            groups={node.get('data-view'):node for node in sheet if node.get('data-view')}
            boxes={name:bounds(group) for name,group in groups.items()}
            width=max(box[2]-box[0] for box in boxes.values())+40
            height=max(box[3]-box[1] for box in boxes.values())+35
            for name,filename in [('Planta','planta.svg'),('Alzado','alzado.svg'),('Perfil derecho','perfil.svg')]:
                root=ET.Element(tag('svg'),{'viewBox':f'0 0 {width:.4f} {height:.4f}',
                    'role':'img','aria-label':name})
                box=boxes[name]
                tx=(width-(box[2]-box[0]))/2-box[0]
                ty=(height-(box[3]-box[1]))/2-box[1]
                parent=ET.SubElement(root,tag('g'),{'transform':f'translate({tx:.4f} {ty:.4f})'})
                parent.append(deepcopy(groups[name]))
                clean(root,key+'-'+filename+'-')
                save(root,folder/filename)
        for artifact in folder.iterdir():
            text=artifact.read_text(encoding='utf-8')
            artifact.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n',encoding='utf-8',newline='\n')
        print(key+': ready',flush=True)
    shutil.copyfile(ROOT/'LICENSE',ROOT/'docs'/'assets'/'LICENSE.txt')

if __name__=='__main__':
    main()
