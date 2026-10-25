"""Read exported surfaces independently and test connected cylindrical voids."""
import copy
import io
import math
import random
import struct
import unittest
import xml.etree.ElementTree as ET
import zipfile

import proyectar as p
from exportar_mallas import prepare, glb, three_mf, stl, validate_mesh
from test_exportar_mallas import load, read_glb, volume, MF
from test_escalas import scaled, radial_ratio
from mallas_taladradas import segments


def read_surface(mesh,format):
    if format=='glb':
        _,(positions,_)=read_glb(glb(mesh))
        positions=[(x*1000,-z*1000,y*1000) for x,y,z in positions]
    elif format=='stl':
        raw=stl(mesh);count=struct.unpack_from('<I',raw,80)[0]
        positions=[]
        for i in range(count):
            values=struct.unpack_from('<12fH',raw,84+i*50)
            positions.extend(values[j:j+3] for j in (3,6,9))
    else:
        with zipfile.ZipFile(io.BytesIO(three_mf(mesh))) as archive:
            root=ET.fromstring(archive.read('3D/3dmodel.model'))
        vertices=[tuple(float(n.get(k)) for k in ('x','y','z')) for n in root.iter(MF+'vertex')]
        return [[vertices[int(n.get(k))] for k in ('v1','v2','v3')] for n in root.iter(MF+'triangle')]
    return [positions[i:i+3] for i in range(0,len(positions),3)]


def winding(surface,point):
    """Solid angle, independent of backend, triangulation and ray directions."""
    angles=[]
    for tri in surface:
        a,b,c=[p.sub(v,point) for v in tri]
        la,lb,lc=map(lambda v:math.hypot(*v),(a,b,c))
        denominator=la*lb*lc+p.dot(a,b)*lc+p.dot(b,c)*la+p.dot(c,a)*lb
        angles.append(2*math.atan2(p.dot(a,p.cross(b,c)),denominator))
    return math.fsum(angles)/(4*math.pi)


