"""Analytic plane sections of convex bodies and unions of cylindrical voids."""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET

import proyectar as p

COLORS = ('#b64d13', '#007a99', '#7544b3', '#23783e')
TOL = 1e-12  # Dimensionless: calculations use the same normalized body as SVG views.


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x*k for x in a)


def unit(a):
    scale = max(abs(v) for v in a)
    if scale == 0 or not math.isfinite(scale):
        raise ValueError('El vector del plano de corte no puede ser nulo.')
    local = tuple(v/scale for v in a)
    length = math.hypot(*local)
    return tuple(v/length for v in local)


def xml_text(value):
    return all(ord(c) in (9, 10, 13) or 0x20 <= ord(c) <= 0xd7ff
               or 0xe000 <= ord(c) <= 0xfffd or 0x10000 <= ord(c) <= 0x10ffff for c in value)


def screen_fmt(value):
    # Keep thin, accepted sections non-degenerate after writing screen coordinates.
    return format(value, '.12f').rstrip('0').rstrip('.') or '0'


class SectionBody:
    """Adapt an already validated projection model; never rebuild its solid."""
    def __init__(self, model):
        self.body = getattr(model, 'box', getattr(model, 'body', model))
        self.data = self.body.data
        self.span = self.body.span
        self.center = tuple(a+(b-a)/2 for a, b in zip(self.body.minimum, self.body.maximum))
        self.planes = []
        volume = math.fsum(p.dot(self.body.vertices[a], p.cross(self.body.vertices[b], self.body.vertices[c]))
                           for a, b, c in self.body.triangles)
        sign = 1 if volume > 0 else -1
        for face, normal in zip(self.body.faces, self.body.normals):
            normal = mul(normal, sign)
            anchor = self.body.vertices[face[0]]
            if any(p.dot(normal, p.sub(v, anchor)) > TOL*100 for v in self.body.vertices):
                raise ValueError('--sections admite cuerpos convexos; este cuerpo es cóncavo.')
            self.planes.append((normal, p.dot(normal, anchor)))
        self.bores = []
        if hasattr(model, 'bores'):
            bores = model.bores
        elif hasattr(model, 'radius'):
            bores = [model]
        else:
            bores = []
        for bore in bores:
            base = bore.rim_centers[False] if hasattr(bore, 'rim_centers') else (bore.cx, bore.cy, 0.)
            axis = getattr(bore, 'axis', (0., 0., 1.))
            self.bores.append((self.normalize(base), axis, bore.radius/self.span))
        self.focus = (0., 0., 0.)
        if hasattr(model, 'crossing'):
            self.focus = self.normalize(model.crossing)
        elif bores:
            bore = bores[0]
            if hasattr(bore, 'rim_centers'):
                self.focus = self.normalize(mul(add(bore.rim_centers[False], bore.rim_centers[True]), .5))
            else:
                self.focus = self.normalize((bore.cx, bore.cy, bore.height/2))

    def normalize(self, point):
        return tuple((a-b)/self.span for a, b in zip(point, self.center))

    def world(self, point):
        return add(self.center, mul(point, self.span))

    def sections(self):
        specs = self.data.get('sections')
        if 'sections' in self.data:
            if not isinstance(specs, list) or not 1 <= len(specs) <= 4:
                raise ValueError('sections debe ser una lista de uno a cuatro planos.')
            result = []
            for i, spec in enumerate(specs):
                if not isinstance(spec, dict):
                    raise ValueError('Cada plano sections debe ser un objeto.')
                name = spec.get('name', f'Corte {i+1}')
                if not isinstance(name, str) or not name.strip() or len(name) > 80:
                    raise ValueError('El nombre de cada corte debe tener 1..80 caracteres.')
                if not xml_text(name):
                    raise ValueError('El nombre del corte contiene caracteres no admitidos por XML.')
                origin = p.point(spec.get('origin'), 3)
                result.append(Section(self, name, self.normalize(origin), p.point(spec.get('normal'), 3),
                                      p.point(spec['up'], 3) if 'up' in spec else None, world_origin=origin))
            return result
        normals = [(0., -1., 0.), (1., 0., 0.)]
        names = ['A–A', 'B–B']
        if len(self.bores) >= 2:
            normals[0] = p.cross(self.bores[0][1], self.bores[1][1])
            names[0] += ' · ejes A y B'
            if len(self.bores) >= 3:
                i, j = (2, 3) if len(self.bores) == 4 else (1, 2)
                normals[1] = p.cross(self.bores[i][1], self.bores[j][1])
                names[1] += f' · ejes {"ABCD"[i]} y {"ABCD"[j]}'
            else:
                normals[1] = p.cross(normals[0], self.bores[0][1])
        elif self.bores:
            axis = self.bores[0][1]
            hint = (1., 0., 0.) if abs(axis[0]) < .9 else (0., 1., 0.)
            normals = [p.cross(axis, hint), p.cross(axis, p.cross(axis, hint))]
        return [Section(self, name, self.focus, normal) for name, normal in zip(names, normals)]


