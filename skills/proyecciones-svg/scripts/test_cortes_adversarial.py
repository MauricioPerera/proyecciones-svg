"""Seeded adversarial/metamorphic checks using independent raw-geometry oracles."""
import copy
import itertools
import json
import math
import os
from pathlib import Path
import random
import unittest
import xml.etree.ElementTree as ET

import cortes
import proyectar as p
from cuatro_taladros import FourBores
from taladro_cilindrico import BoredBlock
from test_escalas import scaled

SEED = int(os.environ.get('ADVERSARIAL_SEED', '20261025'))
ASSETS = Path(__file__).resolve().parent.parent/'assets'
NS = '{http://www.w3.org/2000/svg}'


def load(name='cuatro-taladros.json'):
    return json.loads((ASSETS/name).read_text(encoding='utf-8'))


def raw_void(point, bore):
    # Cross-product distance to an infinite axis, independent of the conic code.
    v = (point[0]-bore['center'][0], point[1]-bore['center'][1], point[2])
    a = bore.get('direction', [0, 0, 1])
    cross = (v[1]*a[2]-v[2]*a[1], v[2]*a[0]-v[0]*a[2], v[0]*a[1]-v[1]*a[0])
    return math.hypot(*cross)/math.hypot(*a)/(bore['diameter']/2)


