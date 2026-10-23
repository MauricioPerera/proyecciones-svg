"""Shared three/four-bore union visibility and buried-curve trimming."""
from __future__ import annotations

import copy
import itertools
import math
import sys

import proyectar as p
import pieza_taladrada as single
import taladros_cruzados as base
import taladros_desiguales as unequal

TAU=2*math.pi


def poly_add(a,b):
    return [(a[i] if i<len(a) else 0)+(b[i] if i<len(b) else 0) for i in range(max(len(a),len(b)))]


def poly_scale(a,k):
    return [v*k for v in a]


def poly_mul(a,b):
    result=[0.0]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            result[i+j]+=x*y
    return result


def quadratic_roots(curve,map_point,map_vector,radius):
    """Quadratic locus on an ellipse or radical seam; degree <= 8 after squaring.

    All distances are measured in target-radius units and the seam radical in
    its large-radius units. Filter squared roots against the unsquared equation.
    """
    def value(t):
        v=tuple(x/radius for x in map_point(curve.point(t)))
        return p.dot(v,v)-1
    def equation(shift):
        c=tuple(x/radius for x in map_point(curve.center))
        a=tuple(x/radius for x in map_vector(base.add(base.scaled(curve.a,math.cos(shift)),base.scaled(curve.b,math.sin(shift)))))
        b=tuple(x/radius for x in map_vector(base.add(base.scaled(curve.a,-math.sin(shift)),base.scaled(curve.b,math.cos(shift)))))
        denominator=[1.0,0.0,1.0]
        cosine=[1.0,0.0,-1.0]
        sine=[0.0,2.0]
        h=[poly_add(poly_add(poly_scale(denominator,c[i]),poly_scale(cosine,a[i])),poly_scale(sine,b[i])) for i in range(len(c))]
        low=poly_scale(poly_mul(denominator,denominator),-1)
        for component in h:
            low=poly_add(low,poly_mul(component,component))
        if not isinstance(curve,unequal.Seam):
            return low
        d=tuple(x*curve.R/radius for x in map_vector(curve.d))
        original_sine=poly_add(poly_scale(cosine,math.sin(shift)),poly_scale(sine,math.cos(shift)))
        radicand=poly_add(poly_mul(denominator,denominator),poly_scale(poly_mul(original_sine,original_sine),-(curve.r/curve.R)**2))
        low=poly_add(low,poly_scale(radicand,p.dot(d,d)))
        mixed=[0.0]
        for component,coefficient in zip(h,d):
            mixed=poly_add(mixed,poly_scale(component,2*coefficient))
        if max(abs(v) for v in mixed)<1e-13:
            return low
        return poly_add(poly_mul(low,low),poly_scale(poly_mul(poly_mul(mixed,mixed),radicand),-1))
    candidates=[(shift,equation(shift)) for shift in (0,.37,.91,1.57,2.2)]
    shift,coefficients=max(candidates,key=lambda pair:abs(pair[1][-1])/max(1e-30,max(abs(v) for v in pair[1])))
    roots=[(2*math.atan(v)+shift)%TAU for v in base.polynomial_roots(coefficients)]
    roots.append((math.pi+shift)%TAU)
    scale=max(1,max(abs(value(t)) for t in (0,.7,1.9,3.2,4.7)))
    return sorted(t for t in roots if abs(value(t))<=scale*2e-7)


def cylinder_roots(curve,bore):
    def radial(v):
        return p.sub(v,base.scaled(bore.axis,p.dot(v,bore.axis)))
    return quadratic_roots(curve,lambda point:radial(p.sub(point,bore.rim_centers[False])),radial,bore.radius)


def inside_bore(point,bore,tolerance=1e-10):
    """Strict interior with a dimensionless tolerance on squared radial ratio."""
    relative=tuple(x/bore.radius for x in p.sub(point,bore.rim_centers[False]))
    radial=p.sub(relative,base.scaled(bore.axis,p.dot(relative,bore.axis)))
    return p.dot(radial,radial)<1-tolerance


