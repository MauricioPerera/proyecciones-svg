"""CLI combinations retain SVG/Cota products and publish mesh outputs safely."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills'/'proyecciones-svg'
sys.path.insert(0,str(SOURCE/'scripts'))
import generar


def run(source,folder,*options):
    with contextlib.redirect_stdout(io.StringIO()):
        return generar.main([str(source),'--output-dir',str(folder),*options])


class MeshDistributionTests(unittest.TestCase):
    def test_combined_mesh_exports_preserve_svg_viewer_source_and_cota(self):
        for name in ('rampa','bloque','escalera'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source=SOURCE/'assets'/'modulos'/(name+'.json')
                flags=('--viewer','--frames','8','--export-cota')
                run(source,root/'base',*flags)
                run(source,root/'meshes',*flags,'--export-glb','--export-3mf','--export-stl')
                for product in ('vistas.svg','angulo.svg','giro.svg','modelo.json','visor.html','modelo.cota'):
                    self.assertEqual((root/'base'/product).read_bytes(),(root/'meshes'/product).read_bytes(),product)
                report=json.loads((root/'meshes'/'informe.json').read_text())
                self.assertEqual(report['meshes']['millimeters_per_source_unit'],1)
                self.assertEqual(report['meshes']['bounds_mm'],[[0,0,0],[40,40,20]])
                self.assertFalse(report['meshes']['printing']['sliced'])
                for ext in ('glb','3mf','stl'):
                    self.assertTrue((root/'meshes'/('modelo.'+ext)).is_file())
                    self.assertIn('modelo.'+ext,report['files'])

    def test_common_unit_override_applies_equally_to_cota_and_meshes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=json.loads((SOURCE/'assets'/'modulos'/'rampa.json').read_text())
            data['units']='u';source=root/'relative.json';source.write_text(json.dumps(data))
            run(source,root/'out','--mode','sheet','--export-cota','--export-3mf','--export-glb','--unit-mm','2')
            report=json.loads((root/'out'/'informe.json').read_text())
            self.assertEqual(report['cota']['millimeters_per_source_unit'],2)
            self.assertEqual(report['meshes']['millimeters_per_source_unit'],2)
            self.assertEqual(report['meshes']['bounds_mm'],[[0,0,0],[80,80,40]])
            for flags in (('--unit-mm','1'),('--export-glb','--unit-mm','0'),
                          ('--export-cota','--unit-mm','2','--cota-unit-mm','3')):
                with self.subTest(flags=flags),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    run(source,root/'bad',*flags)
                self.assertFalse((root/'bad').exists())

    def test_mesh_errors_budget_and_stale_selections_keep_previous_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'out';source=SOURCE/'assets'/'modulos'/'rampa.json'
            common=('--mode','sheet','--export-glb','--export-3mf','--export-stl','--export-cota')
            run(source,output,*common)
            previous={p.name:p.read_bytes() for p in output.iterdir()}
            for flags in (('--mode','sheet'),('--mode','sheet','--export-glb'),(*common,'--max-bytes','1')):
                with self.subTest(flags=flags),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    run(source,output,*flags,'--force')
                self.assertEqual({p.name:p.read_bytes() for p in output.iterdir()},previous)
            invalid=json.loads((SOURCE/'assets'/'cuatro-taladros.json').read_text())
            invalid['bores'][0]['center']=[0,0]
            invalid_path=root/'invalid.json';invalid_path.write_text(json.dumps(invalid))
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                run(invalid_path,output,*common,'--force')
            self.assertEqual({p.name:p.read_bytes() for p in output.iterdir()},previous)

    def test_four_bores_preserve_svg_cota_and_sections_with_all_mesh_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=SOURCE/'assets'/'cuatro-taladros.json'
            flags=('--viewer','--frames','8','--sections','--export-cota')
            run(source,root/'base',*flags)
            run(source,root/'meshes',*flags,'--export-glb','--export-3mf','--export-stl','--mesh-tolerance-mm','0.02')
            for product in ('vistas.svg','angulo.svg','giro.svg','cortes.svg','modelo.json','visor.html','modelo.cota'):
                self.assertEqual((root/'base'/product).read_bytes(),(root/'meshes'/product).read_bytes(),product)
            report=json.loads((root/'meshes'/'informe.json').read_text())
            self.assertEqual(report['meshes']['genus'],7)
            self.assertEqual(report['meshes']['tessellation']['mouths'],8)
            self.assertLessEqual(report['meshes']['tessellation']['max_radial_sagitta_mm'],0.02)
            previous={p.name:p.read_bytes() for p in (root/'meshes').iterdir()}
            for tolerance in ('nan','0','-1','1e-20'):
                with self.subTest(tolerance=tolerance),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    run(source,root/'meshes',*flags,'--export-glb','--export-3mf','--export-stl','--mesh-tolerance-mm',tolerance,'--force')
                self.assertEqual({p.name:p.read_bytes() for p in (root/'meshes').iterdir()},previous)

    def test_sections_coexist_with_meshes_for_a_convex_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            run(SOURCE/'assets'/'modulos'/'rampa.json',root,'--viewer','--frames','8','--sections',
                '--export-glb','--export-3mf','--export-stl','--export-cota')
            report=json.loads((root/'informe.json').read_text())
            self.assertEqual(len(report['sections']['planes']),2)
            self.assertEqual(set(report['files']),{'vistas.svg','angulo.svg','giro.svg','cortes.svg','modelo.json','visor.html',
                                                  'modelo.glb','modelo.3mf','modelo.stl','modelo.cota'})


if __name__=='__main__':unittest.main()
