"""Portable GLB/3MF/STL; optional Manifold backend for cylindrical voids."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import io
import json
import math
import struct
import xml.etree.ElementTree as ET
import zipfile

import proyectar as p
from exportar_cota import millimeters_per_unit, BORED_TYPES

MF = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
MAX_TRIANGLES = 2048


def scale_vector(v, factor):
    return tuple(x*factor for x in v)


def normalized(vertices):
    minimum = tuple(min(v[i] for v in vertices) for i in range(3))
    maximum = tuple(max(v[i] for v in vertices) for i in range(3))
    span = max(b-a for a,b in zip(minimum,maximum))
    if not math.isfinite(span) or span <= 0:
        raise ValueError('La malla no tiene extensión finita.')
    return [tuple((v[i]-minimum[i])/span for i in range(3)) for v in vertices], span


def validate_mesh(vertices, triangles, genus=0):
    """Closed, oriented, connected surface with the expected genus and vertex links.

    The constructor restricts source geometry to a simple extrusion or a convex
    polyhedron. This check is not a general triangle-intersection/CSG solver.
    """
    if type(genus) is not int or not 0 <= genus <= 7:
        raise ValueError('Género topológico fuera del alcance 0..7.')
    if not 4 <= len(vertices) <= (32768 if genus else p.MAX_VERTICES) or not 4 <= len(triangles) <= (65536 if genus else MAX_TRIANGLES):
        raise ValueError('Malla fuera del límite de vértices o triángulos.')
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vertices):
        raise ValueError('La malla contiene coordenadas no finitas.')
    if len(set(vertices)) != len(vertices):
        raise ValueError('La precisión de salida colapsa vértices diferentes.')
    local, span = normalized(vertices)
    edges = defaultdict(list)
    links = defaultdict(list)
    used, seen = set(), set()
    for index, tri in enumerate(triangles):
        if len(tri)!=3 or any(type(i) is not int or not 0<=i<len(vertices) for i in tri) or len(set(tri))!=3:
            raise ValueError('Triángulo con índices inválidos.')
        if tuple(sorted(tri)) in seen:
            raise ValueError('La malla contiene triángulos duplicados.')
        seen.add(tuple(sorted(tri)))
        a,b,c = [local[i] for i in tri]
        u,v = p.sub(b,a),p.sub(c,a)
        if p.length(p.cross(u,v)) <= math.hypot(*u)*math.hypot(*v)*1e-12:
            raise ValueError('La precisión de salida produce un triángulo degenerado.')
        used.update(tri)
        for a,b in zip(tri,tri[1:]+tri[:1]):
            edges[tuple(sorted((a,b)))].append((a,b,index))
        for i in range(3):
            links[tri[i]].append((tri[(i+1)%3],tri[(i+2)%3]))
    if used != set(range(len(vertices))):
        raise ValueError('La malla contiene vértices sin usar.')
    adjacency = defaultdict(set)
    for owners in edges.values():
        if len(owners)!=2 or owners[0][:2] != tuple(reversed(owners[1][:2])):
            raise ValueError('La malla no es cerrada y orientada: cada arista debe unir dos caras opuestas.')
        adjacency[owners[0][2]].add(owners[1][2]);adjacency[owners[1][2]].add(owners[0][2])
    reached, pending = set(), [0]
    while pending:
        current=pending.pop()
        if current not in reached:
            reached.add(current);pending.extend(adjacency[current]-reached)
    if len(reached)!=len(triangles) or len(vertices)-len(edges)+len(triangles)!=2-2*genus:
        raise ValueError('Se requiere una sola superficie conectada con la topología esperada.')
    for segments in links.values():
        graph=defaultdict(set)
        for a,b in segments:graph[a].add(b);graph[b].add(a)
        if any(len(neighbors)!=2 for neighbors in graph.values()):
            raise ValueError('Vértice no manifold en la malla.')
        visited,pending=set(),[next(iter(graph))]
        while pending:
            v=pending.pop()
            if v not in visited:visited.add(v);pending.extend(graph[v]-visited)
        if len(visited)!=len(graph):raise ValueError('El entorno de un vértice no forma un ciclo.')
    volume = math.fsum(p.dot(local[a],p.cross(local[b],local[c])) for a,b,c in triangles)/6
    if volume <= 0 or not math.isfinite(volume):
        raise ValueError('La malla debe encerrar volumen positivo con normales exteriores.')
    try:
        physical_volume=volume*span**3
    except OverflowError as error:
        raise ValueError('El volumen físico excede el rango numérico.') from error
    if not math.isfinite(physical_volume) or physical_volume<=0:
        raise ValueError('El volumen físico no puede representarse como un valor positivo finito.')
    return physical_volume


def float32_vertices(vertices, triangles, genus=0):
    try:
        quantized=[struct.unpack('<3f',struct.pack('<3f',*v)) for v in vertices]
    except (OverflowError,struct.error) as error:
        raise ValueError('La geometría excede la precisión float32 del formato.') from error
    before=validate_mesh(vertices,triangles,genus)
    after=validate_mesh(quantized,triangles,genus)
    if not math.isclose(before,after,rel_tol=1e-5,abs_tol=0):
        raise ValueError('La cuantización float32 altera demasiado el volumen.')
    return quantized


@dataclass
class Mesh:
    vertices: list
    triangles: list
    name: str
    color: tuple
    unit_mm: float
    source_sha256: str
    volume_mm3: float
    genus: int = 0
    tessellation: dict | None = None

    def info(self):
        return {'scope':'simple extrusion, convex mesh, or validated cylindrical through-bores; one closed surface',
                'genus':self.genus,'tessellation':self.tessellation,
                'vertices':len(self.vertices),'triangles':len(self.triangles),'volume_mm3':self.volume_mm3,
                'bounds_mm':[[min(v[i] for v in self.vertices) for i in range(3)],
                             [max(v[i] for v in self.vertices) for i in range(3)]],
                'millimeters_per_source_unit':self.unit_mm,'source_sha256':self.source_sha256,
                'glb':{'units':'m','axes':'(x,y,z) -> (x,z,-y); right handed, Y up','origin':'source origin retained'},
                'printing':{'units':'mm','axes':'source X/Y/Z, Z up','printer_profile':None,'sliced':False}}


def prepare(data, unit_mm=None, tolerance_mm=0.02):
    kind=data.get('type')
    if kind not in ('extrusion','mesh','block_with_bore',*BORED_TYPES):
        raise ValueError('Tipo de modelo no admitido para GLB/3MF/STL.')
    tolerance_mm=p.number(tolerance_mm)
    if tolerance_mm<=0:raise ValueError('La tolerancia radial de malla debe ser positiva.')
    try:
        factor=millimeters_per_unit(data.get('units','u'),unit_mm)
    except ValueError as error:
        raise ValueError('GLB/3MF/STL requiere una equivalencia física válida; indica --unit-mm (milímetros por unidad).') from error
    genus,tessellation=0,None
    if kind in ('block_with_bore',*BORED_TYPES):
        from mallas_taladradas import triangulate_bores
        vertices,triangles,genus,tessellation=triangulate_bores(data,factor,tolerance_mm)
    else:
        vertices,triangles=polyhedron(data,factor)
    volume=validate_mesh(vertices,triangles,genus)
    asset=data.get('asset',{})
    if not isinstance(asset,dict):raise ValueError('asset debe ser un objeto.')
    color=p.point(asset.get('base_color',[.18,.48,.70,1]),4)
    if any(not 0<=v<=1 for v in color):raise ValueError('asset.base_color requiere cuatro componentes entre 0 y 1.')
    source=json.dumps(data,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':')).encode('utf-8')
    return Mesh(vertices,triangles,str(data.get('name','Pieza')),color,factor,hashlib.sha256(source).hexdigest(),volume,genus,tessellation)


def polyhedron(data,factor):
    model=p.Model(data)
    triangles=[tuple(t) for t in model.triangles]
    orientation=math.fsum(p.dot(model.vertices[a],p.cross(model.vertices[b],model.vertices[c])) for a,b,c in triangles)
    if orientation<0:triangles=[(a,c,b) for a,b,c in triangles]
    if data['type']=='mesh':
        sign=1 if orientation>0 else -1
        for face,normal in zip(model.faces,model.normals):
            normal=scale_vector(normal,sign)
            if any(p.dot(normal,p.sub(v,model.vertices[face[0]]))>1e-10 for v in model.vertices):
                raise ValueError('La exportación inicial de type=mesh requiere un cuerpo convexo; usa extrusion para perfiles cóncavos simples.')
        raw=[tuple(v) for v in data['vertices']]
    else:
        profile=[tuple(v) for v in data['profile']]
        if p.signed_area(profile)<0:profile.reverse()
        raw=[(x,y,z) for y in (0.,data['depth']) for x,z in profile]
    vertices=[scale_vector(v,factor) for v in raw]
    return vertices,triangles


def glb(mesh):
    vertices=[(x/1000,z/1000,-y/1000) for x,y,z in mesh.vertices]
    vertices=float32_vertices(vertices,mesh.triangles,mesh.genus)
    positions,normals=[],[]
    for tri in mesh.triangles:
        a,b,c=[vertices[i] for i in tri]
        normal=p.cross(p.sub(b,a),p.sub(c,a));normal=scale_vector(normal,1/math.hypot(*normal))
        for v in (a,b,c):positions.extend(v);normals.extend(normal)
    raw_positions=struct.pack('<'+'f'*len(positions),*positions)
    raw_normals=struct.pack('<'+'f'*len(normals),*normals)
    binary=raw_positions+raw_normals
    color=list(mesh.color)
    material={'name':'Color base','pbrMetallicRoughness':{'baseColorFactor':color,'metallicFactor':0,'roughnessFactor':.8},'doubleSided':False}
    if color[3]<1:material['alphaMode']='BLEND'
    document={'asset':{'version':'2.0','generator':'proyecciones-svg / exportar_mallas'},'scene':0,
        'scenes':[{'nodes':[0]}],'nodes':[{'name':mesh.name,'mesh':0,'extras':{'source_sha256':mesh.source_sha256}}],
        'meshes':[{'name':mesh.name,'primitives':[{'attributes':{'POSITION':0,'NORMAL':1},'material':0,'mode':4}]}],
        'materials':[material],'buffers':[{'byteLength':len(binary)}],
        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(raw_positions),'target':34962},
                       {'buffer':0,'byteOffset':len(raw_positions),'byteLength':len(raw_normals),'target':34962}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':len(positions)//3,'type':'VEC3',
                      'min':[min(v[i] for v in vertices) for i in range(3)],'max':[max(v[i] for v in vertices) for i in range(3)]},
                     {'bufferView':1,'componentType':5126,'count':len(normals)//3,'type':'VEC3'}],
        'extras':{'units':'meter','source_units_to_mm':mesh.unit_mm,'collision_mesh':False,'rigged':False}}
    text=json.dumps(document,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()
    text+=b' '*((-len(text))%4)
    binary+=b'\0'*((-len(binary))%4)
    size=12+8+len(text)+8+len(binary)
    return struct.pack('<III',0x46546c67,2,size)+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary


def stl(mesh):
    vertices=float32_vertices(mesh.vertices,mesh.triangles,mesh.genus)
    out=io.BytesIO();out.write(b'proyecciones-svg | units=mm | source Z up'.ljust(80,b'\0'))
    out.write(struct.pack('<I',len(mesh.triangles)))
    for tri in mesh.triangles:
        a,b,c=[vertices[i] for i in tri]
        normal=p.cross(p.sub(b,a),p.sub(c,a));normal=scale_vector(normal,1/math.hypot(*normal))
        out.write(struct.pack('<12fH',*normal,*a,*b,*c,0))
    return out.getvalue()


def three_mf(mesh):
    root=ET.Element('model',{'unit':'millimeter','xml:lang':'es-ES','xmlns':MF})
    ET.SubElement(root,'metadata',{'name':'Title'}).text=mesh.name
    ET.SubElement(root,'metadata',{'name':'Description'}).text='Modelo geométrico; sin perfil de impresora ni parámetros de laminado.'
    resources=ET.SubElement(root,'resources')
    obj=ET.SubElement(resources,'object',{'id':'1','type':'model','name':mesh.name})
    geometry=ET.SubElement(obj,'mesh');vertices=ET.SubElement(geometry,'vertices')
    for point in mesh.vertices:ET.SubElement(vertices,'vertex',{key:format(value,'.17g') for key,value in zip(('x','y','z'),point)})
    triangles=ET.SubElement(geometry,'triangles')
    for tri in mesh.triangles:ET.SubElement(triangles,'triangle',{key:str(i) for key,i in zip(('v1','v2','v3'),tri)})
    build=ET.SubElement(root,'build');ET.SubElement(build,'item',{'objectid':'1'})
    model=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    ET.fromstring(model)
    contents=b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
    rels=b'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted({'[Content_Types].xml':contents,'_rels/.rels':rels,'3D/3dmodel.model':model}.items()):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
            archive.writestr(info,data)
    return out.getvalue()
