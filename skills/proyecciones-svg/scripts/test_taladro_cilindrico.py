import argparse
import math
import unittest
import xml.etree.ElementTree as ET

import proyectar as p
import taladro_cilindrico as t


def block(height=2):
    return t.BoredBlock({"type": "block_with_bore", "size": [8, 6, height],
                         "bore": {"axis": "z", "center": [4, 3], "diameter": 3, "through": True}})


class AnalyticBoreTests(unittest.TestCase):
    def test_bottom_visibility_agrees_with_independent_ray_exit(self):
        b = block()
        for azimuth in (0, 37, 90, 177, 270):
            for elevation in (10, 30, 45, 70, 90):
                arc = t.bottom_visible_arc(b, azimuth, elevation)
                a, e = math.radians(azimuth), math.radians(elevation)
                direction = (math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e))
                time = b.height/direction[2]
                for i in range(180):
                    theta = 2*math.pi*(i+0.23)/180
                    x = b.radius*math.cos(theta)+time*direction[0]
                    y = b.radius*math.sin(theta)+time*direction[1]
                    expected = x*x+y*y <= b.radius*b.radius+1e-10
                    actual = arc is not None and ((theta-arc[0]) % (2*math.pi) <= arc[1]-arc[0]+1e-10)
                    self.assertEqual(actual, expected, (azimuth, elevation, theta))

    def test_deep_bore_has_no_visible_lower_rim_at_low_elevation(self):
        self.assertIsNone(t.bottom_visible_arc(block(10), 45, 30))
        self.assertEqual(t.bottom_visible_arc(block(), 45, 90), (0, 2*math.pi))

    def test_projected_circle_is_an_exact_ellipse(self):
        b = block()
        for azimuth in (0, 45, 123, 270):
            for elevation in (15, 45, 75, 90):
                center = p.project([b.normalized((b.cx, b.cy, b.height))], azimuth, elevation)[0]
                radius = b.radius/b.span
                for i in range(31):
                    theta = i*2*math.pi/31
                    point = p.project([b.rim(theta, b.height)], azimuth, elevation)[0]
                    residual = ((point[0]-center[0])/radius)**2+((point[1]-center[1])/(radius*math.sin(math.radians(elevation))))**2
                    self.assertAlmostEqual(residual, 1)

    def test_sheet_has_circle_and_two_hidden_limits_per_side(self):
        root = t.sheet(block(), "third", "dash")
        ns = {"s": p.NS}
        groups = {g.get("data-view"): g for g in root.findall("s:g", ns) if g.get("data-view")}
        circle = groups["Planta"].find('.//s:ellipse[@data-feature="top-rim"]', ns)
        self.assertIsNotNone(circle)
        self.assertEqual(circle.get("rx"), circle.get("ry"))
        for name in ("Alzado", "Perfil derecho"):
            self.assertEqual(len(groups[name].findall('.//s:path[@data-feature="bore-generator"]', ns)), 2)
        self.assertIn("Ø 3", ''.join(node.text or '' for node in root.iter(f'{{{p.NS}}}text')))

    def test_bore_clip_ids_are_unique_and_output_is_vector_only(self):
        args = argparse.Namespace(frames=16, seconds=2, sweep=360, azimuth=45, elevation=45, hidden="dash", loop=True)
        root = t.animation(block(), args)
        clips = list(root.iter(f'{{{p.NS}}}clipPath'))
        self.assertEqual(len(clips), 17)
        self.assertEqual(len({node.get('id') for node in clips}), 17)
        xml = ET.tostring(root, encoding="unicode")
        for forbidden in ('<image', '<script', '<foreignObject', '<video', '<canvas'):
            self.assertNotIn(forbidden, xml)
        self.assertEqual(len(list(root.iter(f'{{{p.NS}}}animate'))), 16)

    def test_unsupported_axis_and_open_side_are_rejected(self):
        for bore in ({"axis":"x","center":[4,3],"diameter":3,"through":True},
                     {"axis":"z","center":[4,3],"diameter":6,"through":True},
                     {"axis":"z","center":[4,3],"diameter":3,"through":False}):
            with self.subTest(bore=bore), self.assertRaises(ValueError):
                t.BoredBlock({"type":"block_with_bore","size":[8,6,2],"bore":bore})


if __name__ == '__main__':
    unittest.main()
