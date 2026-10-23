"""Two unequal intersecting bores; exact spatial curves, bounded SVG approximation."""
from __future__ import annotations

import math
import sys

import proyectar as p
import pieza_taladrada as single
import taladros_cruzados as base

TAU=2*math.pi
SVG_TOLERANCE=.025


class Seam:
    def __init__(self,center,small,large,sign,index):
        self.center=center
        self.r,self.R=small.radius,large.radius
        self.axis=small.axis
        self.cosine=p.dot(small.axis,large.axis)
        self.sine=math.sqrt(1-self.cosine**2)
        self.e1=base.scaled(p.sub(large.axis,base.scaled(small.axis,self.cosine)),1/self.sine)
        self.e2=p.cross(self.axis,self.e1)
        self.a=base.add(base.scaled(self.e1,self.r),base.scaled(self.axis,self.r*self.cosine/self.sine))
        self.b=base.scaled(self.e2,self.r)
        self.d=base.scaled(self.axis,sign/self.sine)
        self.feature='intersection-'+str(index)

    def point(self,t):
        q=math.sqrt(self.R*self.R-self.r*self.r*math.sin(t)**2)
        return tuple(c+a*math.cos(t)+b*math.sin(t)+d*q for c,a,b,d in zip(self.center,self.a,self.b,self.d))

    def derivative(self,t):
        q=math.sqrt(self.R*self.R-self.r*self.r*math.sin(t)**2)
        dq=-self.r*self.r*math.sin(t)*math.cos(t)/q
        return tuple(-a*math.sin(t)+b*math.cos(t)+d*dq for a,b,d in zip(self.a,self.b,self.d))

    def linear_roots(self,normal,constant):
        k=p.dot(normal,self.center)+constant
        a,b,d=(p.dot(normal,v) for v in (self.a,self.b,self.d))
        # Absorb R into the radical coefficient before testing for degeneracy.
        # This also works for a seam transformed to screen coordinates.
        d*=self.R
        scale=max(abs(k),abs(a),abs(b),abs(d))
        if scale==0:
            return []
        k,a,b,d=(v/scale for v in (k,a,b,d))
        ratio=(self.r/self.R)**2
        if abs(d)<1e-12:
            return base.trig_roots(k,a,b)
        roots=base.trig_roots(k*k+(a*a+b*b)/2-d*d*(1-ratio/2),
            2*k*a,2*k*b,(a*a-b*b)/2-d*d*ratio/2,a*b)
        return [t for t in roots if abs(k+a*math.cos(t)+b*math.sin(t)+d*math.sqrt(1-ratio*math.sin(t)**2))<1e-7]


class UnequalBores:
    """Dos taladros pasantes de distinto diámetro, ejes cruzados y cuatro bocas separadas."""
    def __init__(self,data):
        if not isinstance(data,dict) or data.get('type')!='unequal_crossed_bores':
            raise ValueError('Se esperaba type=unequal_crossed_bores.')
        bores=data.get('bores')
        if not isinstance(bores,list) or len(bores)!=2:
            raise ValueError('Se requieren dos taladros.')
        self.bores=[single.SlopedBore({**data,'type':'sloped_prism_with_bore','bore':b}) for b in bores]
        one,two=self.bores
        small,large=sorted(self.bores,key=lambda b:b.radius)
        # Avoid the equal-radius singular transition; use the conic constructor.
        if large.radius-small.radius<large.radius*1e-4:
            raise ValueError('Diámetros casi iguales: usa el constructor crossed_bores para radios iguales.')
        self.body,self.span,self.center=one.body,one.span,one.center
        self.body.data=data
        self.normalized=one.normalized
        self.ax,self.by=one.ax,one.by
        alignment=p.dot(one.axis,two.axis)
        denominator=1-alignment**2
        if denominator<1e-8:
            raise ValueError('Los ejes no pueden ser paralelos.')
        delta=p.sub(two.rim_centers[False],one.rim_centers[False])
        t=(p.dot(delta,one.axis)-alignment*p.dot(delta,two.axis))/denominator
        u=(alignment*p.dot(delta,one.axis)-p.dot(delta,two.axis))/denominator
        self.crossing=base.add(one.rim_centers[False],base.scaled(one.axis,t))
        other=base.add(two.rim_centers[False],base.scaled(two.axis,u))
        if math.dist(self.crossing,other)>self.span*1e-8:
            raise ValueError('Los ejes deben intersecarse; no se admiten ejes alabeados.')
        self.caps=[{cap:base.Ellipse(b.rim_centers[cap],b.rim_u[cap],b.rim_v[cap],('top-' if cap else 'bottom-')+str(i))
                    for cap in (False,True)} for i,b in enumerate(self.bores)]
        self.seams=[Seam(self.crossing,small,large,sign,i) for i,sign in enumerate((-1,1))]
        # A conservative analytic support bound certifies the complete curves,
        # rather than testing only sampled vertices against the body.
        for curve in self.seams:
            for face,n in zip(self.body.faces,self.body.normals):
                distance=p.dot(n,p.sub(self.normalized(curve.center),self.body.vertices[face[0]]))*self.span
                extent=math.hypot(p.dot(n,curve.a),p.dot(n,curve.b))+abs(p.dot(n,curve.d))*curve.R
                if distance+extent>=-self.span*1e-7:
                    raise ValueError('No se puede certificar el cruce completo dentro del cuerpo; reduce radios o cambia los ejes.')
        self.curves=[cap[key] for cap in self.caps for key in (False,True)]+self.seams