class Section:
    def __init__(self, body, name, origin, normal, up=None, world_origin=None):
        self.body, self.name, self.origin = body, name, origin
        self.n = unit(normal)
        # A point far along the plane must not move calculations far from the body.
        # Preserve the declared origin for metadata; use its normal projection locally.
        self.world_origin = body.world(origin) if world_origin is None else world_origin
        if world_origin is None:
            constant = math.fsum(v*n for v,n in zip(origin,self.n))
        else:
            # Sum world-coordinate products before subtracting the body center.
            # Componentwise normalization first loses the plane offset at large
            # tangential origins (e.g. x=y=1e16 with normal [1,-1,0]).
            constant = math.fsum([v*n for v,n in zip(world_origin,self.n)]
                                 +[-v*n for v,n in zip(body.center,self.n)])/body.span
        self.anchor = mul(self.n, constant)
        automatic_up = up is None
        up = unit((0., 0., 1.) if automatic_up else up)
        right = p.cross(up, self.n)
        if math.hypot(*right) < 1e-8:
            if not automatic_up:
                raise ValueError('El vector up no puede ser paralelo a la normal del corte.')
            right = p.cross((0., 1., 0.), self.n)
        self.u = unit(right)
        self.v = unit(p.cross(self.n, self.u))
        self.polygon = self.clip_body()
        self.shapes = [self.bore_shape(bore) for bore in body.bores]

    def project(self, point):
        q = p.sub(point, self.anchor)
        return p.dot(q, self.u), p.dot(q, self.v)

    def point(self, q):
        return add(self.anchor, add(mul(self.u, q[0]), mul(self.v, q[1])))

    def clip_body(self):
        projected = [self.project(v) for v in self.body.body.vertices]
        low = [min(q[i] for q in projected)-1 for i in (0, 1)]
        high = [max(q[i] for q in projected)+1 for i in (0, 1)]
        polygon = [(low[0], low[1]), (high[0], low[1]), (high[0], high[1]), (low[0], high[1])]
        for normal, constant in self.body.planes:
            a, b, c = p.dot(normal, self.u), p.dot(normal, self.v), p.dot(normal, self.anchor)-constant
            result = []
            for start, end in zip(polygon, polygon[1:]+polygon[:1]):
                first, last = a*start[0]+b*start[1]+c, a*end[0]+b*end[1]+c
                if abs(first) <= TOL:
                    first = 0.
                if abs(last) <= TOL:
                    last = 0.
                if first <= 0:
                    result.append(start)
                if (first > 0) != (last > 0):
                    result.append(add(start, mul(p.sub(end, start), first/(first-last))))
            polygon = []
            for q in result:
                if not polygon or math.dist(q, polygon[-1]) > TOL:
                    polygon.append(q)
            if len(polygon) > 1 and math.dist(polygon[0], polygon[-1]) <= TOL:
                polygon.pop()
        if len(polygon) < 3 or abs(p.signed_area(polygon)) <= TOL*TOL:
            raise ValueError('El plano de corte no atraviesa un área del cuerpo.')
        # A coincident exterior face is a view of a face, not an interior section.
        distances = [p.dot(self.n, p.sub(v, self.anchor)) for v in self.body.body.vertices]
        if min(distances) >= -TOL or max(distances) <= TOL:
            raise ValueError('El plano debe atravesar el interior del cuerpo, no sólo tocarlo.')
        return polygon

    def bore_shape(self, bore):
        base, axis, radius = bore
        cosine = p.dot(self.n, axis)
        if abs(cosine) <= 5e-15:
            distance = p.dot(self.n, p.sub(base, self.anchor))
            if abs(distance) >= radius:
                return None  # Parallel plane misses or merely touches this cylinder.
            direction = unit((p.dot(axis, self.u), p.dot(axis, self.v)))
            return {'kind':'strip', 'center':self.project(base), 'direction':direction,
                    'normal':(-direction[1], direction[0]), 'halfwidth':math.sqrt((radius-distance)*(radius+distance))}
        if abs(cosine) < 1e-7:
            raise ValueError('Plano casi paralelo a un taladro: cambia su normal para evitar una elipse mal condicionada.')
        center = add(base, mul(axis, p.dot(self.n, p.sub(self.anchor, base))/cosine))
        projection = (p.dot(axis, self.u), p.dot(axis, self.v))
        major = unit(projection) if math.hypot(*projection) > TOL else (1., 0.)
        return {'kind':'ellipse', 'center':self.project(center), 'major':major,
                'minor':(-major[1], major[0]), 'a':radius/abs(cosine), 'b':radius}


