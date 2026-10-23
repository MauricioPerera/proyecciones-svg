import argparse
import copy
import itertools
import math
import unittest

import proyectar as p
import taladros_cruzados as base
import taladros_desiguales as unequal
import tres_taladros as shared
from cuatro_taladros import FourBores
from test_tres_taladros import model as three_model
from test_taladros_cruzados import oracle


def model():
    data=copy.deepcopy(three_model().body.data)
    data['type']='quadruple_crossed_bores'
    data['bores'].append({'axis':'inclined','center':[4,4.425],'direction':[0,-.95,1],'diameter':.4,'through':True})
    return FourBores(data)


class FourBoreTests(unittest.TestCase):
    def test_four_radii_and_exact_six_pair_intersections(self):
        m=model()
        self.assertEqual([b.radius*2 for b in m.bores],[1.2,.8,.6,.4])
        self.assertLess(math.dist(m.crossing,(4,3,1.5)),1e-12)
        self.assertEqual(len(m.pairs),6)
        self.assertEqual(len(m.seams),12)
        for curve in m.seams:
            self.assertEqual(len(curve.others),2)
            for i in curve.pair:
                bore=m.bores[i]
                for j in range(73):
                    point=curve.point(j*math.tau/73)
                    r=p.sub(point,bore.rim_centers[False])
                    self.assertAlmostEqual(p.dot(r,r)-p.dot(r,bore.axis)**2,bore.radius**2)

    def test_simple_routes_equal_interval_union_for_every_overlap_graph(self):
        # Every four-interval overlap graph, including chains requiring all four.
        intervals=list(itertools.combinations(range(6),2))
        exercised_chain=False
        for spans in itertools.product(intervals,repeat=4):
            adjacency={(i,j):max(spans[i][0],spans[j][0])<=min(spans[i][1],spans[j][1])
                       for i in range(4) for j in range(4)}
            for start,end in ((0,1),(0,2),(0,3)):
                connected={start}
                for _ in range(3):
                    connected|={j for i in connected for j in range(4) if adjacency[i,j]}
                routes=shared.connection_routes(4,start,end)
                active=[route for route in routes if all(adjacency[a,b] for a,b in route)]
                self.assertEqual(bool(active),end in connected)
                exercised_chain|=bool(active) and min(map(len,active))==3
        self.assertTrue(exercised_chain)

    def test_visibility_and_double_burial_against_independent_oracle(self):
        m=model()
        buried_by_second_other=0
        for azimuth,elevation in [(a,e) for a in range(0,360,45) for e in (0,50,90)]:
            mapping=p.angle_mapping(m.body)
            direction=p.camera(azimuth,elevation)[2]
            screens={c.feature:shared.screen_curve(c,m,azimuth,elevation,mapping) for c in m.curves}
            tops=[screens['top-'+str(i)] for i in range(4)]
            hulls={pair:unequal.overlap_projection_path(value,azimuth,elevation,mapping,True) for pair,value in m.pairs.items()}
            for curve in m.curves:
                if curve.feature.startswith('bottom') and elevation==0:
                    continue
                intervals=shared.curve_intervals(curve,screens[curve.feature],tops,hulls,m,direction)
                for j in range(151):
                    theta=math.tau*(j+.391)/151
                    actual=next(state for a,b,state in intervals if a<=theta<=b)
                    point=curve.point(theta)
                    buried=isinstance(curve,unequal.Seam) and any(shared.inside_bore(point,m.bores[k]) for k in curve.others)
                    if isinstance(curve,unequal.Seam) and shared.inside_bore(point,m.bores[curve.others[1]]):
                        buried_by_second_other+=1
                    expected='omit' if buried else 'hidden' if oracle(m,point,direction) else 'visible'
                    self.assertEqual(actual,expected,(azimuth,elevation,curve.feature,theta))
        self.assertGreater(buried_by_second_other,0)
        for first,last in shared.generator_pieces(m,p.camera(45,50)[2]):
            for fraction in (.1,.5,.9):
                point=base.add(first,base.scaled(p.sub(last,first),fraction))
                self.assertFalse(any(shared.inside_bore(point,b,1e-9) for b in m.bores))

    def test_svg_has_eight_mouths_and_no_buried_seams(self):
        m=model()
        root=base.animation(m,argparse.Namespace(frames=8,seconds=1,sweep=360,azimuth=45,elevation=50,hidden='dash',loop=True),shared.decorate)
        ids=[n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        lookup={c.feature:c for c in m.seams}
        for node in root.iter():
            feature=node.get('data-curve')
            if feature in lookup:
                curve=lookup[feature]
                a,b=float(node.get('data-start')),float(node.get('data-end'))
                for fraction in (.05,.5,.95):
                    point=curve.point(a+(b-a)*fraction)
                    self.assertFalse(any(shared.inside_bore(point,m.bores[k],1e-6) for k in curve.others))
            if node.get('clip-path'):
                self.assertIn(node.get('clip-path')[5:-1],ids)
        for frame in (n for n in root.iter() if n.get('data-frame') is not None):
            self.assertEqual(sum(n.get('class')=='bore-wall' for n in frame.iter()),4)
            self.assertEqual(sum(n.get('data-feature')=='overlap-projection' for n in frame.iter()),6)


if __name__=='__main__':
    unittest.main()
