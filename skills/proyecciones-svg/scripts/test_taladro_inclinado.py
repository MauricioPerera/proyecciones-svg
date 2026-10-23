import argparse
import copy
import math
import unittest

import pieza_taladrada as s
import proyectar as p


def model(direction=(.5,.25,1), center=(3.4,2.6)):
    return s.SlopedBore({"type":"sloped_prism_with_bore",
        "footprint":[[0,0],[7,0],[8,1.5],[8,5],[6,6],[0,6]],
        "roof":{"offset":1.5,"slope_x":.2,"slope_y":.1},
        "bore":{"axis":"inclined","direction":list(direction),"center":list(center),"diameter":3,"through":True}})


def ray_hits_material(m, origin, direction):
    """Clip independently against the outer convex hull and an infinite cylinder."""
    point = m.normalized(origin)
    lo, hi = 1e-7, math.inf
    for face, normal in zip(m.body.faces, m.body.normals):
        distance = p.dot(normal, p.sub(point, m.body.vertices[face[0]]))
        speed = p.dot(normal, direction)
        if abs(speed)<1e-11:
            if distance>1e-9:
                return False
        elif speed>0:
            hi=min(hi,-distance/speed)
        else:
            lo=max(lo,-distance/speed)
        if hi-lo<=1e-9:
            return False
    relative=p.sub(point,m.normalized((m.cx,m.cy,0)))
    dot_origin=p.dot(relative,m.axis)
    radial=tuple(relative[k]-dot_origin*m.axis[k] for k in range(3))
    dot_speed=p.dot(direction,m.axis)
    speed=tuple(direction[k]-dot_speed*m.axis[k] for k in range(3))
    a=p.dot(speed,speed)
    b=2*p.dot(radial,speed)
    c=p.dot(radial,radial)-(m.radius/m.span)**2
    if a<1e-20:
        return c>1e-10
    discriminant=b*b-4*a*c
    if discriminant<0:
        return True
    near=(-b-math.sqrt(discriminant))/(2*a)
    far=(-b+math.sqrt(discriminant))/(2*a)
    return lo<near-1e-9 or hi>far+1e-9


class InclinedBoreTests(unittest.TestCase):
    def test_rims_are_exact_plane_cylinder_intersections(self):
        for direction,center in (((.5,.25,1),(3.4,2.6)),((-.5,.15,1),(4.5,2.8)),((0,0,1),(4,3))):
            m=model(direction,center)
            for top in (False,True):
                for i in range(97):
                    point=m.rim(2*math.pi*i/97,top)
                    relative=p.sub(point,(m.cx,m.cy,0))
                    radial=tuple(relative[k]-p.dot(relative,m.axis)*m.axis[k] for k in range(3))
                    self.assertAlmostEqual(p.dot(radial,radial),m.radius**2)
                    self.assertAlmostEqual(point[2],m.height(*point[:2]) if top else 0)

    def test_visibility_against_ray_solid_oracle(self):
        for direction,center in (((.5,.25,1),(3.4,2.6)),((-.5,.15,1),(4.5,2.8))):
            m=model(direction,center)
            for azimuth in range(0,360,15):
                for elevation in (3,10,25,50,75,90):
                    view=p.camera(azimuth,elevation)[2]
                    arc=s.bottom_visible_arc(m,azimuth,elevation)
                    for i in range(73):
                        theta=2*math.pi*(i+.317)/73
                        visible=arc is not None and (theta-arc[0])%(2*math.pi)<=arc[1]-arc[0]+1e-10
                        self.assertEqual(visible,not ray_hits_material(m,m.rim(theta,False),view),(direction,azimuth,elevation,theta))
                        self.assertEqual(s.roof_facing(m,azimuth,elevation)>p.EPS,
                            not ray_hits_material(m,m.rim(theta),view),(direction,azimuth,elevation,theta,'top'))

    def test_affine_ellipses_match_world_projection(self):
        m=model()
        for azimuth in (0,45,90,180,273):
            for elevation in (0,25,50,90):
                for top in (False,True):
                    mapping=lambda v:(300+230*v[0],210-230*v[1])
                    a,b,c,d,e,f=s.ellipse_matrix(m,azimuth,elevation,mapping,top)
                    for i in range(31):
                        t=i*2*math.pi/31
                        actual=(a*math.cos(t)+c*math.sin(t)+e,b*math.cos(t)+d*math.sin(t)+f)
                        target=mapping(p.project([m.normalized(m.rim(t,top))],azimuth,elevation)[0])
                        for x,y in zip(actual,target):
                            self.assertAlmostEqual(x,y)

    def test_top_view_has_elliptic_shifted_bores_and_projected_axis(self):
        m=model()
        root=s.sheet(m,'third','dash')
        ns={'s':p.NS}
        top=next(g for g in root.findall('s:g',ns) if g.get('data-view')=='Planta')
        rim=top.find('.//s:circle[@data-feature="top-rim"]',ns)
        matrix=list(map(float,rim.get('transform')[7:-1].split()))
        self.assertGreater(abs(math.hypot(matrix[0],matrix[1])-math.hypot(matrix[2],matrix[3])),1)
        axis=top.find('.//s:path[@data-feature="bore-axis"]',ns)
        self.assertIsNotNone(axis)
        self.assertNotAlmostEqual(m.rim_centers[True][0],m.rim_centers[False][0])
        self.assertNotAlmostEqual(m.rim_centers[True][1],m.rim_centers[False][1])

    def test_axis_view_is_circular_and_suppresses_coincident_bottom_curve(self):
        m=model()
        az=math.degrees(math.atan2(m.axis[0],-m.axis[1]))
        el=math.degrees(math.asin(m.axis[2]))
        mapping=lambda v:(100+200*v[0],100-200*v[1])
        matrix=s.ellipse_matrix(m,az,el,mapping)
        a,b,c,d,_,_=matrix
        self.assertAlmostEqual(math.hypot(a,b),math.hypot(c,d))
        self.assertAlmostEqual(a*c+b*d,0)
        root=s.view(m,argparse.Namespace(azimuth=az,elevation=el,hidden='dash'))
        self.assertIsNone(root.find('.//{'+p.NS+'}path[@data-feature="bottom-rim-visible"]'))

    def test_rejects_side_breakouts_and_invalid_axes(self):
        source=model().body.data
        for change in ({'direction':[0,0,0]},{'direction':[1,0,0]},{'direction':[.5,0,-1]},
                       {'direction':[10,0,1]},{'center':[.7,2.6]},
                       {'axis':'z','direction':[.5,0,1]}):
            data=copy.deepcopy(source);data['bore'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                s.SlopedBore(data)

    def test_hidden_line_omission_and_finite_svg(self):
        root=s.animation(model(),argparse.Namespace(frames=24,seconds=2,sweep=360,azimuth=45,elevation=50,hidden='omit',loop=True))
        for node in root.iter():
            self.assertNotIn('hidden-edge',node.get('class',''))
            for value in node.attrib.values():
                self.assertNotIn('nan',value.lower())
                self.assertNotIn('inf',value.lower().replace('indefinite',''))


if __name__=='__main__':
    unittest.main()