class ThreeBores:
    """Tres taladros de diámetros distintos con ejes concurrentes y seis bocas separadas."""
    type_name='triple_crossed_bores'
    count=3

    def __init__(self,data):
        if not isinstance(data,dict) or data.get('type')!=self.type_name:
            raise ValueError('Se esperaba type='+self.type_name+'.')
        bores=data.get('bores')
        if not isinstance(bores,list) or len(bores)!=self.count:
            raise ValueError(f'Se requieren exactamente {self.count} taladros.')
        self.bores=[single.SlopedBore({**data,'type':'sloped_prism_with_bore','bore':b}) for b in bores]
        one=self.bores[0]
        self.body,self.span,self.center=one.body,one.span,one.center
        self.body.data=data
        self.ax,self.by=one.ax,one.by
        self.normalized=one.normalized
        self.pairs={}
        self.seams=[]
        self.crossing=None
        for i,j in itertools.combinations(range(self.count),2):
            pair=unequal.UnequalBores({**data,'type':'unequal_crossed_bores','bores':[bores[i],bores[j]]})
            if self.crossing is None:
                self.crossing=pair.crossing
            elif math.dist(pair.crossing,self.crossing)>self.span*1e-8:
                raise ValueError('Todos los ejes deben pasar por un mismo punto interior.')
            self.pairs[i,j]=pair
            for branch,curve in enumerate(pair.seams):
                curve.feature=f'intersection-{i}-{j}-{branch}'
                curve.pair=(i,j)
                curve.others=tuple(k for k in range(self.count) if k not in (i,j))
                if self.count==3:
                    curve.third=curve.others[0]
                curve.burial_roots=[t for k in curve.others for t in cylinder_roots(curve,self.bores[k])]
                self.seams.append(curve)
        self.caps=[{cap:base.Ellipse(b.rim_centers[cap],b.rim_u[cap],b.rim_v[cap],('top-' if cap else 'bottom-')+str(i))
                    for cap in (False,True)} for i,b in enumerate(self.bores)]
        self.curves=[cap[key] for cap in self.caps for key in (False,True)]+self.seams


def screen_curve(curve,model,azimuth,elevation,mapping):
    if not isinstance(curve,unequal.Seam):
        return base.projected(curve,model,azimuth,elevation,mapping)
    result=copy.copy(curve)
    result.center=unequal.project_point(curve.center,model,azimuth,elevation,mapping)
    for name in ('a','b','d'):
        setattr(result,name,unequal.screen_derivative(getattr(curve,name),model,azimuth,elevation,mapping))
    return result


def line_roots(curve,normal,constant):
    if isinstance(curve,unequal.Seam):
        # A conservative range discards lines that cannot meet the curve.
        k=p.dot(normal,curve.center)+constant
        a,b,d=(p.dot(normal,v) for v in (curve.a,curve.b,curve.d))
        low_q=math.sqrt(curve.R**2-curve.r**2)
        low=k-math.hypot(a,b)+min(d*low_q,d*curve.R)
        high=k+math.hypot(a,b)+max(d*low_q,d*curve.R)
        if low>1e-9 or high< -1e-9:
            return []
        return curve.linear_roots(normal,constant)
    return base.trig_roots(p.dot(normal,curve.center)+constant,p.dot(normal,curve.a),p.dot(normal,curve.b))


def ellipse_roots(source,target):
    determinant=p.cross2(target.a,target.b)
    if abs(determinant)<1e-10:
        tangent=max((target.a,target.b),key=lambda v:p.dot(v,v))
        return line_roots(source,(-tangent[1],tangent[0]),-p.cross2(tangent,target.center))
    def inverse(v):
        return (p.cross2(v,target.b)/determinant,p.cross2(target.a,v)/determinant)
    return quadratic_roots(source,lambda v:inverse(p.sub(v,target.center)),inverse,1.0)


