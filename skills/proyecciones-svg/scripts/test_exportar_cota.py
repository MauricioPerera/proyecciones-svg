"""Physical geometry invariants of the optional Cota interchange format."""
import copy
import json
import math
from pathlib import Path
import unittest

from exportar_cota import document, millimeters_per_unit

ASSETS = Path(__file__).resolve().parent.parent/'assets'


def load(name):
    return json.loads((ASSETS/name).read_text(encoding='utf-8'))


class CotaExportTests(unittest.TestCase):
    def test_wedge_preserves_physical_dimensions_and_source(self):
        source = load('cuna.json')
        previous = copy.deepcopy(source)
        result = document(source,'first')
        props = result['entities'][0]['props']
        self.assertEqual(result['units'],'mm')
        self.assertEqual(result['vars']['VIEWPROJECTION'],'first')
        self.assertEqual(props['op'],'EXTRUDE')
        self.assertEqual(props['axis'],[0,1,0])
        self.assertEqual(props['height'],40)
        self.assertEqual(props['profile'],[[0,0,0],[60,0,0],[60,0,30]])
        self.assertEqual(source,previous)
        self.assertEqual(result,document(source,'first'))

    def test_all_examples_have_exportable_native_geometry(self):
        for path in ASSETS.glob('*.json'):
            with self.subTest(name=path.name):
                data = json.loads(path.read_text(encoding='utf-8'))
                result = document(data)
                self.assertEqual(result['schemaVersion'],1)
                self.assertEqual(result['entities'][0]['type'],'SOLID3D')
                self.assertEqual(result['meta']['custom']['source_type'],data['type'])
                json.dumps(result,allow_nan=False)

    def test_four_bores_preserve_axes_radii_and_clear_both_caps(self):
        source = load('cuatro-taladros.json')
        props = document(source)['entities'][0]['props']
        self.assertEqual(props['op'],'SUBTRACT')
        self.assertEqual(len(props['operands']),5)
        body,*cutters = props['operands']
        self.assertEqual(body['op'],'INTERSECT')
        prism,clip = body['operands']
        bottom = prism['profile']
        top = [[10*x,10*y,15+2*x+y] for x,y in source['footprint']]
        u,v = clip['basis']['x'],clip['basis']['y']
        n = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        for (x,y),low,high in zip(source['footprint'],bottom,top):
            self.assertEqual(low,[10*x,10*y,0])
            roof_distance = sum((a-b)*c for a,b,c in zip(high,clip['origin'],n))
            self.assertAlmostEqual(roof_distance,clip['height'])
            for vertex in (low,high):
                local = [a-b for a,b in zip(vertex,clip['origin'])]
                self.assertGreater(sum(a*b for a,b in zip(local,u)),0)
                self.assertLess(sum(a*b for a,b in zip(local,u)),clip['width'])
                self.assertGreater(sum(a*b for a,b in zip(local,v)),0)
                self.assertLess(sum(a*b for a,b in zip(local,v)),clip['depth'])
        for bore,cutter in zip(source['bores'],cutters):
            length = math.hypot(*bore['direction'])
            self.assertEqual(cutter['op'],'CYLINDER')
            self.assertAlmostEqual(cutter['radius'],bore['diameter']*5)
            for given,actual in zip(bore['direction'],cutter['axis']):
                self.assertAlmostEqual(actual,given/length)
            point = [bore['center'][0]*10,bore['center'][1]*10,0]
            offset = [p-b for p,b in zip(point,cutter['base'])]
            t = sum(v*a for v,a in zip(offset,cutter['axis']))
            self.assertLess(math.dist(offset,[t*a for a in cutter['axis']]),1e-10)
            for vertex in bottom+top:
                along = sum((v-b)*a for v,b,a in zip(vertex,cutter['base'],cutter['axis']))
                self.assertGreater(along,0)
                self.assertLess(along,cutter['height'])

    def test_clockwise_footprint_exports_ccw_extrusion(self):
        source = load('cuatro-taladros.json')
        source['footprint'].reverse()
        bottom = document(source)['entities'][0]['props']['operands'][0]['operands'][0]['profile']
        area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(bottom,bottom[1:]+bottom[:1]))
        self.assertGreater(area,0)

    def test_same_physical_piece_in_meters_and_centimeters_exports_same_geometry(self):
        source = load('cuatro-taladros.json')
        meters = copy.deepcopy(source)
        meters['units'] = 'm'
        meters['footprint'] = [[v/100 for v in p] for p in meters['footprint']]
        meters['roof']['offset'] /= 100
        for bore in meters['bores']:
            bore['center'] = [v/100 for v in bore['center']]
            bore['diameter'] /= 100
        def compare(a,b):
            if isinstance(a,dict):
                self.assertEqual(set(a),set(b))
                for key in a: compare(a[key],b[key])
            elif isinstance(a,list):
                self.assertEqual(len(a),len(b))
                for x,y in zip(a,b): compare(x,y)
            elif isinstance(a,(int,float)):
                self.assertAlmostEqual(a,b,places=10)
            else:
                self.assertEqual(a,b)
        compare(document(source)['entities'],document(meters)['entities'])

    def test_micrometer_geometry_is_converted_to_mm_without_changing_svg_units(self):
        source = {'type':'extrusion','units':'m','profile':[[0,0],[6e-6,0],[6e-6,3e-6]],'depth':4e-6}
        props = document(source)['entities'][0]['props']
        self.assertAlmostEqual(props['profile'][2][0],0.006)
        self.assertAlmostEqual(props['profile'][2][2],0.003)
        self.assertAlmostEqual(props['height'],0.004)
        self.assertEqual(source['units'],'m')
        self.assertEqual(millimeters_per_unit('µm'),0.001)
        self.assertEqual(millimeters_per_unit('μm'),0.001)

    def test_relative_units_require_an_explicit_equivalence(self):
        source = load('cuna.json')
        source['units'] = 'u'
        with self.assertRaisesRegex(ValueError,'cota-unit-mm'):
            document(source)
        self.assertEqual(document(source,unit_mm=2)['entities'][0]['props']['height'],8)
        for factor in (0,-1,math.nan,math.inf):
            with self.subTest(factor=factor),self.assertRaises(ValueError):
                document(source,unit_mm=factor)

    def test_concave_mesh_faces_are_triangulated_with_outward_orientation(self):
        from proyectar import Model
        from proyectar import cross,dot
        # An L profile of area 3 extruded by 2 has volume 6. Model normalizes it
        # by a span of 2, so this fixture's coordinates enclose volume 6/8.
        base = Model({'type':'extrusion','profile':[[0,0],[2,0],[2,1],[1,1],[1,2],[0,2]],'depth':2})
        source = {'type':'mesh','units':'mm','vertices':[list(v) for v in base.vertices],'faces':base.faces}
        for reverse in (False,True):
            if reverse:
                source['faces'] = [list(reversed(face)) for face in source['faces']]
            result = document(source)['entities'][0]
            self.assertEqual(result['type'],'MESH3D')
            mesh = result['props']
            self.assertTrue(all(len(face)==3 for face in mesh['faces']))
            volume = sum(dot(mesh['vertices'][a],cross(mesh['vertices'][b],mesh['vertices'][c]))
                         for a,b,c in mesh['faces'])/6
            self.assertAlmostEqual(volume,0.75)


if __name__ == '__main__':
    unittest.main()
