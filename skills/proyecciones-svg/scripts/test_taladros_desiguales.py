import argparse
import copy
import math
import unittest

import proyectar as p
import taladros_cruzados as base
import taladros_desiguales as s
from test_taladros_cruzados import DATA,oracle


def model(reverse=False):
    data=copy.deepcopy(DATA)
    data['type']='unequal_crossed_bores'
    data['bores'][1]['diameter']=.8
    if reverse:
        data['bores'].reverse()
    return s.UnequalBores(data)


class UnequalBoreTests(unittest.TestCase):
    def test_spatial_seams_satisfy_both_different_cylinders(self):
        for reverse in (False,True):
            m=model(reverse)
            for curve in m.seams:
                for i in range(181):
                    point=curve.point(i*2*math.pi/181)
                    for bore in m.bores:
                        relative=p.sub(point,bore.rim_centers[False])
                        self.assertAlmostEqual(p.dot(relative,relative)-p.dot(relative,bore.axis)**2,bore.radius**2)

    def test_quartic_visibility_events_against_independent_ray_oracle(self):
        m=model()
        for az in range(0,360,15):
            for el in (0,7,50,90):
                toward=p.camera(az,el)[2]
                for curve in m.curves:
                    if curve.feature.startswith('bottom') and el==0:
                        continue
                    intervals=s.visibility_intervals(curve,m,toward)
                    for i in range(181):
                        theta=2*math.pi*(i+.417)/181
                        visible=next(value for left,right,value in intervals if left<=theta<=right)
                        self.assertEqual(visible,not oracle(m,curve.point(theta),toward),(az,el,curve.feature,theta,intervals))

    def test_seam_derivative_matches_finite_difference(self):
        for curve in model().seams:
            for i in range(61):
                t=i*2*math.pi/61
                actual=curve.derivative(t)
                numeric=base.scaled(p.sub(curve.point(t+1e-6),curve.point(t-1e-6)),5e5)
                self.assertLess(math.dist(actual,numeric),1e-8)

    def test_bezier_curve_error_with_dense_checks_between_control_samples(self):
        m=model()
        for az,el in ((0,0),(90,0),(45,50),(0,90),(177,50)):
            mapping=p.angle_mapping(m.body)
            for curve in m.seams:
                segments=s.bezier_segments(curve,0,2*math.pi,m,az,el,mapping)
                for first,c1,c2,last,left,right in segments:
                    for i in range(33):
                        t=i/32
                        cubic=tuple((1-t)**3*first[k]+3*(1-t)**2*t*c1[k]+3*(1-t)*t*t*c2[k]+t**3*last[k] for k in (0,1))
                        actual=s.project_point(curve.point(left+(right-left)*t),m,az,el,mapping)
                        self.assertLessEqual(math.dist(cubic,actual),s.SVG_TOLERANCE*1.01)

    def test_rejects_equal_radius_or_uncertified_internal_crossing(self):
        data=copy.deepcopy(DATA);data['type']='unequal_crossed_bores'
        with self.assertRaises(ValueError):
            s.UnequalBores(data)
        data['bores'][0]['diameter']=1.9
        data['bores'][1]['diameter']=1.2
        with self.assertRaises(ValueError):
            s.UnequalBores(data)

    def test_standalone_contains_curved_seams_native_cap_ellipses_and_tolerance(self):
        m=model()
        root=base.animation(m,argparse.Namespace(frames=12,seconds=1,sweep=360,azimuth=45,elevation=50,hidden='dash',loop=True),s.decorate)
        seams=[n for n in root.iter() if n.get('data-curve','').startswith('intersection')]
        caps=[n for n in root.iter() if n.get('data-curve','').startswith('top')]
        self.assertTrue(seams)
        self.assertTrue(all('C' in n.get('d','') and float(n.get('data-tolerance-px'))==s.SVG_TOLERANCE for n in seams))
        self.assertTrue(all(n.tag.endswith('circle') for n in caps))
        ids=[n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))


if __name__=='__main__':
    unittest.main()