def raw_body(point, data):
    x, y, z = point
    f = data['footprint']
    values = [z, data['roof']['offset']+data['roof']['slope_x']*x+data['roof']['slope_y']*y-z]
    values += [((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/math.dist(a, b) for a, b in zip(f, f[1:]+f[:1])]
    return min(values)


def raw_polygon_margin(q, polygon):
    # Convex polygons emitted by clipping keep positive orientation.
    return min(((b[0]-a[0])*(q[1]-a[1])-(b[1]-a[1])*(q[0]-a[0]))/math.dist(a,b)
               for a,b in zip(polygon,polygon[1:]+polygon[:1]))


def section(data):
    return cortes.prepare(FourBores(data))[1][0]


class AdversarialSectionTests(unittest.TestCase):
    def test_seeded_random_planes_match_raw_body_and_void_union_at_three_scales(self):
        rng = random.Random(SEED)
        normals = [[rng.uniform(-1,1) for _ in range(3)] for _ in range(32)]
        for factor, normal in itertools.product((1e-8,1.,1e6),normals):
            with self.subTest(seed=SEED,scale=factor,normal=normal):
                data = scaled(load(),factor)
                data['sections'] = [{'origin':[4*factor,3*factor,1.5*factor],'normal':normal}]
                body,cuts = cortes.prepare(FourBores(data))
                cut = cuts[0]
                low = [min(q[i] for q in cut.polygon) for i in (0,1)]
                high = [max(q[i] for q in cut.polygon) for i in (0,1)]
                for i,j in itertools.product(range(17),range(13)):
                    q = (low[0]+(high[0]-low[0])*(i+.371)/17,
                         low[1]+(high[1]-low[1])*(j+.613)/13)
                    point = body.world(cut.point(q))
                    distances = [raw_void(point,b) for b in data['bores']]
                    margin = raw_body(point,data)/body.span
                    if abs(margin)>1e-9:
                        self.assertEqual(raw_polygon_margin(q,cut.polygon)>0,margin>0)
                    if min(abs(v-1) for v in distances)>1e-9:
                        self.assertEqual(any(cortes.contains(s,q) for s in cut.shapes),min(distances)<1)
                ET.fromstring(ET.tostring(cortes.section_svg(body,cuts)))

    def test_normal_and_up_magnitudes_do_not_change_the_plane(self):
        for normal,up in (([1,1,1],[0,0,1]),([0,-1,.15],[1,0,0])):
            reference = None
            for magnitude in (1e-300,1e-150,1.,1e150,1.7e308):
                with self.subTest(normal=normal,magnitude=magnitude):
                    data=load()
                    data['sections']=[{'origin':[4,3,1.5],'normal':[x*magnitude for x in normal],
                                       'up':[x*magnitude for x in up]}]
                    cut=section(data)
                    if reference is None:
                        reference=cut
                    self.assertLess(math.dist(cut.n,reference.n),1e-12)
                    self.assertEqual(len(cut.polygon),len(reference.polygon))
                    for a,b in zip(cut.polygon,reference.polygon):
                        self.assertLess(math.dist(a,b),1e-11)

    def test_moving_origin_inside_same_plane_preserves_area_and_contours(self):
        for distance in (0.,1e6,-1e12,1e16):
            with self.subTest(distance=distance):
                data=load()
                data['sections']=[{'origin':[4+distance,3,1.5],'normal':[0,1,0]}]
                cut=section(data)
                world_points=[cut.body.world(cut.point(q)) for q in cut.polygon]
                if distance==0:
                    reference=cut;reference_points=world_points
                self.assertEqual(len(cut.polygon),len(reference.polygon))
                for a,b in zip(world_points,reference_points):
                    self.assertLess(math.dist(a,b),1e-11)
                self.assertTrue(math.isclose(p.signed_area(cut.polygon),p.signed_area(reference.polygon),rel_tol=1e-11))

    def test_explicit_parallel_up_is_rejected_in_both_directions(self):
        for normal,up in itertools.product(([0,0,1],[0,0,-1]),([0,0,1],[0,0,-1],[0,0,2])):
            with self.subTest(normal=normal,up=up):
                data=load()
                data['sections']=[{'origin':[4,3,1.5],'normal':normal,'up':up}]
                with self.assertRaises(ValueError):
                    section(data)
        # The default, unlike an explicitly supplied parallel up, chooses a basis.
        for normal in ([0,0,1],[0,0,-1]):
            data=load();data['sections']=[{'origin':[4,3,1.5],'normal':normal}]
            self.assertAlmostEqual(math.hypot(*section(data).u),1)

    def test_remote_origin_in_oblique_plane_keeps_the_original_world_equation(self):
        for distance in (0.,1e6,1e12,1e16):
            with self.subTest(distance=distance):
                data=load()
                data['sections']=[{'origin':[distance,distance,1.5],'normal':[1,-1,0]}]
                cut=section(data)
                for q in cut.polygon:
                    point=cut.body.world(cut.point(q))
                    self.assertAlmostEqual(point[0]-point[1],0,places=10)

    def test_malformed_section_lists_and_vectors_are_never_silently_defaulted(self):
        for value in (None,False,True,0,1,'',{},[],[None],[{}],[{}]*5):
            with self.subTest(value=value):
                data=load();data['sections']=value
                with self.assertRaises(ValueError):
                    section(data)
        for key,value in itertools.product(('normal','origin','up'),(None,True,0,'1,2,3',[],[1,2],[1,2,3,4],[True,0,1],[0,math.inf,1],[0,math.nan,1])):
            with self.subTest(key=key,value=value):
                spec={'origin':[4,3,1.5],'normal':[1,2,3],'up':[0,0,1]}
                spec[key]=value
                data=load();data['sections']=[spec]
                with self.assertRaises(ValueError):
                    section(data)

    def test_control_characters_and_surrogates_in_section_names_are_rejected(self):
        for name in ('\0','x\x01y','\x0b','\ud800','\ufffe'):
            with self.subTest(name=ascii(name)):
                data=load();data['sections']=[{'name':name,'origin':[4,3,1.5],'normal':[1,2,3]}]
                with self.assertRaises(ValueError):
                    section(data)

    def test_near_parallel_thresholds_do_not_leak_nan_or_wrong_material(self):
        for epsilon in (0.,4e-15,6e-15,1e-10,9e-8,1.1e-7,1e-5):
            with self.subTest(epsilon=epsilon):
                data=load('bloque-taladrado.json')
                data['sections']=[{'origin':[4,3,1],'normal':[1,0,epsilon]}]
                if 5e-15<epsilon<1e-7:
                    with self.assertRaises(ValueError):cortes.prepare(BoredBlock(data))
                    continue
                body,cuts=cortes.prepare(BoredBlock(data));cut=cuts[0]
                for i,j in itertools.product(range(-8,9),range(-6,7)):
                    q=(i/19,j/23)
                    ratio=raw_void(body.world(cut.point(q)),data['bore'])
                    if abs(ratio-1)>1e-8:
                        self.assertEqual(cortes.contains(cut.shapes[0],q),ratio<1)
                svg=ET.tostring(cortes.section_svg(body,cuts)).decode()
                self.assertNotIn('matrix(nan',svg.lower())

    def test_parallel_cylinder_tangency_from_both_sides_at_three_scales(self):
        for factor,offset in itertools.product((1e-8,1,1e6),(1-1e-8,1.,1+1e-8)):
            with self.subTest(scale=factor,offset=offset):
                data=scaled(load('bloque-taladrado.json'),factor)
                radius=data['bore']['diameter']/2
                data['sections']=[{'origin':[data['bore']['center'][0]+radius*offset,3*factor,factor], 'normal':[1,0,0]}]
                body,cuts=cortes.prepare(BoredBlock(data));shape=cuts[0].shapes[0]
                if offset>1:
                    self.assertIsNone(shape)
                elif offset<1:
                    self.assertTrue(math.isclose(shape['halfwidth']*body.span/radius,math.sqrt(1-offset*offset),rel_tol=2e-7))
                elif shape is not None:
                    self.assertLess(shape['halfwidth']*body.span/radius,1e-7)

    def test_accepted_sliver_sections_have_nonzero_emitted_polygon_area(self):
        source={'type':'extrusion','units':'mm','profile':[[0,0],[1,0],[0,1]],'depth':1}
        for epsilon in (1e-4,1e-6,1e-8,1e-10):
            with self.subTest(epsilon=epsilon):
                data=copy.deepcopy(source)
                data['sections']=[{'origin':[1-epsilon,.5,0],'normal':[1,0,0]}]
                body,cuts=cortes.prepare(p.Model(data));root=cortes.section_svg(body,cuts)
                node=root.find('.//*[@id="section-0-body"]/'+NS+'polygon')
                points=[tuple(map(float,pair.split(','))) for pair in node.get('points').split()]
                self.assertGreater(abs(p.signed_area(points)),0)
                dim=root.find('.//*[@data-axis="v"]')
                self.assertTrue(math.isclose(float(dim.get('data-value')),epsilon,rel_tol=1e-5))

    def test_body_tangent_and_exterior_planes_cannot_create_a_section(self):
        for z in (0.,-1e-8,3.6,3.6+1e-8):
            with self.subTest(z=z):
                data=load();data['sections']=[{'origin':[4,3,z],'normal':[0,0,1]}]
                with self.assertRaises(ValueError):section(data)

    def test_permuting_bores_keeps_the_union_and_input_immutable(self):
        original=load()
        for permutation in itertools.permutations(range(4)):
            with self.subTest(permutation=permutation):
                data=copy.deepcopy(original)
                data['bores']=[data['bores'][i] for i in permutation]
                data['sections']=[{'origin':[4,3,1.5],'normal':[1,2,3]}]
                previous=copy.deepcopy(data)
                cut=section(data)
                for i,j in itertools.product(range(-5,6),range(-5,6)):
                    q=(i/25,j/25)
                    ratios=[raw_void(cut.body.world(cut.point(q)),b) for b in original['bores']]
                    if min(abs(r-1) for r in ratios)>1e-9:
                        self.assertEqual(any(cortes.contains(s,q) for s in cut.shapes),min(ratios)<1)
                self.assertEqual(data,previous)

    def test_four_duplicate_names_and_reserved_names_do_not_collide_svg_ids(self):
        data=load()
        data['sections']=[{'name':'sections-title','origin':[4,3,z],'normal':[0,0,1]} for z in (1.1,1.2,1.3,1.4)]
        body,cuts=cortes.prepare(FourBores(data));root=cortes.section_svg(body,cuts)
        ids=[n.get('id') for n in root.iter() if n.get('id')]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(root.findall('.//*[@data-section]')),4)
        self.assertEqual(len(root.findall('.//*[@data-value]')),8)


if __name__=='__main__':unittest.main()