def split_intervals(roots,curve,model,direction):
    knots=[]
    for t in sorted([0.0,TAU]+[t%TAU for t in roots]):
        if not knots or t-knots[-1]>1e-7:
            knots.append(t)
    if knots[-1]<TAU-1e-10:
        knots.append(TAU)
    result=[]
    for left,right in zip(knots,knots[1:]):
        if right-left<1e-9:
            continue
        visible=not base.material_ahead(model,curve.point((left+right)/2),direction)
        if result and result[-1][2]==visible:
            result[-1]=(result[-1][0],right,visible)
        else:
            result.append((left,right,visible))
    return result


def distance_roots(curve,bore):
    def radial(vector):
        return p.sub(vector,base.scaled(bore.axis,p.dot(vector,bore.axis)))
    c=radial(p.sub(curve.center,bore.rim_centers[False]))
    a,b=radial(curve.a),radial(curve.b)
    return base.trig_roots(p.dot(c,c)-bore.radius**2+(p.dot(a,a)+p.dot(b,b))/2,
        2*p.dot(c,a),2*p.dot(c,b),(p.dot(a,a)-p.dot(b,b))/2,p.dot(a,b))


def visibility_intervals(curve,model,direction):
    normal=(-model.ax,-model.by,1.0)
    q=p.dot(normal,direction)
    if curve.feature.startswith('top'):
        return [(0,TAU,q>p.EPS)]
    if q<=p.EPS or direction[2]<=p.EPS:
        return [(0,TAU,False)]
    offset=model.bores[0].offset
    roots=[]
    if isinstance(curve,Seam):
        # At a seam both void ray intervals contain the starting point. Either
        # cylinder can cover the ray to the roof: each test is linear in P(t).
        for bore in model.bores:
            perpendicular=p.sub(direction,base.scaled(bore.axis,p.dot(direction,bore.axis)))
            h2=p.dot(perpendicular,perpendicular)
            if h2<1e-14:
                continue
            vector=p.sub(base.scaled(perpendicular,2*q),base.scaled(normal,h2))
            constant=h2*offset-2*q*p.dot(perpendicular,bore.rim_centers[False])
            roots.extend(curve.linear_roots(vector,constant))
    else:
        index=int(curve.feature.split('-')[-1])
        bore,other=model.bores[index],model.bores[1-index]
        perpendicular=p.sub(direction,base.scaled(bore.axis,p.dot(direction,bore.axis)))
        h2=p.dot(perpendicular,perpendicular)
        if h2<1e-14:
            return [(0,TAU,True)]
        # E(t) is the exit time from the cylinder whose lower rim contains P.
        e0=-2*p.dot(p.sub(curve.center,bore.rim_centers[False]),perpendicular)/h2
        ea,eb=-2*p.dot(curve.a,perpendicular)/h2,-2*p.dot(curve.b,perpendicular)/h2
        roof0=(offset-p.dot(normal,curve.center))/q
        ra,rb=-p.dot(normal,curve.a)/q,-p.dot(normal,curve.b)/q
        roots.extend(base.trig_roots(e0,ea,eb))
        roots.extend(base.trig_roots(e0-roof0,ea-ra,eb-rb))
        # A switch to the other bore is possible iff its interval includes
        # both the first bore's exit point and the roof point. Both loci are
        # affine ellipses, giving quartic event equations without sampling.
        for c,a,b in ((e0,ea,eb),(roof0,ra,rb)):
            locus=base.Ellipse(base.add(curve.center,base.scaled(direction,c)),
                base.add(curve.a,base.scaled(direction,a)),base.add(curve.b,base.scaled(direction,b)),'event')
            roots.extend(distance_roots(locus,other))
    return split_intervals(roots,curve,model,direction)