def audit_edges(surface):
    vertices={};edges={}
    for tri in surface:
        ids=[vertices.setdefault(tuple(v),len(vertices)) for v in tri]
        for a,b in zip(ids,ids[1:]+ids[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    assert all(len(e)==2 and e[0]==tuple(reversed(e[1])) for e in edges.values())
    return len(vertices)-len(edges)+len(surface)


class BoredMeshTests(unittest.TestCase):
    def test_every_supported_bored_constructor_has_expected_handles_and_closed_formats(self):
        cases=(('bloque-taladrado',1),('irregular-taladrada',1),('taladro-inclinado',1),
               ('taladros-cruzados',3),('taladros-desiguales',3),('tres-taladros',5),('cuatro-taladros',7))
        for name,genus in cases:
            with self.subTest(name=name):
                source=load(name+'.json');previous=copy.deepcopy(source);mesh=prepare(source)
                self.assertEqual(mesh.genus,genus)
                self.assertEqual(source,previous)
                for format in ('glb','3mf','stl'):
                    surface=read_surface(mesh,format)
                    self.assertEqual(audit_edges(surface),2-2*genus,format)
                    self.assertTrue(math.isclose(volume(surface),mesh.volume_mm3,rel_tol=1e-6),format)
                self.assertLessEqual(mesh.tessellation['max_radial_sagitta_mm'],.02)

    def test_four_cylinders_and_their_crossing_are_empty_in_every_export(self):
        source=load('cuatro-taladros.json');mesh=prepare(source)
        points=[(40,30,15)]
        for bore in source['bores']:
            dx,dy,dz=bore['direction']
            for z in (.1,.6,1.1,1.5,2,2.5):
                x=bore['center'][0]+z*dx/dz;y=bore['center'][1]+z*dy/dz
                roof=source['roof'];height=roof['offset']+roof['slope_x']*x+roof['slope_y']*y
                if z<height-.05:points.append((x*10,y*10,z*10))
        # Retained material at corners and between mouths, away from boundaries.
        material=((5,5,5),(70,45,10),(10,50,10),(60,10,5))
        for format in ('glb','3mf','stl'):
            surface=read_surface(mesh,format)
            for point in points:self.assertAlmostEqual(winding(surface,point),0,places=6,msg=(format,point))
            for point in material:self.assertAlmostEqual(winding(surface,point),1,places=6,msg=(format,point))

    def test_seeded_points_match_raw_cylinder_union_away_from_faceting_band(self):
        source=load('cuatro-taladros.json');mesh=prepare(source)
        surface=read_surface(mesh,'3mf');rng=random.Random(20261025)
        checked=voids=0
        for _ in range(200):
            point=(rng.uniform(.15,7.8),rng.uniform(.15,5.85),rng.uniform(.15,3))
            x,y,z=point;roof=source['roof'];height=roof['offset']+roof['slope_x']*x+roof['slope_y']*y
            if z>height-.05:continue
            footprint=source['footprint']
            if any(p.cross2(p.sub(b,a),p.sub((x,y),a))<.1 for a,b in zip(footprint,footprint[1:]+footprint[:1])):continue
            gaps=[(math.sqrt(radial_ratio(point,b))-1)*b['diameter']/2 for b in source['bores']]
            if min(abs(g) for g in gaps)<.01:continue
            expected=int(all(g>0 for g in gaps));voids+=1-expected;checked+=1
            self.assertAlmostEqual(winding(surface,tuple(v*10 for v in point)),expected,places=6,msg=point)
        self.assertGreater(checked,100);self.assertGreater(voids,3)

    def test_no_triangle_is_buried_inside_the_communicating_void(self):
        source=load('cuatro-taladros.json');mesh=prepare(source)
        for tri in mesh.triangles:
            center=tuple(math.fsum(mesh.vertices[i][k] for i in tri)/30 for k in range(3))
            for bore in source['bores']:
                gap=(math.sqrt(radial_ratio(center,bore))-1)*bore['diameter']/2*10
                self.assertGreaterEqual(gap,-.02000001)

    def test_single_hole_volume_matches_its_inscribed_polygon_and_converges(self):
        source=load('bloque-taladrado.json');w,d,h=source['size'];radius=source['bore']['diameter']/2
        analytic=(w*d-math.pi*radius**2)*h*1000
        previous=math.inf
        for tolerance in (.02,.005,.001):
            mesh=prepare(source,tolerance_mm=tolerance);n=mesh.tessellation['segments_per_bore'][0]
            expected=(w*d-n*radius**2*math.sin(2*math.pi/n)/2)*h*1000
            self.assertTrue(math.isclose(mesh.volume_mm3,expected,rel_tol=1e-12))
            error=abs(mesh.volume_mm3-analytic);self.assertLess(error,previous);previous=error
        self.assertLess(previous/analytic,1e-4)

    def test_four_holes_converge_without_counting_overlapping_voids_twice(self):
        source=load('cuatro-taladros.json')
        coarse=prepare(source);medium=prepare(source,tolerance_mm=.005);fine=prepare(source,tolerance_mm=.001)
        self.assertGreater(coarse.volume_mm3,medium.volume_mm3)
        self.assertGreater(medium.volume_mm3,fine.volume_mm3)
        self.assertLess(abs(medium.volume_mm3-fine.volume_mm3),abs(coarse.volume_mm3-fine.volume_mm3))
        self.assertLess((coarse.volume_mm3-fine.volume_mm3)/fine.volume_mm3,.001)
        from mallas_taladradas import projection_model
        model=projection_model(source);body=model.body
        body_volume=abs(volume([[body.vertices[i] for i in t] for t in body.triangles]))*(body.span*10)**3
        hole_volumes=[]
        for bore in model.bores:
            length=math.dist(bore.rim_centers[False],bore.rim_centers[True])
            hole_volumes.append(math.pi*bore.radius**2*length*1000)
        self.assertGreater(fine.volume_mm3,body_volume-sum(hole_volumes))
        self.assertLess(fine.volume_mm3,body_volume-max(hole_volumes))

    def test_four_holes_preserve_geometry_at_extreme_scales_and_unit_changes(self):
        source=load('cuatro-taladros.json');reference=prepare(source)
        for factor in (1e-8,1,1e6):
            with self.subTest(factor=factor):
                mesh=prepare(scaled(source,factor),tolerance_mm=.02*factor)
                self.assertEqual(mesh.genus,7)
                self.assertTrue(math.isclose(mesh.volume_mm3,reference.volume_mm3*factor**3,rel_tol=1e-10))
                for format in ('glb','3mf','stl'):
                    surface=read_surface(mesh,format)
                    self.assertEqual(audit_edges(surface),-12)
                    self.assertTrue(math.isclose(volume(surface),reference.volume_mm3*factor**3,rel_tol=2e-6))
        for units,factor in (('mm',10),('m',.01)):
            data=scaled(source,factor);data['units']=units
            self.assertTrue(math.isclose(prepare(data).volume_mm3,reference.volume_mm3,rel_tol=1e-12))

    def test_tolerance_limits_and_wrong_topology_are_rejected(self):
        for tolerance in (0,-1,True,math.nan,math.inf,1e-30):
            with self.subTest(tolerance=tolerance),self.assertRaises(ValueError):prepare(load('cuatro-taladros.json'),tolerance_mm=tolerance)
        for r,t in ((6,.02),(4,.02),(1,.001)):
            n=segments(r,t);self.assertLessEqual(r*(1-math.cos(math.pi/n)),t)
        mesh=prepare(load('cuatro-taladros.json'))
        with self.assertRaises(ValueError):validate_mesh(mesh.vertices,mesh.triangles,0)
        for tris in (mesh.triangles[:-1],mesh.triangles+[mesh.triangles[0]]):
            with self.assertRaises(ValueError):validate_mesh(mesh.vertices,tris,7)

    def test_repeated_bored_exports_are_deterministic(self):
        data=load('cuatro-taladros.json');first=prepare(data);second=prepare(data)
        for encode in (glb,three_mf,stl):self.assertEqual(encode(first),encode(second))


if __name__=='__main__':unittest.main()
