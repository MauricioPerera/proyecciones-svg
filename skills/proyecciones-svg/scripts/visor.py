"""Build a standalone SVG viewer without local paths or runtime dependencies."""
import json
import re
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


def create_viewer(folder, seconds=6, loop=False, sections=False):
    template=(Path(__file__).resolve().parent.parent/'assets'/'visor.html').read_text(encoding='utf-8')
    values={
        '__SHEET__':embedded_svg(folder/'vistas.svg','sheet-'),
        '__ROTATION__':embedded_svg(folder/'giro.svg','rotation-',True),
        '__SETTINGS__':json.dumps({'seconds':seconds,'loop':loop}),
        '__SECTIONS__':section_panel(folder) if sections else '',
    }
    for token in values:
        if template.count(token)!=1:
            raise ValueError('Plantilla de visor inválida: '+token)
    # Substitute only template tokens, never marker-like text in inserted SVG data.
    template=re.sub('|'.join(map(re.escape,values)),lambda match:values[match.group()],template)
    (folder/'visor.html').write_text(template,encoding='utf-8')


def section_panel(folder):
    has_bores=any(n.get('data-bore') is not None for n in ET.parse(folder/'cortes.svg').getroot().iter())
    svg=embedded_svg(folder/'cortes.svg','cuts-')
    control='<label><input type="checkbox" id="section-guides"> Mostrar contornos auxiliares de los taladros</label>' if has_bores else ''
    help_text='El rayado indica material. El blanco es la unión de los vaciados; sus bordes enterrados no son aristas.' if has_bores else 'El rayado indica el material atravesado por el plano del corte.'
    script='''<script>(()=>{const control=document.getElementById('section-guides');control.addEventListener('change',()=>{document.getElementById('sections').classList.toggle('show-guides',control.checked);document.getElementById('section-help').textContent=control.checked?'Guías discontinuas: cada cilindro cortado por el plano, incluso dentro de otro vaciado. Son auxiliares, no aristas del sólido.':'El rayado indica material. El blanco es la unión de los vaciados; sus bordes enterrados no son aristas.';});})();</script>''' if has_bores else ''
    return ('<section class="panel section-panel" id="sections"><h2>Vista en corte</h2><div class="drawing">'+svg+'</div>'
        +'<div class="controls">'+control+'<a href="cortes.svg" download>Descargar cortes SVG</a></div>'
        +'<p class="section-help" id="section-help">'+help_text+'</p></section>'
        +'<style>.section-panel{margin-bottom:20px}.section-panel .section-help{padding:0 16px 16px;margin:0;color:#4f6270}.section-panel.show-guides .section-guides{display:inline}</style>'+script)