def project_point(point,model,azimuth,elevation,mapping):
    return mapping(p.project([model.normalized(point)],azimuth,elevation)[0])


def screen_derivative(vector,model,azimuth,elevation,mapping):
    origin=project_point(model.center,model,azimuth,elevation,mapping)
    end=project_point(base.add(model.center,vector),model,azimuth,elevation,mapping)
    return p.sub(end,origin)


def bezier_segments(curve,left,right,model,azimuth,elevation,mapping,tolerance=SVG_TOLERANCE):
    def point(t):
        return project_point(curve.point(t),model,azimuth,elevation,mapping)
    def derivative(t):
        return screen_derivative(curve.derivative(t),model,azimuth,elevation,mapping)
    def recurse(a,b,depth):
        first,last=point(a),point(b)
        control1=base.add(first,base.scaled(derivative(a),(b-a)/3))
        control2=p.sub(last,base.scaled(derivative(b),(b-a)/3))
        error=0
        for u in (.125,.25,.5,.75,.875):
            value=tuple((1-u)**3*first[i]+3*(1-u)**2*u*control1[i]+3*(1-u)*u*u*control2[i]+u**3*last[i] for i in (0,1))
            error=max(error,math.dist(value,point(a+(b-a)*u)))
        if (error>tolerance*.75 or b-a>math.pi/4) and depth<16:
            middle=(a+b)/2
            return recurse(a,middle,depth+1)+recurse(middle,b,depth+1)
        if error>tolerance:
            raise ValueError('No se alcanzó la tolerancia SVG de la curva de cruce.')
        return [(first,control1,control2,last,a,b)]
    return recurse(left,right,0)


def bezier_path(segments):
    def pair(v):
        return p.fmt(v[0])+','+p.fmt(v[1])
    return 'M'+pair(segments[0][0])+' '+' '.join('C'+pair(c1)+' '+pair(c2)+' '+pair(end) for _,c1,c2,end,_,_ in segments)


def convex_hull(points):
    points=sorted(set(points))
    def half(values):
        result=[]
        for v in values:
            while len(result)>1 and p.cross2(p.sub(result[-1],result[-2]),p.sub(v,result[-1]))<=0:
                result.pop()
            result.append(v)
        return result
    return half(points)[:-1]+half(reversed(points))[:-1]


def overlap_projection_path(model,azimuth,elevation,mapping,return_points=False):
    # Convex hull commutes with projection. Flatten the true spatial seams in
    # screen coordinates; this approximates only the 2D clip, never a 3D mesh.
    points=[]
    for curve in model.seams:
        def point(t):
            return project_point(curve.point(t),model,azimuth,elevation,mapping)
        def flatten(a,b,depth):
            first,last=point(a),point(b)
            chord=p.sub(last,first)
            length2=p.dot(chord,chord)
            error=0
            for u in (.25,.5,.75):
                value=point(a+(b-a)*u)
                fraction=max(0,min(1,p.dot(p.sub(value,first),chord)/length2)) if length2>1e-20 else 0
                nearest=base.add(first,base.scaled(chord,fraction))
                error=max(error,math.dist(value,nearest))
            if (error>SVG_TOLERANCE*.75 or b-a>math.pi/16) and depth<18:
                return flatten(a,(a+b)/2,depth+1)+flatten((a+b)/2,b,depth+1)
            if error>SVG_TOLERANCE:
                raise ValueError('No se alcanzó la tolerancia del clip SVG.')
            return [first,last]
        points.extend(flatten(0,TAU,0))
    hull=convex_hull(points)
    return hull if return_points else p.path_data(hull,True)


