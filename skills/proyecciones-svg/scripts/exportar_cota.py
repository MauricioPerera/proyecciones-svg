"""Export validated skill geometry to Cota schema 1, using only Python's standard library."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

SCHEMA_VERSION = 1
CYLINDER_SEGMENTS = 64
MILLIMETERS = {'mm':1.0, 'cm':10.0, 'm':1000.0, 'km':1e6,
               'um':1e-3, 'nm':1e-6, 'in':25.4, 'ft':304.8}
BORED_TYPES = {'sloped_prism_with_bore', 'crossed_bores', 'unequal_crossed_bores',
               'triple_crossed_bores', 'quadruple_crossed_bores'}


def millimeters_per_unit(units, override=None):
    key = str(units).strip().casefold().replace('µ','u').replace('μ','u')
    factor = override if override is not None else MILLIMETERS.get(key)
    if factor is None:
        raise ValueError('Unidad sin equivalencia física para Cota: '+str(units)+
                         '. Indica --cota-unit-mm (milímetros por unidad del JSON).')
    factor = float(factor)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError('--cota-unit-mm debe ser finito y positivo.')
    return factor


def ccw(points):
    """Orient a convex footprint without a translation-dependent area calculation."""
    x0,y0 = points[0]
    area = math.fsum((a[0]-x0)*(b[1]-y0)-(b[0]-x0)*(a[1]-y0)
                     for a,b in zip(points,points[1:]+points[:1]))
    return list(reversed(points)) if area < 0 else points


def sloped_body(bottom, top, roof):
    """Clip an extrusion below the roof with an oriented box.

    Cota 1.0.0's LOFT has inconsistent cap/side winding for this construction;
    its boolean evaluator needs the consistently oriented EXTRUDE and BOX.
    """
    normal = [-roof['slope_x'],-roof['slope_y'],1.0]
    length = math.hypot(*normal)
    normal = [v/length for v in normal]
    u = [1.0,0.0,roof['slope_x']]
    length = math.hypot(*u)
    u = [v/length for v in u]
    v = [normal[1]*u[2]-normal[2]*u[1], normal[2]*u[0]-normal[0]*u[2],
         normal[0]*u[1]-normal[1]*u[0]]
    anchor = top[0]
    offsets = [[x-a for x,a in zip(point,anchor)] for point in bottom+top]
    project = lambda axis: [math.fsum(x*a for x,a in zip(point,axis)) for point in offsets]
    us,vs,ns = project(u),project(v),project(normal)
    diagonal = math.hypot(*(max(p[i] for p in bottom+top)-min(p[i] for p in bottom+top)
                            for i in range(3)))
    margin = diagonal*0.05
    depth = -min(ns)+margin
    origin = [a+(min(us)-margin)*x+(min(vs)-margin)*y-depth*n
              for a,x,y,n in zip(anchor,u,v,normal)]
    prism = {'op':'EXTRUDE','profile':bottom,'axis':[0.0,0.0,1.0],
             'height':max(p[2] for p in top)+margin}
    clip = {'op':'BOX','origin':origin,'width':max(us)-min(us)+2*margin,
            'depth':max(vs)-min(vs)+2*margin,'height':depth,'basis':{'x':u,'y':v}}
    return {'op':'INTERSECT','operands':[prism,clip]}


def subtract_bores(body, vertices, bores, factor):
    minimum = [min(v[i] for v in vertices) for i in range(3)]
    maximum = [max(v[i] for v in vertices) for i in range(3)]
    diagonal = math.dist(minimum,maximum)
    cutters = []
    for bore in bores:
        direction = bore['direction'] if bore['axis']=='inclined' else [0.0,0.0,1.0]
        length = math.hypot(*direction)
        axis = [v/length for v in direction]
        center = [bore['center'][0]*factor,bore['center'][1]*factor,0.0]
        # Both end caps lie beyond every body vertex along this axis. The cutter
        # therefore crosses the whole body, including its inclined roof.
        along = [math.fsum((v-c)*a for v,c,a in zip(point,center,axis)) for point in vertices]
        margin = diagonal*0.05
        low,high = min(along)-margin,max(along)+margin
        cutters.append({'op':'CYLINDER', 'base':[c+a*low for c,a in zip(center,axis)],
                        'axis':axis, 'height':high-low, 'radius':bore['diameter']*factor/2,
                        'segments':CYLINDER_SEGMENTS})
    return {'op':'SUBTRACT','operands':[body,*cutters]}


def entity(data, factor):
    kind = data['type']
    if kind == 'extrusion':
        return 'SOLID3D', {'op':'EXTRUDE',
            'profile':[[x*factor,0.0,z*factor] for x,z in data['profile']],
            'height':data['depth']*factor, 'axis':[0.0,1.0,0.0]}
    if kind == 'mesh':
        from proyectar import Model, dot, cross
        model = Model(data)
        triangles = [list(t) for t in model.triangles]
        volume = math.fsum(dot(model.vertices[a],cross(model.vertices[b],model.vertices[c]))
                           for a,b,c in triangles)
        if volume < 0:
            triangles = [[a,c,b] for a,b,c in triangles]
        return 'MESH3D', {'vertices':[[v*factor for v in point] for point in data['vertices']],
                          'faces':triangles}
    if kind == 'block_with_bore':
        w,d,h = [v*factor for v in data['size']]
        body = {'op':'BOX','origin':[0.0,0.0,0.0],'width':w,'depth':d,'height':h}
        vertices = [[x,y,z] for x in (0.0,w) for y in (0.0,d) for z in (0.0,h)]
        bores = [data['bore']]
    elif kind in BORED_TYPES:
        footprint = ccw(data['footprint'])
        roof = data['roof']
        bottom = [[x*factor,y*factor,0.0] for x,y in footprint]
        top = [[x*factor,y*factor,
                (roof['offset']+roof['slope_x']*x+roof['slope_y']*y)*factor]
               for x,y in footprint]
        body = sloped_body(bottom,top,roof)
        vertices = bottom+top
        bores = data.get('bores',[data['bore']] if 'bore' in data else [])
    else:
        raise ValueError('Tipo de modelo no admitido para Cota: '+str(kind))
    return 'SOLID3D', subtract_bores(body,vertices,bores,factor)


def document(data, projection='third', unit_mm=None):
    """Convert the source already validated by generar.renderers; do not modify it."""
    if projection not in ('first','third'):
        raise ValueError('Sistema de proyección no admitido para Cota.')
    units = data.get('units','u')
    factor = millimeters_per_unit(units,unit_mm)
    kind,props = entity(data,factor)
    source = json.dumps(data,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',',':'))
    version = (Path(__file__).resolve().parent.parent/'VERSION').read_text(encoding='utf-8').strip()
    result = {
        'schemaVersion':SCHEMA_VERSION, 'id':'doc', 'name':str(data.get('name','Pieza')),
        'units':'mm',
        'layers':[{'id':'0','name':'0','color':'#ffffff','lineWeight':0.25,
                   'lineType':'CONTINUOUS','locked':False,'visible':True,'printable':True}],
        'ucs':[{'id':'world','name':'World','origin':[0.0,0.0,0.0],
                'xAxis':[1.0,0.0,0.0],'yAxis':[0.0,1.0,0.0]}],
        'entities':[{'id':'e1','type':kind,'layer':'0','props':props}],
        'vars':{'VIEWPROJECTION':projection},
        'meta':{'custom':{
            'proyecciones_svg_version':version,
            'source_file':'modelo.json', 'source_type':data['type'], 'source_units':str(units),
            'millimeters_per_source_unit':repr(factor),
            'source_sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'compatibility':'Cota 1.0.0 / schema 1; one-way export',
            'curves':'Cota evaluates tessellated solids; the original SVG curves are preserved separately.',
        }},
    }
    # Fail before publishing any output if unit conversion overflowed.
    json.dumps(result,allow_nan=False)
    return result
