"""Check static landing links, release scope and derived SVG examples."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'docs'

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        for name in ('src','href'):
            if a.get(name):self.links.append(a[name])
        if a.get('data-copy-target'):
            self.links.append('#'+a['data-copy-target'])

def main():
    page=Page()
    source=(SITE/'index.html').read_text(encoding='utf-8')
    page.feed(source)
    assert len(page.ids)==len(set(page.ids)),'Duplicate HTML IDs'
    for link in page.links:
        parsed=urlsplit(link)
        if parsed.scheme or parsed.netloc:continue
        if not parsed.path:
            assert not parsed.fragment or parsed.fragment in page.ids,link
        else:
            path=(SITE/unquote(parsed.path)).resolve()
            assert path.is_relative_to(SITE.resolve()) and path.is_file(),link
    assert 'repositorio privado' in source
    assert 'macOS: validación pendiente' in source
    ns={'s':'http://www.w3.org/2000/svg'}
    for key in ('cuna','escalon','taladro','irregular'):
        folder=SITE/'assets'/'models'/key
        model=json.loads((folder/'modelo.json').read_text(encoding='utf-8'))
        assert model['type']
        boxes=[]
        for name in ('planta.svg','alzado.svg','perfil.svg'):
            root=ET.parse(folder/name).getroot()
            boxes.append(root.get('viewBox'))
        assert len(set(boxes))==1,'Projection scale differs: '+key
        rotation=ET.parse(folder/'rotation.svg').getroot()
        frames=rotation.findall('.//s:g[@data-frame]',ns)
        assert len(frames)==24,key
        assert len([frame for frame in frames if frame.get('visibility')=='visible'])==1,key
        ids=[n.get('id') for n in rotation.iter() if n.get('id')]
        assert len(ids)==len(set(ids)),key
        assert not rotation.findall('.//s:animate',ns),key
        for node in rotation.iter():
            for value in node.attrib.values():
                if 'url(#' in value:
                    assert value.split('url(#',1)[1].split(')',1)[0] in ids,value
        for name in ('vistas.svg','giro.svg','angulo.svg','rotation.svg','planta.svg','alzado.svg','perfil.svg'):
            root=ET.parse(folder/name).getroot()
            assert not any(n.tag.rsplit('}',1)[-1] in ('script','image','foreignObject') for n in root.iter()),name
    print(f'Landing OK: {len(page.ids)} unique IDs, {len(page.links)} references, four vector examples and consistent projection scales.')

if __name__=='__main__':
    main()