def decorate(parent,model,azimuth,elevation,mapping,hidden,prefix):
    strokes=[node for node in parent if node.get('class') in ('edge','hidden-edge')]
    for node in strokes:
        parent.remove(node)
    surface=p.svg_el(parent,'g',data_layer='bore-surface')
    concealed=p.svg_el(parent,'g',data_layer='bore-hidden')
    visible=p.svg_el(parent,'g',data_layer='bore-visible')
    direction=p.camera(azimuth,elevation)[2]
    cap_screen={c.feature:base.projected(c,model,azimuth,elevation,mapping) for cap in model.caps for c in cap.values()}
    if single.roof_facing(model,azimuth,elevation)>p.EPS:
        defs=p.svg_el(surface,'defs')
        overlap=p.svg_el(defs,'clipPath',id=prefix+'-overlap',clipPathUnits='userSpaceOnUse')
        p.svg_el(overlap,'path',d=overlap_projection_path(model,azimuth,elevation,mapping),
            data_feature='overlap-projection',data_tolerance_px=SVG_TOLERANCE)
        for i in range(2):
            transform=single.matrix_text(base.matrix(cap_screen['top-'+str(i)]))
            clip=p.svg_el(defs,'clipPath',id=prefix+'-opening-'+str(i),clipPathUnits='userSpaceOnUse')
            p.svg_el(clip,'circle',cx=0,cy=0,r=1,transform=transform)
            p.svg_el(surface,'circle',cx=0,cy=0,r=1,transform=transform,class_='bore-wall')
            if elevation>1e-8:
                aperture=p.svg_el(surface,'g',clip_path=f'url(#{prefix}-opening-{i})')
                for j in range(2):
                    clipped=aperture if i==j else p.svg_el(aperture,'g',clip_path=f'url(#{prefix}-overlap)')
                    p.svg_el(clipped,'circle',cx=0,cy=0,r=1,class_='face',
                        transform=single.matrix_text(base.matrix(cap_screen['bottom-'+str(j)])),data_feature='through-aperture')
    for curve in model.curves:
        if curve.feature.startswith('bottom') and elevation<1e-8:
            continue
        for left,right,is_visible in visibility_intervals(curve,model,direction):
            if not is_visible and hidden=='omit':
                continue
            target=visible if is_visible else concealed
            attrs={'class_':('edge' if is_visible else 'hidden-edge')+' curve',
                   'data_curve':curve.feature,'data_start':p.fmt(left),'data_end':p.fmt(right)}
            if isinstance(curve,Seam):
                segments=bezier_segments(curve,left,right,model,azimuth,elevation,mapping)
                p.svg_el(target,'path',d=bezier_path(segments),data_tolerance_px=SVG_TOLERANCE,**attrs)
            else:
                attrs['transform']=single.matrix_text(base.matrix(cap_screen[curve.feature]))
                if right-left>TAU-1e-7:
                    p.svg_el(target,'circle',cx=0,cy=0,r=1,**attrs)
                else:
                    p.svg_el(target,'path',d=single.unit_arc(left,right),**attrs)
    if hidden=='dash':
        for _,pieces in base.generator_lines(model,direction,azimuth,elevation,mapping):
            for start,end in pieces:
                points=[project_point(v,model,azimuth,elevation,mapping) for v in (start,end)]
                p.svg_el(concealed,'path',d=p.path_data(points),class_='hidden-edge',data_feature='bore-generator')
    for node in strokes:
        (concealed if node.get('class')=='hidden-edge' else visible).insert(0,node)


if __name__=='__main__':
    sys.exit(base.main(constructor=UnequalBores,decorator=decorate))