def contains(shape, point):
    if shape is None:
        return False
    q = p.sub(point, shape['center'])
    if shape['kind'] == 'strip':
        return abs(p.dot(q, shape['normal'])) < shape['halfwidth']
    return (p.dot(q, shape['major'])/shape['a'])**2+(p.dot(q, shape['minor'])/shape['b'])**2 < 1


def shape_svg(parent, shape, mapping, scale, **attrs):
    if shape is None:
        return
    f = lambda v: format(v, '.12g')
    if shape['kind'] == 'ellipse':
        center = mapping(shape['center'])
        a, b = mul(shape['major'], shape['a']*scale), mul(shape['minor'], shape['b']*scale)
        matrix = (a[0], -a[1], b[0], -b[1], *center)
        return p.svg_el(parent, 'ellipse', rx=1, ry=1, transform='matrix('+ ' '.join(map(f, matrix))+')',
                        vector_effect='non-scaling-stroke', **attrs)
    # A strip is infinite. Extend it past all corners of the actual panel,
    # including when its reference axis is far from the section origin.
    corners = getattr(mapping, 'corners')
    c, d = shape['center'], shape['direction']
    ts = [p.dot(p.sub(q, c), d) for q in corners]
    lo, hi = min(ts)-1, max(ts)+1
    normal = mul(shape['normal'], shape['halfwidth'])
    points = [mapping(add(c, add(mul(d, t), mul(normal, side)))) for t, side in ((lo,-1),(hi,-1),(hi,1),(lo,1))]
    return p.svg_el(parent, 'polygon', points=' '.join(f(x)+','+f(y) for x, y in points),
                    vector_effect='non-scaling-stroke', **attrs)


def text(parent, x, y, content, kind='small', **attrs):
    p.svg_el(parent, 'text', x=p.fmt(x), y=p.fmt(y), class_='section-'+kind, **attrs).text = content


