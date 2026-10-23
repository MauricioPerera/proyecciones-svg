import argparse
import copy
import math
import unittest

import proyectar as p
import taladros_cruzados as s


DATA={"type":"crossed_bores","footprint":[[0,0],[7,0],[8,1.5],[8,5],[6,6],[0,6]],
      "roof":{"offset":1.5,"slope_x":.2,"slope_y":.1},
      "bores":[{"axis":"inclined","center":[2.8,2.775],"direction":[.8,.15,1],"diameter":1.2,"through":True},
               {"axis":"inclined","center":[5.2,2.775],"direction":[-.8,.15,1],"diameter":1.2,"through":True}]}


def oracle(model, point, direction):
    """Independent material test: split the hull ray at every cylinder root."""
    low,high=1e-7,math.inf
    normalized=model.normalized(point)
    for face,normal in zip(model.body.faces,model.body.normals):
        offset=p.dot(normal,p.sub(normalized,model.body.vertices[face[0]]))*model.span
        speed=p.dot(normal,direction)
        if abs(speed)<1e-12:
            if offset>1e-8:
                return False
        elif speed>0:
            high=min(high,-offset/speed)
        else:
            low=max(low,-offset/speed)
    if high-low<1e-8:
        return False
    roots=[low,high]
    for bore in model.bores:
        offset=p.sub(point,bore.rim_centers[False])
        c=p.dot(offset,offset)-p.dot(offset,bore.axis)**2-bore.radius**2
        b=2*(p.dot(offset,direction)-p.dot(offset,bore.axis)*p.dot(direction,bore.axis))
        a=p.dot(direction,direction)-p.dot(direction,bore.axis)**2
        discriminant=b*b-4*a*c
        if a>1e-12 and discriminant>0:
            roots += [v for v in ((-b-math.sqrt(discriminant))/(2*a),(-b+math.sqrt(discriminant))/(2*a)) if low<v<high]
    roots=sorted(roots)
    for start,end in zip(roots,roots[1:]):
        if end-start<1e-8:
            continue
        at=s.add(point,s.scaled(direction,(start+end)/2))
        if all(p.dot((r:=p.sub(at,b.rim_centers[False])),r)-p.dot(r,b.axis)**2 > b.radius*b.radius+1e-10 for b in model.bores):
            return True
    return False


class CrossedBoreTests(unittest.TestCase):
    def test_two_exact_seam_ellipses_on_both_cylinders(self):
        model=s.CrossedBores(copy.deepcopy(DATA))
        self.assertAlmostEqual(math.dist(model.crossing,(4,3,1.5)),0)
        for curve in model.seams:
            for i in range(181):
                point=curve.point(2*math.pi*i/181)
                for bore in model.bores:
                    relative=p.sub(point,bore.rim_centers[False])
                    self.assertAlmostEqual(p.dot(relative,relative)-p.dot(relative,bore.axis)**2,bore.radius**2)

    def test_union_ray_against_partitioned_material_oracle(self):
        model=s.CrossedBores(copy.deepcopy(DATA))
        for azimuth in range(0,360,30):
            for elevation in (0,12,50,90):
                direction=p.camera(azimuth,elevation)[2]
                for curve in model.curves:
                    if curve.feature.startswith('bottom') and elevation==0:
                        continue
                    for i in range(47):
                        point=curve.point(2*math.pi*(i+.217)/47)
                        self.assertEqual(s.material_ahead(model,point,direction),oracle(model,point,direction),
                                         (curve.feature,azimuth,elevation,i))

    def test_all_conic_visibility_intervals_match_dense_ray_samples(self):
        model=s.CrossedBores(copy.deepcopy(DATA))
        mapping=p.angle_mapping(model.body)
        for azimuth in range(0,360,15):
            for elevation in (0,7,50,90):
                direction=p.camera(azimuth,elevation)[2]
                flat=[s.projected(c,model,azimuth,elevation,mapping) for c in model.curves]
                lines=s.generator_lines(model,direction,azimuth,elevation,mapping)
                for curve,screen in zip(model.curves,flat):
                    if curve.feature.startswith('bottom') and elevation==0:
                        continue
                    segments=s.visibility_intervals(curve,screen,flat,lines,model,direction)
                    for i in range(181):
                        theta=2*math.pi*(i+.391)/181
                        visible=next(value for left,right,value in segments if left<=theta<=right)
                        self.assertEqual(visible,not oracle(model,curve.point(theta),direction),
                                         (curve.feature,azimuth,elevation,theta,segments))

    def test_crossing_can_open_a_path_that_neither_single_bore_provides(self):
        model=s.CrossedBores(copy.deepcopy(DATA))
        count=0
        for i in range(100):
            point=(2.8+i*.012,3,0)
            intervals=[s.cylinder_interval(b,point,(0,0,1)) for b in model.bores]
            top=1.5+.2*point[0]+.1*point[1]
            individually_visible=any(v is not None and v[0]<=0 and v[1]>=top for v in intervals)
            if not individually_visible and not oracle(model,point,(0,0,1)):
                count+=1
                self.assertFalse(s.material_ahead(model,point,(0,0,1)))
        self.assertGreater(count,0)

    def test_generators_are_removed_inside_the_other_void(self):
        model=s.CrossedBores(copy.deepcopy(DATA))
        lines=s.generator_lines(model,p.camera(45,50)[2],45,50,p.angle_mapping(model.body))
        for _,pieces in lines:
            for start,end in pieces:
                middle=tuple((x+y)/2 for x,y in zip(start,end))
                distances=[]
                for bore in model.bores:
                    r=p.sub(middle,bore.rim_centers[False])
                    distances.append(p.dot(r,r)-p.dot(r,bore.axis)**2-bore.radius**2)
                self.assertGreaterEqual(min(distances),-1e-9)

    def test_repeated_and_periodic_polynomial_roots(self):
        roots=s.trig_roots(0,0,0,0,1)
        self.assertEqual(len(roots),4)
        for root in roots:
            self.assertAlmostEqual(math.sin(2*root),0)
        roots=s.trig_roots(1,1)
        self.assertTrue(any(abs(root-math.pi)<1e-6 for root in roots))

    def test_invalid_diameters_skew_axes_and_external_crossings_rejected(self):
        for change in ({'diameter':1.3},{'center':[5.2,3.1]},{'direction':[.8,.15,1]}):
            data=copy.deepcopy(DATA);data['bores'][1].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                s.CrossedBores(data)
        data=copy.deepcopy(DATA)
        for bore in data['bores']:
            bore['diameter']=2
        with self.assertRaises(ValueError):
            s.CrossedBores(data)

    def test_standalone_svg_clip_references_and_hidden_omission(self):
        root=s.animation(s.CrossedBores(copy.deepcopy(DATA)),argparse.Namespace(
            frames=12,seconds=1,sweep=360,azimuth=45,elevation=50,hidden='omit',loop=True))
        ids=[node.get('id') for node in root.iter() if node.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        for node in root.iter():
            self.assertNotIn('hidden-edge',node.get('class',''))
            if node.get('clip-path'):
                self.assertIn(node.get('clip-path')[5:-1],ids)
        self.assertEqual(len([node for node in root.iter() if node.get('data-feature')=='overlap-projection']),13)


if __name__=='__main__':
    unittest.main()