def classify(curve,model,direction,theta):
    point=curve.point(theta)
    if isinstance(curve,unequal.Seam) and any(inside_bore(point,model.bores[k]) for k in curve.others):
        return 'omit'
    return 'hidden' if base.material_ahead(model,point,direction) else 'visible'


def curve_intervals(curve,flat,top_screen,hulls,model,direction):
    roots=list(curve.burial_roots) if isinstance(curve,unequal.Seam) else []
    normal=(-model.ax,-model.by,1)
    internal=not curve.feature.startswith('top')
    could_see_interior=p.dot(normal,direction)>p.EPS and direction[2]>p.EPS
    if internal and could_see_interior:
        for target in top_screen:
            roots.extend(ellipse_roots(flat,target))
        for polygon in hulls.values():
            for first,last in zip(polygon,polygon[1:]+polygon[:1]):
                tangent=p.sub(last,first)
                length=math.hypot(*tangent)
                if length<1e-9:
                    continue
                n=(-tangent[1]/length,tangent[0]/length)
                roots.extend(line_roots(flat,n,-p.dot(n,first)))
    knots=[]
    for t in sorted([0.0,TAU]+[t%TAU for t in roots]):
        if not knots or t-knots[-1]>1e-7:
            knots.append(t)
    if knots[-1]<TAU-1e-10:
        knots.append(TAU)
    pieces=[]
    for left,right in zip(knots,knots[1:]):
        if right-left<1e-8:
            continue
        state=classify(curve,model,direction,(left+right)/2)
        if pieces and pieces[-1][2]==state:
            pieces[-1]=(pieces[-1][0],right,state)
        else:
            pieces.append((left,right,state))
    # Polygonal overlap clips locate events to their screen tolerance. Refine
    # each observed state transition using the exact union-ray/material test.
    boundaries=[0.0]
    for left,right in zip(pieces,pieces[1:]):
        a=(left[0]+left[1])/2
        b=(right[0]+right[1])/2
        for _ in range(38):
            middle=(a+b)/2
            if classify(curve,model,direction,middle)==left[2]:
                a=middle
            else:
                b=middle
        boundaries.append((a+b)/2)
    boundaries.append(TAU)
    return [(boundaries[i],boundaries[i+1],part[2]) for i,part in enumerate(pieces)]


def generator_pieces(model,direction):
    result=[]
    for index,bore in enumerate(model.bores):
        du,dv=p.dot(bore.u,direction),p.dot(bore.v,direction)
        if math.hypot(du,dv)<1e-9:
            continue
        phase=math.atan2(dv,du)
        for theta in (phase-math.pi/2,phase+math.pi/2):
            first,last=bore.rim(theta,False),bore.rim(theta,True)
            delta=p.sub(last,first)
            hidden=[]
            for j,other in enumerate(model.bores):
                if j==index:
                    continue
                interval=base.cylinder_interval(other,first,delta)
                if interval is not None and min(1,interval[1])-max(0,interval[0])>1e-10:
                    hidden.append((max(0,interval[0]),min(1,interval[1])))
            cursor=0.0
            for start,end in p.merge_intervals(hidden)+[(1.0,1.0)]:
                if start-cursor>1e-9:
                    result.append((base.add(first,base.scaled(delta,cursor)),base.add(first,base.scaled(delta,start))))
                cursor=max(cursor,end)
    return result


def connection_routes(count,start,end):
    """All simple paths of the ray-interval overlap graph (at most four nodes).

    Connectivity is sufficient because each cylinder cuts a ray in one interval.
    The same bore at both ends already covers the whole in-body ray segment.
    """
    if start==end:
        return [()]
    remaining=[i for i in range(count) if i not in (start,end)]
    paths=[]
    for size in range(len(remaining)+1):
        for middle in itertools.permutations(remaining,size):
            nodes=(start,)+middle+(end,)
            paths.append(tuple(zip(nodes,nodes[1:])))
    return paths


