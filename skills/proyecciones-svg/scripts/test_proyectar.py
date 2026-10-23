"""Meaningful geometry and standalone-output checks; no external packages."""
import argparse
import copy
import contextlib
import io
import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import proyectar as p


def box():
    return p.Model({"type": "extrusion", "profile": [[0, 0], [2, 0], [2, 2], [0, 2]], "depth": 2})


class GeometryTests(unittest.TestCase):
    def test_camera_front_right_top(self):
        vertex = [(2, 3, 4)]
        for angles, expected in (((0, 0), (2, 4, -3)), ((90, 0), (3, 4, 2)), ((0, 90), (2, 3, 4))):
            for actual, target in zip(p.project(vertex, *angles)[0], expected):
                self.assertAlmostEqual(actual, target)

    def test_camera_preserves_length(self):
        point = [(0.32, -0.47, 0.69)]
        for azimuth in range(0, 360, 37):
            for elevation in (-90, -35, 0, 35, 90):
                self.assertAlmostEqual(p.length(p.project(point, azimuth, elevation)[0]), p.length(point[0]))

    def test_hidden_interval_is_only_the_covered_part(self):
        tri = [(-0.5, -1, 1), (0.5, -1, 1), (0, 1, 1)]
        result = p.occluded_interval((-1, 0, 0), (1, 0, 0), tri)
        self.assertAlmostEqual(result[0], 0.375)
        self.assertAlmostEqual(result[1], 0.625)

    def test_behind_or_coplanar_faces_do_not_hide(self):
        for depth in (-1, 0):
            tri = [(-0.5, -1, depth), (0.5, -1, depth), (0, 1, depth)]
            self.assertIsNone(p.occluded_interval((-1, 0, 0), (1, 0, 0), tri))

    def test_depth_crossing_splits_an_edge(self):
        tri = [(-0.5, -1, 0), (0.5, -1, 0), (0, 1, 0)]
        result = p.occluded_interval((-1, 0, -1), (1, 0, 1), tri)
        self.assertAlmostEqual(result[0], 0.375)
        self.assertAlmostEqual(result[1], 0.5, places=6)

    def test_cube_hidden_and_visible_projected_lengths(self):
        model = box()
        result = p.edge_segments(model, p.project(model.vertices, 45, math.degrees(math.asin(1/math.sqrt(3)))))
        total = lambda kind: sum(math.dist(a, b) for a, b in result[kind])
        self.assertAlmostEqual(total("visible"), 9*math.sqrt(2/3), places=5)
        self.assertAlmostEqual(total("hidden"), 3*math.sqrt(2/3), places=5)

    def test_concave_extrusion_triangulation_and_volume(self):
        profile = [[0, 0], [8, 0], [8, 5], [7, 5], [7, 1], [1, 1], [1, 5], [0, 5]]
        model = p.Model({"type": "extrusion", "profile": profile, "depth": 3})
        volume = sum(p.dot(model.vertices[a], p.cross(model.vertices[b], model.vertices[c])) for a, b, c in model.triangles)/6
        self.assertAlmostEqual(abs(volume)*model.span**3, 48)
        self.assertEqual(len(model.edges), 24)
        # A notch midpoint is not covered by either front or back face.
        projection = p.project(model.vertices, 0, 0)
        x = (4-4)/8
        z = (3-2.5)/8
        line = ((x-0.01, z, -2), (x+0.01, z, -2))
        for tri in model.triangles[:12]:
            self.assertIsNone(p.occluded_interval(*line, [projection[i] for i in tri]))

    def test_coplanar_triangle_diagonal_is_not_a_feature(self):
        model = box()
        faces = copy.deepcopy(model.faces)
        face = faces.pop(0)
        faces.extend([[face[0], face[1], face[2]], [face[0], face[2], face[3]]])
        result = p.Model({"type": "mesh", "vertices": [list(v) for v in model.vertices], "faces": faces})
        self.assertEqual(len(result.edges), 12)

    def test_translation_scaling_and_clockwise_input(self):
        original = [[0, 0], [6, 0], [6, 2], [2, 2], [2, 4], [0, 4]]
        a = p.Model({"type": "extrusion", "profile": original, "depth": 4})
        b = p.Model({"type": "extrusion", "profile": [[x*5-30, z*5-10] for x, z in reversed(original)], "depth": 20})
        self.assertEqual(sorted(a.vertices), sorted(b.vertices))

    def test_invalid_inputs_fail(self):
        inputs = [
            {"type": "extrusion", "profile": [[0, 0], [2, 2], [0, 2], [2, 0]], "depth": 1},
            {"type": "extrusion", "profile": [[0, 0], [2, 0], [2, 2]], "depth": 0},
            {"type": "extrusion", "profile": [[0, 0], [2, 0], [2, float('nan')]], "depth": 2},
            {"type": "mesh", "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], "faces": [[0, 2, 1], [0, 1, 3], [1, 2, 3]]},
        ]
        for data in inputs:
            with self.subTest(data=data), self.assertRaises(ValueError):
                p.Model(data)

    def test_nonplanar_faces_and_inconsistent_winding_fail(self):
        model = box()
        data = {"type": "mesh", "vertices": [list(v) for v in model.vertices], "faces": copy.deepcopy(model.faces)}
        data["faces"][0].reverse()
        with self.assertRaisesRegex(ValueError, "Orientación"):
            p.Model(data)
        data["faces"][0].reverse()
        data["vertices"][0][1] += 0.2
        with self.assertRaisesRegex(ValueError, "no plana"):
            p.Model(data)

    def test_projection_system_changes_positions_without_mirroring(self):
        ns = {"s": p.NS}
        for system, compare in (("third", -1), ("first", 1)):
            root = p.sheet_svg(box(), system, "dash")
            labels = {g.get("data-view"): g.find("s:text", ns) for g in root.findall("s:g", ns)}
            self.assertEqual(math.copysign(1, float(labels["Planta"].get("y"))-float(labels["Alzado"].get("y"))), compare)
            self.assertEqual(math.copysign(1, float(labels["Alzado"].get("x"))-float(labels["Perfil derecho"].get("x"))), compare)
            self.assertEqual(len(set(g.get("data-scale") for g in root.findall("s:g", ns))), 1)

    def test_animation_is_vector_only_with_consistent_smil_timing(self):
        args = argparse.Namespace(frames=12, seconds=2, sweep=360, azimuth=45, elevation=35, hidden="omit", loop=True)
        root = p.animation_svg(box(), args)
        xml = ET.tostring(root, encoding="unicode")
        for forbidden in ("<image", "<script", "<foreignObject", "<video", "<canvas"):
            self.assertNotIn(forbidden, xml)
        ns = {"s": p.NS}
        groups = [g for g in root.iter(f"{{{p.NS}}}g") if g.get("data-frame") is not None]
        self.assertEqual(len(groups), 12)
        for g in groups:
            anim = g.find("s:animate", ns)
            times = list(map(float, anim.get("keyTimes").split(';')))
            self.assertEqual(len(times), len(anim.get("values").split(';')))
            self.assertEqual(times, sorted(times))
            self.assertEqual((times[0], times[-1]), (0, 1))
        for index in range(12):
            time = (index+0.5)/12
            active = []
            for g in groups:
                anim = g.find("s:animate", ns)
                values = anim.get("values").split(';')
                times = list(map(float, anim.get("keyTimes").split(';')))
                value = values[max(i for i, t in enumerate(times) if t <= time)]
                if value == 'visible':
                    active.append(int(g.get("data-frame")))
            self.assertEqual(active, [index])

    def test_cli_preserves_existing_files_and_invalid_models_create_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            model_file = work/"modelo.json"
            model_file.write_text(json.dumps({"type": "extrusion", "profile": [[0, 0], [2, 0], [2, 1]], "depth": 1}), encoding="utf-8")
            output = work/"salida"
            arguments = [str(model_file), "--output-dir", str(output), "--mode", "all", "--frames", "8"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(p.main(arguments), 0)
            files = {file.name: file.read_bytes() for file in output.iterdir()}
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                p.main(arguments)
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(files, {file.name: file.read_bytes() for file in output.iterdir()})
            model_file.write_text('{"type":"extrusion","profile":[],"depth":1}', encoding="utf-8")
            invalid_output = work/"no-debe-crearse"
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                p.main([str(model_file), "--output-dir", str(invalid_output)])
            self.assertFalse(invalid_output.exists())


if __name__ == "__main__":
    unittest.main()
