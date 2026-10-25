"""Section regressions against raw solid/cylinder equations, at physical scales."""
import copy
import json
import math
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import cortes
import proyectar as p
from cuatro_taladros import FourBores
from pieza_taladrada import SlopedBore
from taladro_cilindrico import BoredBlock
from test_escalas import scaled

ASSETS = Path(__file__).resolve().parent.parent/'assets'
SCALES = (1e-8, 1e-5, 1., 1e6)


def load(name='cuatro-taladros.json'):
    return json.loads((ASSETS/name).read_text(encoding='utf-8'))


def radial(point, bore):
    axis = bore.get('direction', [0, 0, 1])
    axis = [v/math.hypot(*axis) for v in axis]
    vector = [point[0]-bore['center'][0], point[1]-bore['center'][1], point[2]]
    t = sum(a*b for a, b in zip(vector, axis))
    return math.hypot(*(v-t*a for v, a in zip(vector, axis)))


def boundary(shape, theta):
    c = shape['center']
    if shape['kind'] == 'ellipse':
        return tuple(c[i]+shape['a']*math.cos(theta)*shape['major'][i]+shape['b']*math.sin(theta)*shape['minor'][i] for i in (0, 1))
    return tuple(c[i]+math.sin(theta)*shape['direction'][i]+(1 if math.cos(theta)>=0 else -1)*shape['halfwidth']*shape['normal'][i] for i in (0, 1))


