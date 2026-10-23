import copy
import math
import unittest

import proyectar as p


def beam(width=40000):
    return {'type':'extrusion','units':'mm','profile':[[0,0],[width,0],[width,1],[0,1]],'depth':1}


class SlenderTests(unittest.TestCase):
    def test_valid_slender_beam_has_correct_volume_and_closed_features(self):
        for width in (40000,1e6):
            for factor in (1e-8,1,1e6):
                data=beam(width)
                data['profile']=[[x*factor,z*factor] for x,z in data['profile']]
                data['depth']*=factor
                model=p.Model(data)
                volume=math.fsum(p.dot(model.vertices[a],p.cross(model.vertices[b],model.vertices[c])) for a,b,c in model.triangles)/6*model.span**3
                self.assertTrue(math.isclose(abs(volume),width*factor**3,rel_tol=1e-8))
                self.assertEqual(len(model.edges),12)
                self.assertEqual(len(model.faces),6)
                self.assertEqual(len(model.triangles),12)

    def test_too_slender_shape_has_explicit_numerical_limit_error(self):
        with self.assertRaisesRegex(ValueError,'proporción.*límite numérico'):
            p.Model(beam(1e6+1))

    def test_degenerate_and_nonplanar_faces_still_fail(self):
        with self.assertRaises(ValueError):
            p.Model({'type':'extrusion','profile':[[0,0],[1,0],[2,0]],'depth':1})
        model=p.Model(beam())
        data={'type':'mesh','vertices':[list(v) for v in model.vertices],'faces':copy.deepcopy(model.faces)}
        data['vertices'][0][1]+=1e-6
        with self.assertRaises(ValueError):
            p.Model(data)

    def test_resource_bounds_reject_input_before_triangulation(self):
        with self.assertRaisesRegex(ValueError,'hasta 64'):
            p.Model({'type':'extrusion','profile':[[i,0] for i in range(65)],'depth':1})
        with self.assertRaisesRegex(ValueError,'hasta 256'):
            p.Model({'type':'mesh','vertices':[[0,0,0]]*257,'faces':[]})

    def test_small_faces_still_occlude_after_uniform_scaling(self):
        for factor in (1e-8,1e-6,1,1e6):
            scale=lambda v: tuple(x*factor for x in v)
            triangle=[scale(v) for v in ((-1,-1,1),(1,-1,1),(0,1,1))]
            interval=p.occluded_interval(scale((-.1,0,0)),scale((.1,0,0)),triangle)
            self.assertEqual(interval,(0.0,1.0))


if __name__=='__main__':
    unittest.main()