def decorate(parent,model,azimuth,elevation,mapping,hidden,prefix):
    strokes=[node for node in parent if node.get('class') in ('edge','hidden-edge')]
    for node in strokes:
        parent.remove(node)
    surface=p.svg_el(parent,'g',data_layer='bore-surface')
    concealed=p.svg_el(parent,'g',data_layer='bore-hidden')
    visible=p.svg_el(parent,'g',data_layer='bore-visible')
    direction=p.camera(azimuth,elevation)[2]
    screen={curve.feature:screen_curve(curve,model,azimuth,elevation,mapping) for curve in model.curves}
    hulls={pair:unequal.overlap_projection_path(value,azimuth,elevation,mapping,True) for pair,value in model.pairs.items()}
    def overlap_id(i,j):
        return prefix+'-overlap-'+str(min(i,j))+'-'+str(max(i,j))
    if single.roof_facing(model,azimuth,elevation)>p.EPS:
        defs=p.svg_el(surface,'defs')
        for (i,j),polygon in hulls.items():
            clip=p.svg_el(defs,'clipPath',id=overlap_id(i,j),clipPathUnits='userSpaceOnUse')
            p.svg_el(clip,'path',d=p.path_data(polygon,True),data_feature='overlap-projection',data_pair=f'{i}-{j}',data_tolerance_px=unequal.SVG_TOLERANCE)
        for i in range(len(model.bores)):
            transform=single.matrix_text(base.matrix(screen['top-'+str(i)]))
            clip=p.svg_el(defs,'clipPath',id=prefix+'-opening-'+str(i),clipPathUnits='userSpaceOnUse')
            p.svg_el(clip,'circle',cx=0,cy=0,r=1,transform=transform)
            p.svg_el(surface,'circle',cx=0,cy=0,r=1,transform=transform,class_='bore-wall')
            if elevation>1e-8:
                aperture=p.svg_el(surface,'g',clip_path=f'url(#{prefix}-opening-{i})')
                for j in range(len(model.bores)):
                    routes=connection_routes(len(model.bores),i,j)
                    for route in routes:
                        clipped=aperture
                        for a,b in route:
                            clipped=p.svg_el(clipped,'g',clip_path=f'url(#{overlap_id(a,b)})')
                        p.svg_el(clipped,'circle',cx=0,cy=0,r=1,class_='face',data_feature='through-aperture',
                            transform=single.matrix_text(base.matrix(screen['bottom-'+str(j)])))
    top_screen=[screen['top-'+str(i)] for i in range(len(model.bores))]
    for curve in model.curves:
        if curve.feature.startswith('bottom') and elevation<1e-8:
            continue
        for left,right,state in curve_intervals(curve,screen[curve.feature],top_screen,hulls,model,direction):
            if state=='omit' or (state=='hidden' and hidden=='omit'):
                continue
            target=visible if state=='visible' else concealed
            attrs={'class_':('edge' if state=='visible' else 'hidden-edge')+' curve',
                   'data_curve':curve.feature,'data_start':p.fmt(left),'data_end':p.fmt(right)}
            if isinstance(curve,unequal.Seam):
                segments=unequal.bezier_segments(curve,left,right,model,azimuth,elevation,mapping)
                p.svg_el(target,'path',d=unequal.bezier_path(segments),data_tolerance_px=unequal.SVG_TOLERANCE,**attrs)
            else:
                attrs['transform']=single.matrix_text(base.matrix(screen[curve.feature]))
                if right-left>TAU-1e-7:
                    p.svg_el(target,'circle',cx=0,cy=0,r=1,**attrs)
                else:
                    p.svg_el(target,'path',d=single.unit_arc(left,right),**attrs)
    if hidden=='dash':
        for first,last in generator_pieces(model,direction):
            points=[unequal.project_point(v,model,azimuth,elevation,mapping) for v in (first,last)]
            p.svg_el(concealed,'path',d=p.path_data(points),class_='hidden-edge',data_feature='bore-generator')
    for node in strokes:
        (concealed if node.get('class')=='hidden-edge' else visible).insert(0,node)


if __name__=='__main__':
    sys.exit(base.main(constructor=ThreeBores,decorator=decorate))
