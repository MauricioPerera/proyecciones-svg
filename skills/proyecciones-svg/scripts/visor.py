"""Build a standalone SVG viewer without local paths or runtime dependencies."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS='http://www.w3.org/2000/svg'


def embedded_svg(path, prefix, rotation=False):
    root=ET.parse(path).getroot()
    for parent in root.iter():
        for child in list(parent):
            if child.tag==f'{{{NS}}}animate' or child.get('class')=='still-frame':
                parent.remove(child)
    for node in root.iter():
        for key,value in list(node.attrib.items()):
            if key=='id':
                node.set(key,prefix+value)
            elif 'url(#' in value:
                node.set(key,value.replace('url(#','url(#'+prefix))
            elif key=='aria-labelledby':
                node.set(key,' '.join(prefix+item for item in value.split()))
        if rotation and node.get('class')=='motion-frames':
            node.set('class','viewer-frames')
        if rotation and 'data-frame' in node.attrib:
            # The viewer controls frames; autonomous SVG files keep their SMIL.
            node.set('visibility','visible' if node.get('data-frame')=='0' else 'hidden')
    return ET.tostring(root,encoding='unicode')


def create_viewer(folder, seconds=6, loop=False):
    template=(Path(__file__).resolve().parent.parent/'assets'/'visor.html').read_text(encoding='utf-8')
    values={
        '__SHEET__':embedded_svg(folder/'vistas.svg','sheet-'),
        '__ROTATION__':embedded_svg(folder/'giro.svg','rotation-',True),
        '__SETTINGS__':json.dumps({'seconds':seconds,'loop':loop}),
    }
    for token,value in values.items():
        if template.count(token)!=1:
            raise ValueError('Plantilla de visor inválida: '+token)
        template=template.replace(token,value)
    (folder/'visor.html').write_text(template,encoding='utf-8')
