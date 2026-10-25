"""Independent format readers check physical geometry, units and precision."""
import copy
import io
import json
import math
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET
import zipfile
from unittest.mock import patch

import proyectar as p
from exportar_mallas import prepare, glb, stl, three_mf, validate_mesh, float32_vertices
from test_escalas import scaled

ASSETS=Path(__file__).resolve().parent.parent/'assets'
MF='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'


def load(name='modulos/rampa.json'):
    return json.loads((ASSETS/name).read_text(encoding='utf-8'))


def volume(triangles):
    return math.fsum(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]) for a,b,c in triangles)/6


def read_glb(raw):
    magic,version,length=struct.unpack_from('<III',raw)
    assert magic==0x46546c67 and version==2 and length==len(raw)
    size,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4e4f534a and size%4==0
    document=json.loads(raw[20:20+size])
    binary_size,kind=struct.unpack_from('<II',raw,20+size)
    assert kind==0x004e4942 and 28+size+binary_size==len(raw)
    binary=raw[28+size:]
    arrays=[]
    for accessor in document['accessors']:
        view=document['bufferViews'][accessor['bufferView']]
        assert accessor['componentType']==5126 and accessor['type']=='VEC3'
        start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        arrays.append([struct.unpack_from('<3f',binary,start+12*i) for i in range(accessor['count'])])
    return document,arrays


