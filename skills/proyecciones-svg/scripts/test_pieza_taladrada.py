import argparse
import math
import unittest

import pieza_taladrada as s
import proyectar as p


def model():
    return s.SlopedBore({"type":"sloped_prism_with_bore",
                        "footprint":[[0,0],[7,0],[8,1.5],[8,5],[6,6],[0,6]],
                        "roof":{"offset":1.5,"slope_x":.2,"slope_y":.1},
                        "bore":{"axis":"z","center":[4,3],"diameter":3,"through":True}})


def ray_hits_material(m, origin, direction):
    """Independent half-space slab + quadratic cylinder ray oracle."""
    point = m.normalized(origin)
    lo, hi = 1e-7, math.inf
    for face, normal in zip(m.body.faces, m.body.normals):
        distance = p.dot(normal, p.sub(point, m.body.vertices[face[0]]))
        speed = p.dot(normal, direction)
        if abs(speed) < 1e-11:
            if distance > 1e-9:
                return False
        elif speed > 0:
            hi = min(hi, -distance/speed)
        else:
            lo = max(lo, -distance/speed)
        if hi-lo <= 1e-9:
            return False
    cx = (m.cx-m.center[0])/m.span
    cy = (m.cy-m.center[1])/m.span
    x, y = point[0]-cx, point[1]-cy
    a = direction[0]**2+direction[1]**2
    b = 2*(x*direction[0]+y*direction[1])
    c = x*x+y*y-(m.radius/m.span)**2
    if a < 1e-20:
        return c > 1e-10
    discriminant = b*b-4*a*c
    if discriminant < 0:
        return True
    near = (-b-math.sqrt(discriminant))/(2*a)
    far = (-b+math.sqrt(discriminant))/(2*a)
    return lo < near-1e-9 or hi > far+1e-9


class SlopedBoreTests(unittest.TestCase):
    def test_exact_plane_cylinder_intersection(self):
        m = model()
        for i in range(91):
            point = m.rim(i*2*math.pi/91)
            self.assertAlmostEqual((point[0]-m.cx)**2+(point[1]-m.cy)**2, m.radius**2)
            self.assertAlmostEqual(point[2], m.offset+m.ax*point[0]+m.by*point[1])

    def test_top_rim_visibility_against_solid_ray_oracle(self):
        m = model()
        for azimuth in (0,37,90,177,270,329):
            for elevation in (0,5,15,35,50,75,90):
                visible = s.roof_facing(m, azimuth, elevation) > p.EPS
                direction = p.camera(azimuth, elevation)[2]
                for i in range(61):
                    theta = 2*math.pi*(i+.21)/61
                    self.assertEqual(not ray_hits_material(m, m.rim(theta), direction), visible,
                                     (azimuth,elevation,theta))

    def test_bottom_arcs_against_solid_ray_oracle(self):
        m = model()
        for azimuth in (0,37,90,177,270,329):
            for elevation in (0,5,15,35,50,75,90):
                arc = s.bottom_visible_arc(m, azimuth, elevation)
                direction = p.camera(azimuth,elevation)[2]
                for i in range(61):
                    theta = 2*math.pi*(i+.37)/61
                    visible = arc is not None and ((theta-arc[0]) % (2*math.pi) <= arc[1]-arc[0]+1e-10)
                    self.assertEqual(not ray_hits_material(m, m.rim(theta,False), direction), visible,
                                     (azimuth,elevation,theta))

    def test_affine_svg_ellipse_matches_projected_spatial_rim(self):
        m = model()
        mapping = lambda v:(120+80*v[0],150-80*v[1])
        for azimuth in (0,45,90,217):
            for elevation in (0,30,50,90):
                a,b,c,d,e,f = s.ellipse_matrix(m,azimuth,elevation,mapping)
                for i in range(31):
                    theta = i*2*math.pi/31
                    expected = mapping(p.project([m.normalized(m.rim(theta))],azimuth,elevation)[0])
                    actual = (a*math.cos(theta)+c*math.sin(theta)+e,b*math.cos(theta)+d*math.sin(theta)+f)
                    for value,target in zip(actual,expected):
                        self.assertAlmostEqual(value,target)

    def test_svg_cap_visibility_is_different_between_front_and_right(self):
        root = s.sheet(model(),"third","dash")
        ns = {"s":p.NS}
        groups = {g.get('data-view'):g for g in root.findall('s:g',ns) if g.get('data-view')}
        self.assertIsNotNone(groups['Alzado'].find('.//s:circle[@data-feature="top-rim"]',ns))
        self.assertIsNone(groups['Perfil derecho'].find('.//s:circle[@data-feature="top-rim"]',ns))
        self.assertIsNotNone(groups['Perfil derecho'].find('.//s:circle[@data-feature="top-rim-hidden"]',ns))
        top = groups['Planta'].find('.//s:circle[@data-feature="top-rim"]',ns)
        self.assertIsNotNone(top)
        matrix = list(map(float,top.get('transform')[7:-1].split()))
        self.assertAlmostEqual(abs(matrix[0]),abs(matrix[3]))

    def test_convex_outer_edge_visibility_is_unchanged_by_internal_bore(self):
        m = model()
        for azimuth in (0,45,90,160,235,310):
            for elevation in (0,25,50,90):
                toward = p.camera(azimuth,elevation)[2]
                projected = p.project(m.body.vertices,azimuth,elevation)
                triangles = [[projected[i] for i in triangle] for triangle in m.body.triangles]
                for i,j in m.body.edges:
                    intervals = p.merge_intervals([interval for tri in triangles
                                                  if (interval:=p.occluded_interval(projected[i],projected[j],tri)) is not None])
                    if math.hypot(projected[i][0]-projected[j][0],projected[i][1]-projected[j][1])<1e-8:
                        continue
                    for fraction in (.19,.51,.83):
                        point = tuple(m.body.vertices[i][k]+fraction*(m.body.vertices[j][k]-m.body.vertices[i][k]) for k in range(3))
                        world = tuple(point[k]*m.span+m.center[k] for k in range(3))
                        hidden = any(lo-1e-9<=fraction<=hi+1e-9 for lo,hi in intervals)
                        self.assertEqual(ray_hits_material(m,world,toward),hidden,(azimuth,elevation,i,j,fraction))

    def test_invalid_footprint_roof_or_bore_fail(self):
        data = model().body.data
        for change in ({'footprint':[[0,0],[8,0],[4,1],[8,6],[0,6]]},
                       {'roof':{'offset':-1,'slope_x':.2,'slope_y':.1}},
                       {'bore':{'axis':'z','center':[.5,3],'diameter':3,'through':True}}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                s.SlopedBore({**data,**change})

    def test_animation_clip_ids_and_arc_paths(self):
        args = argparse.Namespace(frames=12,seconds=2,sweep=360,azimuth=45,elevation=50,hidden='dash',loop=True)
        root = s.animation(model(),args)
        clips = list(root.iter(f'{{{p.NS}}}clipPath'))
        self.assertEqual(len(clips),13)
        self.assertEqual(len({node.get('id') for node in clips}),13)
        arcs = [node for node in root.iter(f'{{{p.NS}}}path') if node.get('data-feature')=='bottom-rim-visible']
        self.assertEqual(len(arcs),13)
        self.assertTrue(all(' A1,1 ' in node.get('d') for node in arcs))


if __name__=='__main__':
    unittest.main()