def render_panel(root, defs, section, index, height):
    x, y, width, panel_height = 24+(index%2)*608, 152+(index//2)*380, 584, 364
    bounds = [(min(q[i] for q in section.polygon), max(q[i] for q in section.polygon)) for i in (0, 1)]
    scale = min((width-100)/(bounds[0][1]-bounds[0][0]), (panel_height-142)/(bounds[1][1]-bounds[1][0]))
    midpoint = tuple((a+b)/2 for a, b in bounds)
    def mapping(q):
        return (x+width/2+12+(q[0]-midpoint[0])*scale, y+panel_height/2+15-(q[1]-midpoint[1])*scale)
    mapping.corners = [(bounds[0][i], bounds[1][j]) for i in (0, 1) for j in (0, 1)]
    points = ' '.join(screen_fmt(a)+','+screen_fmt(b) for a, b in map(mapping, section.polygon))
    key = 'section-'+str(index)
    clip = p.svg_el(defs, 'clipPath', id=key+'-body')
    p.svg_el(clip, 'polygon', points=points)
    def mask(identifier, excluded):
        m = p.svg_el(defs, 'mask', id=identifier, maskUnits='userSpaceOnUse', x=0, y=0, width=1240, height=height)
        p.svg_el(m, 'rect', x=0, y=0, width=1240, height=height, fill='white')
        for i in excluded:
            shape_svg(m, section.shapes[i], mapping, scale, fill='black')
    mask(key+'-material', range(len(section.shapes)))
    for i in range(len(section.shapes)):
        mask(key+'-other-'+str(i), [j for j in range(len(section.shapes)) if j != i])
    panel = p.svg_el(root, 'g', data_section=index)
    p.svg_el(panel, 'rect', x=x, y=y, width=width, height=panel_height, rx=10, fill='white', stroke='#c7d3df')
    text(panel, x+18, y+29, section.name, 'heading')
    origin = ', '.join(p.fmt_measurement(v) for v in section.world_origin)
    text(panel, x+18, y+53, f'Origen ({origin}) {section.body.data.get("units", "u")}', 'origin')
    drawing = p.svg_el(panel, 'g', clip_path=f'url(#{key}-body)')
    material = p.svg_el(drawing, 'g', mask=f'url(#{key}-material)')
    p.svg_el(material, 'polygon', points=points, fill='#e8eef4')
    p.svg_el(material, 'polygon', points=points, fill='url(#section-hatch)', stroke='#30445b', stroke_width=2)
    for i, shape in enumerate(section.shapes):
        edge = p.svg_el(drawing, 'g', mask=f'url(#{key}-other-{i})')
        shape_svg(edge, shape, mapping, scale, fill='none', stroke=COLORS[i], stroke_width=2,
                  data_bore=i, data_boundary='material')
    guides = p.svg_el(drawing, 'g', class_='section-guides')
    for i, shape in enumerate(section.shapes):
        shape_svg(guides, shape, mapping, scale, fill='none', stroke=COLORS[i], stroke_width=1.2,
                  stroke_dasharray='6 5', data_bore=i, data_boundary='auxiliary')
    # True lengths in the orthonormal section basis, not projected silhouettes.
    for axis in (0, 1):
        value = (bounds[axis][1]-bounds[axis][0])*section.body.span
        label = p.fmt_measurement(value)
        if axis == 0:
            left = mapping((bounds[0][0], bounds[1][0]))
            right = mapping((bounds[0][1], bounds[1][0]))
            ydim = left[1]+20
            p.svg_el(panel, 'path', d=f'M{p.fmt(left[0])},{p.fmt(ydim)}H{p.fmt(right[0])}', stroke='#718096')
            for xx in (left[0], right[0]):
                p.svg_el(panel, 'path', d=f'M{p.fmt(xx)},{p.fmt(ydim-3)}v6', stroke='#718096')
            text(panel, (left[0]+right[0])/2, ydim+19, label, 'dimension', text_anchor='middle', data_value=label, data_axis='u')
        else:
            left, top = mapping((bounds[0][0], bounds[1][1]))
            _, bottom = mapping((bounds[0][0], bounds[1][0]))
            xdim = left-20
            p.svg_el(panel, 'path', d=f'M{p.fmt(xdim)},{p.fmt(top)}V{p.fmt(bottom)}', stroke='#718096')
            for yy in (top, bottom):
                p.svg_el(panel, 'path', d=f'M{p.fmt(xdim-3)},{p.fmt(yy)}h6', stroke='#718096')
            tx, ty = xdim-8, (top+bottom)/2
            text(panel, tx, ty, label, 'dimension', text_anchor='middle', data_value=label, data_axis='v',
                 transform=f'rotate(-90 {p.fmt(tx)} {p.fmt(ty)})')


def section_svg(body, sections):
    height = 152+380*math.ceil(len(sections)/2)+80
    root = ET.Element(f'{{{p.NS}}}svg', {'viewBox':f'0 0 1240 {height}', 'width':'1240', 'height':str(height),
                                      'class':'section-svg', 'role':'img', 'aria-labelledby':'sections-title sections-desc'})
    p.svg_el(root, 'title', id='sections-title').text = str(body.data.get('name', 'Pieza'))+' · cortes'
    p.svg_el(root, 'desc', id='sections-desc').text = 'Secciones planas reales: material rayado y unión de vaciados en blanco. Los bordes enterrados en otro vaciado se omiten.'
    p.svg_el(root, 'metadata').text = json.dumps({'method':'analytic plane/cylinder sections; convex half-spaces; union masks',
        'units':body.data.get('units', 'u'), 'source':body.data, 'planes':[
            {'name':s.name, 'origin':s.world_origin, 'normal':s.n, 'horizontal':s.u, 'vertical':s.v} for s in sections]}, ensure_ascii=False, allow_nan=False)
    p.svg_el(root, 'style').text = '''.section-svg text{font-family:system-ui,sans-serif;fill:#1b3048}.section-svg .section-title{font-size:25px;font-weight:700}.section-svg .section-heading{font-size:20px;font-weight:650}.section-svg .section-small,.section-svg .section-origin{font-size:15px}.section-svg .section-dimension{font-size:14px}.section-svg .section-guides{display:none}'''
    defs = p.svg_el(root, 'defs')
    pattern = p.svg_el(defs, 'pattern', id='section-hatch', width=9, height=9, patternUnits='userSpaceOnUse')
    p.svg_el(pattern, 'path', d='M-2,2L2,-2M0,9L9,0M7,11L11,7', stroke='#93a5b8', stroke_width=.8)
    p.svg_el(root, 'rect', width='100%', height='100%', fill='#f5f8fb')
    text(root, 24, 38, 'Cortes por el interior de la pieza', 'title')
    units = str(body.data.get('units', 'u'))
    text(root, 24, 70, f'Longitudes reales en el plano del corte · cotas y diámetros en {units}')
    for i, (_, _, radius) in enumerate(body.bores):
        value = p.fmt_measurement(2*radius*body.span)
        p.svg_el(root, 'circle', cx=33+i*240, cy=113, r=6, fill=COLORS[i])
        text(root, 49+i*240, 118, f'{"ABCD"[i]} · Ø {value} {units}', data_diameter=value)
    for i, section in enumerate(sections):
        render_panel(root, defs, section, i, height)
    text(root, 28, height-45, 'Rayado = material · blanco = vaciado común · color = borde real de un taladro')
    text(root, 28, height-20, 'Las guías auxiliares se activan en el visor; no representan aristas. Cotas generales, sin tolerancias de fabricación.')
    return root


def prepare(model):
    body = SectionBody(model)
    sections = body.sections()
    return body, sections