class MeshExportTests(unittest.TestCase):
    def test_three_modules_have_expected_solid_volume_and_bounds(self):
        for name,expected in (('rampa',16000),('bloque',32000),('escalera',20000)):
            with self.subTest(name=name):
                source=load('modulos/'+name+'.json');previous=copy.deepcopy(source)
                mesh=prepare(source)
                self.assertAlmostEqual(mesh.volume_mm3,expected)
                self.assertEqual(mesh.info()['bounds_mm'],[[0,0,0],[40,40,20]])
                self.assertEqual(source,previous)
                self.assertGreater(validate_mesh(mesh.vertices,mesh.triangles),0)

    def test_glb_uses_meters_y_up_and_outward_flat_normals(self):
        for name,expected in (('rampa',16000),('bloque',32000),('escalera',20000)):
            with self.subTest(name=name):
                mesh=prepare(load('modulos/'+name+'.json'))
                document,(positions,normals)=read_glb(glb(mesh))
                self.assertEqual(document['asset']['version'],'2.0')
                self.assertEqual(len(positions),len(mesh.triangles)*3)
                for actual,target in zip(document['accessors'][0]['max'],(.04,.02,0)):
                    self.assertAlmostEqual(actual,target,places=8)
                for actual,target in zip(document['accessors'][0]['min'],(0,0,-.04)):
                    self.assertAlmostEqual(actual,target,places=8)
                self.assertTrue(math.isclose(volume([positions[i:i+3] for i in range(0,len(positions),3)]),expected/1e9,rel_tol=1e-6))
                for i in range(0,len(positions),3):
                    a,b,c=positions[i:i+3];n=normals[i]
                    actual=p.cross(p.sub(b,a),p.sub(c,a))
                    self.assertGreater(p.dot(actual,n),0)
                    self.assertAlmostEqual(math.hypot(*n),1,places=6)
                    self.assertEqual(normals[i:i+3],[n,n,n])
                self.assertNotIn('uri',document['buffers'][0])
                self.assertEqual(document['materials'][0]['pbrMetallicRoughness']['baseColorFactor'],list(mesh.color))

    def test_3mf_has_closed_oriented_indexed_geometry_and_explicit_mm_units(self):
        for name,expected in (('rampa',16000),('bloque',32000),('escalera',20000)):
            with self.subTest(name=name),zipfile.ZipFile(io.BytesIO(three_mf(prepare(load('modulos/'+name+'.json'))))) as archive:
                self.assertEqual(set(archive.namelist()),{'[Content_Types].xml','_rels/.rels','3D/3dmodel.model'})
                root=ET.fromstring(archive.read('3D/3dmodel.model'))
                self.assertEqual(root.get('unit'),'millimeter')
                vertices=[tuple(float(n.get(k)) for k in ('x','y','z')) for n in root.iter(MF+'vertex')]
                triangles=[tuple(int(n.get(k)) for k in ('v1','v2','v3')) for n in root.iter(MF+'triangle')]
                self.assertAlmostEqual(volume([[vertices[i] for i in tri] for tri in triangles]),expected)
                # Independent edge count and winding audit, after reading the file.
                edges={}
                for tri in triangles:
                    for a,b in zip(tri,tri[1:]+tri[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
                self.assertTrue(all(len(e)==2 and e[0]==tuple(reversed(e[1])) for e in edges.values()))
                self.assertEqual(root.find(MF+'build/'+MF+'item').get('objectid'),'1')
                for entry in archive.namelist():ET.fromstring(archive.read(entry))

    def test_stl_binary_has_mm_coordinates_volume_and_exact_record_count(self):
        for name,expected in (('rampa',16000),('bloque',32000),('escalera',20000)):
            with self.subTest(name=name):
                mesh=prepare(load('modulos/'+name+'.json'));raw=stl(mesh)
                count=struct.unpack_from('<I',raw,80)[0]
                self.assertEqual(len(raw),84+50*count)
                triangles=[]
                for i in range(count):
                    values=struct.unpack_from('<12fH',raw,84+50*i)
                    self.assertEqual(values[-1],0)
                    tri=[values[j:j+3] for j in (3,6,9)];triangles.append(tri)
                    self.assertGreater(p.dot(p.cross(p.sub(tri[1],tri[0]),p.sub(tri[2],tri[0])),values[:3]),0)
                self.assertAlmostEqual(volume(triangles),expected)
                self.assertEqual(max(v[2] for tri in triangles for v in tri),20)

    def test_same_physical_model_in_mm_cm_and_m_has_identical_binary_geometry(self):
        data=load();reference=None
        for units,factor in (('mm',1),('cm',.1),('m',.001)):
            source=scaled(data,factor);source['units']=units;mesh=prepare(source)
            _,arrays=read_glb(glb(mesh))
            if reference is None:reference=arrays
            self.assertEqual(arrays,reference)
            self.assertAlmostEqual(mesh.volume_mm3,16000)

    def test_extreme_scales_preserve_volume_ratios_in_all_formats(self):
        for factor in (1e-8,1,1e6):
            with self.subTest(factor=factor):
                mesh=prepare(scaled(load(),factor))
                self.assertTrue(math.isclose(mesh.volume_mm3,16000*factor**3,rel_tol=1e-10))
                _,(positions,_)=read_glb(glb(mesh))
                actual=volume([positions[i:i+3] for i in range(0,len(positions),3)])
                self.assertTrue(math.isclose(actual,16000*factor**3/1e9,rel_tol=1e-6))
                self.assertGreater(len(stl(mesh)),84)
                self.assertTrue(three_mf(mesh).startswith(b'PK'))

    def test_exports_are_deterministic_and_do_not_change_input(self):
        source=load();previous=copy.deepcopy(source);mesh=prepare(source)
        for encode in (glb,three_mf,stl):self.assertEqual(encode(mesh),encode(prepare(source)))
        self.assertEqual(source,previous)

    def test_relative_units_require_explicit_equivalence(self):
        data=load();data['units']='u'
        with self.assertRaisesRegex(ValueError,'--unit-mm'):prepare(data)
        self.assertAlmostEqual(prepare(data,2).volume_mm3,16000*8)

    def test_missing_optional_backend_and_concave_mesh_are_rejected(self):
        for name in ('bloque-taladrado.json','cuatro-taladros.json'):
            with self.subTest(name=name),patch.dict('sys.modules',{'manifold3d':None}),self.assertRaisesRegex(ValueError,'dependencia opcional'):prepare(load(name))
        base=p.Model(load('escalon.json'))
        mesh={'type':'mesh','units':'mm','vertices':[list(v) for v in base.vertices],'faces':base.faces}
        with self.assertRaisesRegex(ValueError,'convexo'):prepare(mesh)

    def test_globally_reversed_convex_mesh_is_reoriented_outward(self):
        source={'type':'mesh','units':'mm','vertices':[[0,0,0],[4,0,0],[0,3,0],[0,0,2]],
                'faces':[[0,2,1],[0,1,3],[1,2,3],[2,0,3]]}
        for reverse in (False,True):
            if reverse:source['faces']=[list(reversed(f)) for f in source['faces']]
            self.assertAlmostEqual(prepare(source).volume_mm3,4)

    def test_float32_collapse_and_nonmanifold_or_disconnected_mesh_are_rejected(self):
        mesh=prepare(load())
        remote=[(x+1e10,y,z) for x,y,z in mesh.vertices]
        with self.assertRaises(ValueError):float32_vertices(remote,mesh.triangles)
        for triangles in (mesh.triangles[:-1],mesh.triangles+[mesh.triangles[0]],[(a,c,b) for a,b,c in mesh.triangles]):
            with self.subTest(triangles=len(triangles)),self.assertRaises(ValueError):validate_mesh(mesh.vertices,triangles)
        n=len(mesh.vertices)
        vertices=mesh.vertices+[(x+100,y,z) for x,y,z in mesh.vertices]
        triangles=mesh.triangles+[tuple(i+n for i in tri) for tri in mesh.triangles]
        with self.assertRaises(ValueError):validate_mesh(vertices,triangles)

    def test_material_values_are_validated_when_exporting_meshes(self):
        for asset in (None,{'base_color':[1,2,3,4]},{'base_color':[0,0,0,math.nan]},{'base_color':[True,0,0,1]}):
            data=load();data['asset']=asset
            with self.subTest(asset=asset),self.assertRaises(ValueError):prepare(data)

    def test_unrepresentable_physical_volume_is_rejected_instead_of_reporting_zero_or_infinity(self):
        for factor in (1e-120,1e110):
            with self.subTest(factor=factor),self.assertRaises(ValueError):prepare(scaled(load(),factor))


if __name__=='__main__':unittest.main()