class SectionTests(unittest.TestCase):
    def test_four_axis_planes_and_boundaries_against_raw_cylinders_at_all_scales(self):
        original = load()
        for factor in SCALES:
            data = scaled(original, factor)
            body, sections = cortes.prepare(FourBores(data))
            for section in sections:
                for i, shape in enumerate(section.shapes):
                    for k in range(127):
                        q = boundary(shape, math.tau*(k+.271)/127)
                        world = body.world(section.point(q))
                        self.assertTrue(math.isclose(radial(world, data['bores'][i]), data['bores'][i]['diameter']/2, rel_tol=2e-11))
                        offset = [a-b for a, b in zip(world, body.world(section.origin))]
                        self.assertLess(abs(sum(a*b for a, b in zip(offset, section.n))), body.span*1e-12)
            self.assertAlmostEqual(p.dot(sections[0].n, sections[1].n), 0)
            for section, indices in zip(sections, ((0, 1), (2, 3))):
                for i in indices:
                    self.assertEqual(section.shapes[i]['kind'], 'strip')
            self.assertEqual(original, load())

    def test_material_and_buried_boundaries_match_union_not_xor_at_all_scales(self):
        for factor in SCALES:
            data = scaled(load(), factor)
            body, sections = cortes.prepare(FourBores(data))
            for section in sections:
                count = 0
                for i in range(51):
                    for j in range(39):
                        q = ((i-25)/52, (j-19)/65)
                        world = body.world(section.point(q))
                        distances = [radial(world, b)/(b['diameter']/2) for b in data['bores']]
                        if any(abs(r-1)<1e-9 for r in distances):
                            continue
                        self.assertEqual(any(cortes.contains(s, q) for s in section.shapes), min(distances)<1)
                        count += 1
                self.assertGreater(count, 1900)
                # All four overlap at P; subtracting with even/odd fill would refill it.
                common = section.project(body.normalize((4*factor, 3*factor, 1.5*factor)))
                self.assertTrue(all(cortes.contains(s, common) for s in section.shapes))

    def test_true_lengths_and_diameters_remain_correct_and_nonzero(self):
        reference = None
        for factor in SCALES:
            body, sections = cortes.prepare(FourBores(scaled(load(), factor)))
            root = cortes.section_svg(body, sections)
            ET.fromstring(ET.tostring(root))
            dimensions = [float(n.get('data-value')) for n in root.iter() if n.get('data-value')]
            height_a = (1.5+.1*2.775+.2*8)/(1-.1*.15)*math.sqrt(1+.15**2)
            for actual, expected in zip(dimensions, (8, height_a, 6, 2.9)):
                self.assertTrue(math.isclose(actual, expected*factor, rel_tol=5e-12))
                self.assertGreater(actual, 0)
            diameters = [float(n.get('data-diameter')) for n in root.iter() if n.get('data-diameter')]
            for actual, expected in zip(diameters, (1.2, .8, .6, .4)):
                self.assertTrue(math.isclose(actual, expected*factor, rel_tol=5e-12))
            def coordinates(value):
                return tuple(map(float,value.replace('matrix(','').replace(')','').replace(',',' ').split())) if value else ()
            geometry = [(n.tag, coordinates(n.get('points')), coordinates(n.get('transform'))) for n in root.iter() if n.tag.endswith(('polygon', 'ellipse'))]
            if reference is None:
                reference = geometry
            else:
                # Normalized drawing coordinates must remain stable, including masks.
                self.assertEqual(len(geometry),len(reference))
                for actual,expected in zip(geometry,reference):
                    self.assertEqual(actual[0],expected[0])
                    for a,b in zip(actual[1:],expected[1:]):
                        self.assertEqual(len(a),len(b))
                        self.assertTrue(all(math.isclose(x,y,abs_tol=2e-9,rel_tol=2e-12) for x,y in zip(a,b)))

    def test_section_polygon_obeys_original_sloped_body_planes(self):
        for factor in SCALES:
            data = scaled(load(), factor)
            body, sections = cortes.prepare(FourBores(data))
            for section in sections:
                for q in section.polygon:
                    x, y, z = body.world(section.point(q))
                    self.assertGreaterEqual(z, -body.span*1e-12)
                    roof = data['roof']
                    self.assertLessEqual(z, roof['offset']+roof['slope_x']*x+roof['slope_y']*y+body.span*1e-12)
                    for a, b in zip(data['footprint'], data['footprint'][1:]+data['footprint'][:1]):
                        distance = ((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/math.dist(a, b)
                        self.assertGreaterEqual(distance, -body.span*1e-12)

    def test_custom_oblique_sections_and_unit_conversion(self):
        data = load()
        data['sections'] = [{'name':'Oblicuo', 'origin':[4, 3, 1.2], 'normal':[1, 2, 3]},
                            {'name':'Horizontal', 'origin':[4, 3, 1.5], 'normal':[0, 0, 1]}]
        original = copy.deepcopy(data)
        for factor in SCALES:
            source = scaled(data, factor)
            body, sections = cortes.prepare(FourBores(source))
            for section in sections:
                for bore, shape in zip(source['bores'], section.shapes):
                    self.assertEqual(shape['kind'], 'ellipse')
                    for k in range(71):
                        q = boundary(shape, math.tau*k/71)
                        self.assertTrue(math.isclose(radial(body.world(section.point(q)), bore), bore['diameter']/2, rel_tol=2e-11))
        # Same physical geometry expressed in meters, while SVG retains input units.
        meters = scaled(data, .01)
        meters['units'] = 'm'
        a, sa = cortes.prepare(FourBores(data))
        b, sb = cortes.prepare(FourBores(meters))
        self.assertEqual(len(sa[0].polygon), len(sb[0].polygon))
        for first, second in zip(sa[0].polygon, sb[0].polygon):
            self.assertLess(math.dist(first, second), 1e-12)
        self.assertEqual(json.loads(cortes.section_svg(b, sb).findtext(f'{{{p.NS}}}metadata'))['units'], 'm')
        self.assertEqual(data, original)

    def test_parallel_offset_strip_tangent_and_missing_cylinder(self):
        data = load('bloque-taladrado.json')
        data['sections'] = []
        cx, cy = data['bore']['center']
        radius = data['bore']['diameter']/2
        for offset, expected in ((0, 1), (.5, math.sqrt(.75)), (1, None), (1.1, None)):
            data['sections'] = [{'origin':[cx+radius*offset, cy, 1], 'normal':[1, 0, 0]}]
            body, sections = cortes.prepare(BoredBlock(data))
            shape = sections[0].shapes[0]
            if expected is None:
                self.assertIsNone(shape)
            else:
                self.assertEqual(shape['kind'], 'strip')
                self.assertAlmostEqual(shape['halfwidth']*body.span, radius*expected)

    def test_convex_wedge_reversed_mesh_and_single_bore(self):
        data = load('cuna.json')
        body, sections = cortes.prepare(p.Model(data))
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].shapes, [])
        raw = p.Model(data)
        mesh = {'type':'mesh', 'vertices':[[v[i]*raw.span+(raw.minimum[i]+raw.maximum[i])/2 for i in range(3)] for v in raw.vertices],
                'faces':[list(reversed(f)) for f in raw.faces]}
        other, cuts = cortes.prepare(p.Model(mesh))
        for first, second in zip(sections, cuts):
            for a, b in zip(first.polygon, second.polygon):
                self.assertLess(math.dist(a, b), 1e-12)
        for name, constructor in (('taladro-inclinado.json', SlopedBore), ('bloque-taladrado.json', BoredBlock)):
            _, cuts = cortes.prepare(constructor(load(name)))
            self.assertTrue(all(s.shapes[0]['kind']=='strip' for s in cuts))

    def test_bad_planes_empty_sections_concavity_and_near_parallel_are_rejected(self):
        cases = ([], [{}], [None], [{'origin':[4,3,1.5], 'normal':[0,0,0]}],
                 [{'origin':[4,3,100], 'normal':[0,0,1]}], [{'origin':[0,0,0], 'normal':[0,0,1]}],
                 [{'origin':[4,3,1.5], 'normal':[0,1,-.15+1e-10]}],
                 [{'origin':[4,3,1.5], 'normal':[1,0,0], 'up':[0,0,0]}],
                 [{'origin':[4,3,math.nan], 'normal':[0,1,0]}], [{'name':'x'*81, 'origin':[4,3,1.5], 'normal':[0,1,0]}])
        for specs in cases:
            data = load()
            data['sections'] = specs
            with self.subTest(specs=specs), self.assertRaises(ValueError):
                cortes.prepare(FourBores(data))
        with self.assertRaisesRegex(ValueError, 'cóncavo'):
            cortes.prepare(p.Model(load('escalon.json')))

    def test_svg_masks_are_a_union_and_references_are_complete(self):
        body, cuts = cortes.prepare(FourBores(load()))
        root = cortes.section_svg(body, cuts)
        ids = {n.get('id') for n in root.iter() if n.get('id')}
        for node in root.iter():
            for value in node.attrib.values():
                if 'url(#' in value:
                    self.assertIn(value.split('url(#')[1].split(')')[0], ids)
        for i in range(2):
            mask = root.find(f'.//*[@id="section-{i}-material"]')
            self.assertEqual(len(mask), 5)  # white rectangle, four black voids: union, never XOR
            self.assertTrue(all(n.get('fill')=='black' for n in list(mask)[1:]))
            for j in range(4):
                self.assertEqual(len(root.find(f'.//*[@id="section-{i}-other-{j}"]')), 4)


if __name__ == '__main__':
    unittest.main()
