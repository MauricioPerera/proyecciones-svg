"""Two equal-radius intersecting bores: analytic conics and union-ray visibility.

Scope: convex footprint, one roof plane, four separate cap openings, and both
complete cylinder/cylinder intersection ellipses strictly inside the body.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import proyectar as p
import pieza_taladrada as single

TAU = 2*math.pi


def scaled(v, k):
    return tuple(x*k for x in v)


def add(a, b):
    return tuple(x+y for x, y in zip(a, b))


@dataclass
class Ellipse:
    center: tuple
    a: tuple
    b: tuple
    feature: str

    def point(self, t):
        return tuple(c+a*math.cos(t)+b*math.sin(t) for c, a, b in zip(self.center, self.a, self.b))


class CrossedBores:
    def __init__(self, data):
        if not isinstance(data, dict) or data.get('type') != 'crossed_bores':
            raise ValueError('Se esperaba type=crossed_bores.')
        bores = data.get('bores')
        if not isinstance(bores, list) or len(bores) != 2:
            raise ValueError('Se requieren exactamente dos taladros.')
        self.bores = [single.SlopedBore({**data, 'type':'sloped_prism_with_bore', 'bore':b}) for b in bores]
        one, two = self.bores
        if one.radius != two.radius:
            raise ValueError('Este constructor analítico requiere diámetros iguales.')
        self.body, self.span, self.center = one.body, one.span, one.center
        self.body.data = data
        self.ax, self.by = one.ax, one.by
        self.normalized = one.normalized
        alignment = p.dot(one.axis, two.axis)
        denominator = 1-alignment*alignment
        if denominator < 1e-8:
            raise ValueError('Los ejes deben cruzarse y no ser paralelos.')
        delta = p.sub(two.rim_centers[False], one.rim_centers[False])
        along_one = (p.dot(delta, one.axis)-alignment*p.dot(delta, two.axis))/denominator
        along_two = (alignment*p.dot(delta, one.axis)-p.dot(delta, two.axis))/denominator
        crossing = add(one.rim_centers[False], scaled(one.axis, along_one))
        other = add(two.rim_centers[False], scaled(two.axis, along_two))
        if math.dist(crossing, other) > self.span*1e-8:
            raise ValueError('Se admiten ejes que se intersecan, no ejes alabeados.')
        self.crossing = crossing
        self.caps = []
        for i, bore in enumerate(self.bores):
            self.caps.append({cap:Ellipse(bore.rim_centers[cap], bore.rim_u[cap], bore.rim_v[cap],
                ('top-' if cap else 'bottom-')+str(i)) for cap in (False, True)})
        self.seams = []
        # Equal-radius cylinder equations differ by
        # ((w1-w2).X)*((w1+w2).X)=0 about the common axis point.
        for i, normal in enumerate((p.sub(one.axis, two.axis), add(one.axis, two.axis))):
            denominator = p.dot(normal, one.axis)
            vectors = [scaled(p.sub(radial, scaled(one.axis, p.dot(normal, radial)/denominator)), one.radius)
                       for radial in (one.u, one.v)]
            curve = Ellipse(crossing, *vectors, 'intersection-'+str(i))
            for face, n in zip(self.body.faces, self.body.normals):
                distance = p.dot(n, p.sub(self.normalized(crossing), self.body.vertices[face[0]]))
                extent = math.hypot(p.dot(n, curve.a), p.dot(n, curve.b))/self.span
                if distance+extent >= -1e-7:
                    raise ValueError('El cruce completo debe quedar dentro del cuerpo; las cuatro bocas deben permanecer separadas.')
            self.seams.append(curve)
        self.curves = [cap[key] for cap in self.caps for key in (False, True)]+self.seams


def cylinder_interval(bore, origin, direction, tolerance=1e-12):
    # Solve in bore-radius units along a unit direction, then restore the ray
    # parameter. Tolerances depend on angles/ratios, never on the input units.
    magnitude = math.hypot(*direction)
    relative = tuple(v/bore.radius for v in p.sub(origin, bore.rim_centers[False]))
    radial = p.sub(relative, scaled(bore.axis, p.dot(relative, bore.axis)))
    unit_direction = scaled(direction, 1/magnitude) if magnitude else (0.0, 0.0, 0.0)
    speed = p.sub(unit_direction, scaled(bore.axis, p.dot(unit_direction, bore.axis)))
    a, b = p.dot(speed, speed), 2*p.dot(radial, speed)
    c = p.dot(radial, radial)-1
    if a <= tolerance:
        return (-math.inf, math.inf) if c <= tolerance else None
    discriminant = b*b-4*a*c
    if discriminant < -tolerance*max(1.0, b*b, abs(4*a*c)):
        return None
    root = math.sqrt(max(0.0, discriminant))
    factor = bore.radius/magnitude
    return (-b-root)/(2*a)*factor, (-b+root)/(2*a)*factor


def material_ahead(model, origin, direction):
    """Ray intersects material iff the two void intervals fail to cover the hull."""
    point = model.normalized(origin)
    lo, hi = model.span*1e-8, math.inf
    for face, normal in zip(model.body.faces, model.body.normals):
        distance = p.dot(normal, p.sub(point, model.body.vertices[face[0]]))*model.span
        speed = p.dot(normal, direction)
        if abs(speed) < 1e-12:
            if distance > model.span*1e-9:
                return False
        elif speed > 0:
            hi = min(hi, -distance/speed)
        else:
            lo = max(lo, -distance/speed)
        if hi-lo <= model.span*1e-9:
            return False
    intervals = sorted(interval for bore in model.bores if (interval := cylinder_interval(bore, origin, direction)) is not None)
    cursor = lo
    for start, end in intervals:
        if end < cursor:
            continue
        if start > cursor+model.span*1e-9:
            return True
        cursor = max(cursor, end)
        if cursor >= hi-model.span*1e-9:
            return False
    return True


def polynomial_roots(coefficients):
    """Isolate real roots using derivative intervals, up to degree eight."""
    scale = max(abs(v) for v in coefficients)
    if scale == 0:
        return []
    c = [v/scale for v in coefficients]
    while len(c)>1 and abs(c[-1])<1e-13:
        c.pop()
    if len(c)==1:
        return []
    if len(c)==2:
        return [-c[0]/c[1]]
    bound = 1+max(abs(v/c[-1]) for v in c[:-1])
    critical = polynomial_roots([i*c[i] for i in range(1,len(c))])
    points = [-bound]+[x for x in critical if -bound<x<bound]+[bound]
    def evaluate(x):
        total = 0
        for v in reversed(c):
            total = total*x+v
        return total
    roots = [x for x in points[1:-1] if abs(evaluate(x))<1e-10]
    for left,right in zip(points,points[1:]):
        fl,fr = evaluate(left),evaluate(right)
        if fl*fr>=0:
            continue
        for _ in range(64):
            middle=(left+right)/2
            fm=evaluate(middle)
            if fl*fm<=0:
                right=middle
            else:
                left,fl=middle,fm
        roots.append((left+right)/2)
    return sorted(roots)


def trig_roots(c0, c1=0, s1=0, c2=0, s2=0):
    """All roots of a second-order trigonometric polynomial, without sampling."""
    scale=max(abs(v) for v in (c0,c1,s1,c2,s2))
    if scale == 0:
        return []
    c0,c1,s1,c2,s2=(v/scale for v in (c0,c1,s1,c2,s2))
    def rotated(shift):
        return (c1*math.cos(shift)+s1*math.sin(shift), -c1*math.sin(shift)+s1*math.cos(shift),
                c2*math.cos(2*shift)+s2*math.sin(2*shift), -c2*math.sin(2*shift)+s2*math.cos(2*shift))
    # Keep the half-angle quartic's leading term away from zero/infinity.
    shift=max((0,.37,.91,1.57,2.2),key=lambda t:abs(c0-rotated(t)[0]+rotated(t)[2]))
    a,b,c,d=rotated(shift)
    roots=polynomial_roots([c0+a+c,2*b+4*d,2*c0-6*c,2*b-4*d,c0-a+c])
    return sorted((2*math.atan(x)+shift)%TAU for x in roots)


def projected(curve, model, azimuth, elevation, mapping):
    def point(world):
        return mapping(p.project([model.normalized(world)],azimuth,elevation)[0])
    center=point(curve.center)
    return Ellipse(center,p.sub(point(add(curve.center,curve.a)),center),
                   p.sub(point(add(curve.center,curve.b)),center),curve.feature)


def matrix(curve):
    return (curve.a[0],curve.a[1],curve.b[0],curve.b[1],*curve.center)


def conic_crossings(source, target):
    determinant=p.cross2(target.a,target.b)
    delta=p.sub(source.center,target.center)
    if abs(determinant) <= 1e-10*max(1e-10,math.hypot(*target.a)*math.hypot(*target.b)):
        tangent=max((target.a,target.b),key=lambda v:p.dot(v,v))
        n=(-tangent[1],tangent[0])
        return trig_roots(p.dot(n,delta),p.dot(n,source.a),p.dot(n,source.b))
    def inverse(v):
        return (p.cross2(v,target.b)/determinant,p.cross2(target.a,v)/determinant)
    c,a,b=map(inverse,(delta,source.a,source.b))
    return trig_roots(p.dot(c,c)-1+(p.dot(a,a)+p.dot(b,b))/2,
                     2*p.dot(c,a),2*p.dot(c,b),(p.dot(a,a)-p.dot(b,b))/2,p.dot(a,b))


def generator_lines(model, direction, azimuth, elevation, mapping):
    result=[]
    for i,bore in enumerate(model.bores):
        du,dv=p.dot(bore.u,direction),p.dot(bore.v,direction)
        if math.hypot(du,dv)<1e-9:
            continue
        phase=math.atan2(dv,du)
        for theta in (phase+math.pi/2,phase-math.pi/2):
            start,end=bore.rim(theta,False),bore.rim(theta,True)
            delta=p.sub(end,start)
            interval=cylinder_interval(model.bores[1-i],start,delta)
            pieces=[(0.0,1.0)]
            if interval is not None:
                left,right=max(0.0,interval[0]),min(1.0,interval[1])
                if right>left:
                    pieces=[(a,b) for a,b in ((0,left),(right,1)) if b-a>1e-9]
            endpoints=[mapping(p.project([model.normalized(world)],azimuth,elevation)[0]) for world in (start,end)]
            result.append((endpoints,[(add(start,scaled(delta,a)),add(start,scaled(delta,b))) for a,b in pieces]))
    return result


def visibility_intervals(curve, screen, all_screen, lines, model, direction):
    roots=[0.0,TAU]
    for target in all_screen:
        if target.feature != screen.feature:
            roots.extend(conic_crossings(screen,target))
    for (start,end),_ in lines:
        tangent=p.sub(end,start)
        normal=(-tangent[1],tangent[0])
        roots.extend(trig_roots(p.dot(normal,p.sub(screen.center,start)),p.dot(normal,screen.a),p.dot(normal,screen.b)))
    unique=[]
    for value in sorted(roots):
        if not unique or value-unique[-1]>1e-7:
            unique.append(value)
    if unique[-1]<TAU-1e-10:
        unique.append(TAU)
    result=[]
    for left,right in zip(unique,unique[1:]):
        if right-left<1e-8:
            continue
        visible=not material_ahead(model,curve.point((left+right)/2),direction)
        if result and result[-1][2]==visible:
            result[-1]=(result[-1][0],right,visible)
        else:
            result.append((left,right,visible))
    return result


def ellipse_covariance(curve):
    return (curve.a[0]**2+curve.b[0]**2,curve.a[0]*curve.a[1]+curve.b[0]*curve.b[1],curve.a[1]**2+curve.b[1]**2)


def overlap_projection_path(curves):
    """Exact convex hull of two concentric ellipses: ellipse arcs + bitangents.

    The intersection of the cylinders is the convex hull of its two seam
    ellipses: any smooth cylinder support is a generator with seam endpoints.
    Projection commutes with convex hull.
    """
    cov=[ellipse_covariance(curve) for curve in curves]
    xx,xy,yy=(cov[0][i]-cov[1][i] for i in range(3))
    roots=trig_roots((xx+yy)/2,0,0,(xx-yy)/2,xy)
    knots=[0.0]+[v for v in roots if 1e-8<v<TAU-1e-8]+[TAU]
    pieces=[]
    for left,right in zip(knots,knots[1:]):
        n=(math.cos((left+right)/2),math.sin((left+right)/2))
        winner=max(range(2),key=lambda i:cov[i][0]*n[0]**2+2*cov[i][1]*n[0]*n[1]+cov[i][2]*n[1]**2)
        if pieces and pieces[-1][2]==winner:
            pieces[-1]=(pieces[-1][0],right,winner)
        else:
            pieces.append((left,right,winner))
    commands=[]
    for left,right,winner in pieces:
        xx,xy,yy=cov[winner]
        angle=.5*math.atan2(2*xy,xx-yy)
        delta=math.hypot(xx-yy,2*xy)
        rx=math.sqrt(max(0,(xx+yy+delta)/2))
        ry=math.sqrt(max(0,(xx+yy-delta)/2))
        a=(rx*math.cos(angle),rx*math.sin(angle))
        b=(-ry*math.sin(angle),ry*math.cos(angle))
        def support(phi):
            n=(math.cos(phi),math.sin(phi))
            phase=math.atan2(p.dot(n,b),p.dot(n,a))
            point=add(curves[0].center,add(scaled(a,math.cos(phase)),scaled(b,math.sin(phase))))
            return phase,point
        t0,start=support(left)
        t1,end=support(right)
        commands.append(('M' if not commands else 'L')+p.fmt(start[0])+','+p.fmt(start[1]))
        sweep=(t1-t0)%TAU if right-left<TAU-1e-8 else TAU
        if sweep>TAU-1e-8:
            middle=add(curves[0].center,add(scaled(a,-math.cos(t0)),scaled(b,-math.sin(t0))))
            commands.append(f'A{p.fmt(rx)},{p.fmt(ry)} {p.fmt(math.degrees(angle))} 0 1 {p.fmt(middle[0])},{p.fmt(middle[1])}')
            sweep=math.pi
        if math.dist(start,end)>1e-7 or right-left>TAU-1e-8:
            commands.append(f'A{p.fmt(rx)},{p.fmt(ry)} {p.fmt(math.degrees(angle))} {int(sweep>math.pi)} 1 {p.fmt(end[0])},{p.fmt(end[1])}')
    return ' '.join(commands)+' Z'


def decorate(parent,model,azimuth,elevation,mapping,hidden,prefix):
    strokes=[node for node in parent if node.get('class') in ('edge','hidden-edge')]
    for node in strokes:
        parent.remove(node)
    surface=p.svg_el(parent,'g',data_layer='bore-surface')
    concealed=p.svg_el(parent,'g',data_layer='bore-hidden')
    visible=p.svg_el(parent,'g',data_layer='bore-visible')
    direction=p.camera(azimuth,elevation)[2]
    screen=[projected(c,model,azimuth,elevation,mapping) for c in model.curves]
    by_name={c.feature:c for c in screen}
    if single.roof_facing(model,azimuth,elevation)>p.EPS:
        defs=p.svg_el(surface,'defs')
        overlap=p.svg_el(defs,'clipPath',id=prefix+'-overlap',clipPathUnits='userSpaceOnUse')
        p.svg_el(overlap,'path',d=overlap_projection_path(screen[-2:]),data_feature='overlap-projection')
        for i in range(2):
            top=by_name['top-'+str(i)]
            transform=single.matrix_text(matrix(top))
            clip=p.svg_el(defs,'clipPath',id=prefix+'-opening-'+str(i),clipPathUnits='userSpaceOnUse')
            p.svg_el(clip,'circle',cx=0,cy=0,r=1,transform=transform)
            p.svg_el(surface,'circle',cx=0,cy=0,r=1,transform=transform,class_='bore-wall')
            if elevation>1e-8:
                aperture=p.svg_el(surface,'g',clip_path=f'url(#{prefix}-opening-{i})')
                for j in range(2):
                    parent_clip=aperture if i==j else p.svg_el(aperture,'g',clip_path=f'url(#{prefix}-overlap)')
                    p.svg_el(parent_clip,'circle',cx=0,cy=0,r=1,
                        transform=single.matrix_text(matrix(by_name['bottom-'+str(j)])),class_='face',data_feature='through-aperture')
    lines=generator_lines(model,direction,azimuth,elevation,mapping)
    for curve,flat in zip(model.curves,screen):
        if curve.feature.startswith('bottom') and elevation<1e-8:
            continue  # Its projection coincides with the exterior base outline.
        intervals=visibility_intervals(curve,flat,screen,lines,model,direction)
        for start,end,is_visible in intervals:
            if not is_visible and hidden=='omit':
                continue
            attrs={'transform':single.matrix_text(matrix(flat)),
                   'class_':('edge' if is_visible else 'hidden-edge')+' curve',
                   'data_curve':curve.feature,'data_start':p.fmt(start),'data_end':p.fmt(end)}
            target=visible if is_visible else concealed
            if end-start>TAU-1e-7:
                p.svg_el(target,'circle',cx=0,cy=0,r=1,**attrs)
            else:
                p.svg_el(target,'path',d=single.unit_arc(start,end),**attrs)
    if hidden=='dash':
        for _,pieces in lines:
            for start,end in pieces:
                points=[mapping(p.project([model.normalized(world)],azimuth,elevation)[0]) for world in (start,end)]
                p.svg_el(concealed,'path',d=p.path_data(points),class_='hidden-edge',data_feature='bore-generator')
    for node in strokes:
        (concealed if node.get('class')=='hidden-edge' else visible).insert(0,node)


def sheet(model,system,hidden,decorator=decorate):
    root=p.sheet_svg(model.body,system,hidden)
    single.add_style(root)
    for group in root.findall(f'{{{p.NS}}}g'):
        name=group.get('data-view')
        if name is None:
            continue
        azimuth,elevation={'Alzado':(0,0),'Planta':(0,90),'Perfil derecho':(90,0)}[name]
        heading=group.find(f'{{{p.NS}}}text')
        scale=float(group.get('data-scale'))
        width=model.body.size[1] if name=='Perfil derecho' else model.body.size[0]
        left=float(heading.get('x'))-width/model.span*scale/2
        top=float(heading.get('y'))+20
        vertices=p.project(model.body.vertices,azimuth,elevation)
        min_x,max_y=min(v[0] for v in vertices),max(v[1] for v in vertices)
        mapping=lambda v:(left+(v[0]-min_x)*scale,top+(max_y-v[1])*scale)
        decorator(group,model,azimuth,elevation,mapping,hidden,'sheet-'+name.replace(' ','-'))
        for i,bore in enumerate(model.bores):
            points=[mapping(p.project([model.normalized(bore.rim_centers[cap])],azimuth,elevation)[0]) for cap in (False,True)]
            p.svg_el(group,'path',d=p.path_data(points),class_='axis',data_feature='bore-axis')
            if name=='Planta':
                theta=math.pi/4 if i==0 else 3*math.pi/4 if i==1 else math.pi/2 if i==2 else 3*math.pi/2
                start=mapping(p.project([model.normalized(bore.rim(theta))],azimuth,elevation)[0])
                offset=15 if i==0 else -15 if i==1 else 0
                end=(start[0]+offset,start[1]+(18 if i==3 else -15))
                p.svg_el(group,'path',d=p.path_data([start,end]),class_='dimension')
                anchor='start' if i==0 else 'end' if i==1 else 'middle'
                p.label(group,end[0]+(5 if i==0 else -5 if i==1 else 0),end[1]+(12 if i==3 else -3),chr(65+i)+' Ø '+p.fmt_measurement(bore.radius*2),anchor)
    return root


def view(model,args,decorator=decorate):
    root=p.view_svg(model.body,args.azimuth,args.elevation,args.hidden)
    single.add_style(root)
    decorator(root.find(f'{{{p.NS}}}g'),model,args.azimuth,args.elevation,p.angle_mapping(model.body),args.hidden,'view')
    return root


def animation(model,args,decorator=decorate):
    root=p.animation_svg(model.body,args)
    single.add_style(root)
    for group in root.iter(f'{{{p.NS}}}g'):
        if group.get('data-frame') is not None:
            index=int(group.get('data-frame'))
            azimuth=args.azimuth+args.sweep*index/(args.frames if args.loop else args.frames-1)
            decorator(group,model,azimuth,args.elevation,p.angle_mapping(model.body),args.hidden,'frame-'+str(index))
        elif group.get('class')=='still-frame':
            decorator(group,model,args.azimuth,args.elevation,p.angle_mapping(model.body),args.hidden,'still')
    return root


def main(argv=None,constructor=CrossedBores,decorator=decorate):
    parser=argparse.ArgumentParser(description=constructor.__doc__ or __doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--mode',choices=('sheet','view','animation','all'),default='all')
    parser.add_argument('--system',choices=('third','first'),default='third')
    parser.add_argument('--hidden',choices=('dash','omit'),default='dash')
    parser.add_argument('--azimuth',type=float,default=45)
    parser.add_argument('--elevation',type=float,default=50)
    parser.add_argument('--frames',type=int,default=120)
    parser.add_argument('--seconds',type=float,default=10)
    parser.add_argument('--sweep',type=float,default=360)
    parser.add_argument('--loop',action='store_true')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args(argv)
    if not all(math.isfinite(v) for v in (args.azimuth,args.elevation,args.seconds,args.sweep)) or not 0<=args.elevation<=90 or args.seconds<=0 or not 8<=args.frames<=240:
        parser.error('Se requiere elevación 0..90°, duración positiva y 8..240 fotogramas.')
    try:
        model=constructor(json.loads(args.model.read_text(encoding='utf-8-sig')))
        jobs=[]
        if args.mode in ('sheet','all'):
            jobs.append(('vistas.svg',lambda:sheet(model,args.system,args.hidden,decorator)))
        if args.mode in ('view','all'):
            jobs.append(('angulo.svg',lambda:view(model,args,decorator)))
        if args.mode in ('animation','all'):
            jobs.append(('giro.svg',lambda:animation(model,args,decorator)))
        if not args.force and any((args.output_dir/name).exists() for name,_ in jobs):
            raise ValueError('Ya existen salidas; usa otra carpeta o --force.')
        documents=[(name,create()) for name,create in jobs]
        args.output_dir.mkdir(parents=True,exist_ok=True)
        for name,root in documents:
            path=args.output_dir/name
            ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
            print(path.resolve())
    except (OSError,ValueError,TypeError,AttributeError,KeyError,OverflowError) as error:
        parser.exit(2,f'Error: {error}\n')
    return 0


if __name__=='__main__':
    sys.exit(main())
