import argparse
import copy
import math
import unittest

import proyectar as p
import taladros_cruzados as base
import taladros_desiguales as unequal
import tres_taladros as s
from test_taladros_cruzados import DATA,oracle


def model():
    data=copy.deepcopy(DATA)
    data['type']='triple_crossed_bores'
    data['bores'][1]['diameter']=.8
    data['bores'].append({'axis':'inclined','center':[4,1.575],'direction':[0,.95,1],'diameter':.6,'through':True})
    return s.ThreeBores(data)


class ThreeBoreTests(unittest.TestCase):
    def test_three_diameters_concurrency_and_exact_pair_seams(self):
        m=model()
        self.assertAlmostEqual(math.dist(m.crossing,(4,3,1.5)),0)
        self.assertEqual([b.radius*2 for b in m.bores],[1.2,.8,.6])
        for curve in m.seams:
            for index in curve.pair:
                bore=m.bores[index]
                for i in range(93):
                    relative=p.sub(curve.point(i*2*math.pi/93),bore.rim_centers[False])
                    self.assertAlmostEqual(p.dot(relative,relative)-p.dot(relative,bore.axis)**2,bore.radius**2)

    def test_burial_roots_are_real_triple_surface_intersections(self):
        m=model()
        buried=0
        for curve in m.seams:
            self.assertGreater(len(curve.burial_roots),0)
            bore=m.bores[curve.third]
            for t in curve.burial_roots:
                r=p.sub(curve.point(t),bore.rim_centers[False])
                self.assertLess(abs(p.dot(r,r)-p.dot(r,bore.axis)**2-bore.radius**2),1e-7)
            buried+=sum(s.inside_bore(curve.point(i*2*math.pi/181),bore) for i in range(181))
        self.assertGreater(buried,0)

    def test_trim_and_visibility_against_independent_ray_oracle(self):
        m=model()
        for azimuth,elevation in [(a,e) for a in range(0,360,45) for e in (0,50,90)]:
            mapping=p.angle_mapping(m.body)
            direction=p.camera(azimuth,elevation)[2]
            screens={c.feature:s.screen_curve(c,m,azimuth,elevation,mapping) for c in m.curves}
            tops=[screens['top-'+str(i)] for i in range(3)]
            hulls={pair:unequal.overlap_projection_path(value,azimuth,elevation,mapping,True) for pair,value in m.pairs.items()}
            for curve in m.curves:
                if curve.feature.startswith('bottom') and elevation==0:
                    continue
                intervals=s.curve_intervals(curve,screens[curve.feature],tops,hulls,m,direction)
                for i in range(181):
                    t=2*math.pi*(i+.391)/181
                    actual=next(value for left,right,value in intervals if left<=t<=right)
                    point=curve.point(t)
                    if isinstance(curve,unequal.Seam) and s.inside_bore(point,m.bores[curve.third]):
                        expected='omit'
                    else:
                        expected='hidden' if oracle(m,point,direction) else 'visible'
                    self.assertEqual(actual,expected,(azimuth,elevation,curve.feature,t,intervals))

    def test_no_generator_is_buried_in_another_cylinder(self):
        m=model()
        for first,last in s.generator_pieces(m,p.camera(45,50)[2]):
            for fraction in (.1,.5,.9):
                point=base.add(first,base.scaled(p.sub(last,first),fraction))
                self.assertFalse(any(s.inside_bore(point,b,1e-9) for b in m.bores))

    def test_no_buried_curve_segments_emitted_and_clips_are_unique(self):
        m=model()
        root=base.animation(m,argparse.Namespace(frames=8,seconds=1,sweep=360,azimuth=45,elevation=50,hidden='dash',loop=True),s.decorate)
        lookup={c.feature:c for c in m.seams}
        ids=[n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        for node in root.iter():
            feature=node.get('data-curve')
            if feature in lookup:
                curve=lookup[feature]
                left,right=float(node.get('data-start')),float(node.get('data-end'))
                for fraction in (.05,.5,.95):
                    self.assertFalse(s.inside_bore(curve.point(left+(right-left)*fraction),m.bores[curve.third],1e-6))
            if node.get('clip-path'):
                self.assertIn(node.get('clip-path')[5:-1],ids)


if __name__=='__main__':
    unittest.main()
