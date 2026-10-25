"""Facet and subtract validated through-cylinders, in normalized coordinates.

Manifold performs the union/difference; it never participates in SVG or Cota.
The specified tolerance bounds the radial sagitta of each inscribed polygon,
not the Hausdorff distance of oblique rims or intersections of cylinders.
"""
from __future__ import annotations

import importlib.metadata
import math
import proyectar as p


def projection_model(data):
    kind=data.get('type')
    if kind=='block_with_bore':
        from taladro_cilindrico import BoredBlock
        return BoredBlock(data)
    if kind=='sloped_prism_with_bore':
        from pieza_taladrada import SlopedBore
        return SlopedBore(data)
    if kind=='crossed_bores':
        from taladros_cruzados import CrossedBores
        return CrossedBores(data)
    if kind=='unequal_crossed_bores':
        from taladros_desiguales import UnequalBores
        return UnequalBores(data)
    if kind=='triple_crossed_bores':
        from tres_taladros import ThreeBores
        return ThreeBores(data)
    if kind=='quadruple_crossed_bores':
        from cuatro_taladros import FourBores
        return FourBores(data)
    raise ValueError('Constructor taladrado no admitido.')


def segments(radius_mm,tolerance_mm):
    ratio=tolerance_mm/radius_mm
    if ratio>=1:return 32
    if ratio<=0:raise ValueError('La tolerancia radial no es representable a esta escala.')
    angle=2*math.asin(math.sqrt(ratio/2))
    count=max(32,4*math.ceil(math.pi/angle/4))
    if count>512:
        raise ValueError('La tolerancia radial requiere más de 512 segmentos por cilindro; aumenta --mesh-tolerance-mm.')
    return count


def triangulate_bores(data,factor,tolerance_mm):
    model=projection_model(data)  # Reuse all analytic clearance/concurrence checks.
    body=getattr(model,'box',getattr(model,'body',None))
    bores=getattr(model,'bores',[model])
    span_mm=body.span*factor
    if not math.isfinite(span_mm) or span_mm<=0:
        raise ValueError('Extensión física de malla fuera del rango numérico.')
    counts=[segments(b.radius*factor,tolerance_mm) for b in bores]
    try:
        import manifold3d as m
        import numpy as np
    except ImportError as error:
        raise ValueError('Los taladros GLB/3MF/STL requieren la dependencia opcional: python -m pip install -r <skill>/requirements-mesh.txt. SVG y Cota no la necesitan.') from error
    triangles=[tuple(t) for t in body.triangles]
    if math.fsum(p.dot(body.vertices[a],p.cross(body.vertices[b],body.vertices[c])) for a,b,c in triangles)<0:
        triangles=[(a,c,b) for a,b,c in triangles]
    solid=m.Manifold(m.Mesh64(np.array(body.vertices,dtype=np.float64),np.array(triangles,dtype=np.uint64)))
    if solid.status()!=m.Error.NoError:raise ValueError('Manifold rechazó la frontera del cuerpo.')
    center=tuple(a+(b-a)/2 for a,b in zip(body.minimum,body.maximum))
    cutters=[]
    for bore,count in zip(bores,counts):
        axis=getattr(bore,'axis',(0.,0.,1.))
        base=bore.rim_centers[False] if hasattr(bore,'rim_centers') else (bore.cx,bore.cy,0.)
        base=tuple((v-c)/body.span for v,c in zip(base,center))
        u=getattr(bore,'u',(1.,0.,0.));v=p.cross(axis,u)
        along=[p.dot(p.sub(point,base),axis) for point in body.vertices]
        low,high=min(along)-1,max(along)+1
        origin=tuple(b+low*a for b,a in zip(base,axis))
        cutter=m.Manifold.cylinder(high-low,bore.radius/body.span,circular_segments=count)
        cutters.append(cutter.transform([[u[i],v[i],axis[i],origin[i]] for i in range(3)]))
    void=m.Manifold.batch_boolean(cutters,m.OpType.Add)
    result=solid-void
    genus=2*len(bores)-1  # 2N separate mouths, one connected internal void.
    if result.status()!=m.Error.NoError or result.is_empty() or len(result.decompose())!=1 or result.genus()!=genus:
        raise ValueError('El vaciado no conserva un sólido único con todos los conductos comunicados.')
    if result.num_vert()>32768 or result.num_tri()>65536:
        raise ValueError('El vaciado excede el presupuesto de malla.')
    raw=result.to_mesh64()
    vertices=[tuple((float(v)*body.span+c)*factor for v,c in zip(point[:3],center)) for point in raw.vert_properties]
    triangles=[tuple(int(i) for i in tri) for tri in raw.tri_verts]
    details={'backend':'manifold3d','backend_version':importlib.metadata.version('manifold3d'),
             'operation':'body minus union of inscribed polygonal cylinders',
             'radial_tolerance_mm':tolerance_mm,'segments_per_bore':counts,
             'max_radial_sagitta_mm':max(b.radius*factor*(1-math.cos(math.pi/n)) for b,n in zip(bores,counts)),
             'bound_scope':'radial sagitta only; not an intersection/rim Hausdorff or manufacturing tolerance',
             'mouths':2*len(bores),'communicating_void':True}
    return vertices,triangles,genus,details
