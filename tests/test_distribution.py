import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills'/'proyecciones-svg'
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(SOURCE/'scripts'))
import release
import install_skill
import generar


class DistributionTests(unittest.TestCase):
    def test_build_is_reproducible_and_installs_in_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            first,digest=release.build(destination=folder/'first.zip')
            second,other=release.build(destination=folder/'second.zip')
            self.assertEqual(digest,other)
            target,backup=install_skill.install(first,folder/'clean skills')
            self.assertIsNone(backup)
            result=subprocess.run([sys.executable,'-B',str(target/'scripts'/'generar.py'),
                str(target/'assets'/'cuna.json'),'--output-dir',str(folder/'output'),
                '--frames','8','--viewer','--export-cota','--sections','--export-glb','--export-3mf','--export-stl'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((folder/'output'/'visor.html').is_file())
            self.assertEqual(json.loads((folder/'output'/'modelo.cota').read_text())['units'],'mm')
            self.assertTrue((folder/'output'/'cortes.svg').exists())
            self.assertTrue(all((folder/'output'/('modelo.'+ext)).is_file() for ext in ('glb','3mf','stl')))
            self.assertNotIn(str(ROOT),(folder/'output'/'visor.html').read_text(encoding='utf-8'))
            self.assertEqual((target/'VERSION').read_text().strip(),(SOURCE/'VERSION').read_text().strip())
            bored=subprocess.run([sys.executable,'-B',str(target/'scripts'/'generar.py'),
                str(target/'assets'/'cuatro-taladros.json'),'--output-dir',str(folder/'bored'),
                '--mode','sheet','--export-cota','--export-glb','--export-3mf','--export-stl'],capture_output=True,text=True)
            self.assertEqual(bored.returncode,0,bored.stderr)
            self.assertEqual(json.loads((folder/'bored'/'informe.json').read_text())['meshes']['genus'],7)

    def test_update_requires_flag_and_preserves_previous_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            package,_=release.build(destination=folder/'release.zip')
            target,_=install_skill.install(package,folder/'skills')
            (target/'local-marker').write_text('keep me')
            with self.assertRaises(ValueError):
                install_skill.install(package,folder/'skills')
            _,backup=install_skill.install(package,folder/'skills',True)
            self.assertEqual((backup/'local-marker').read_text(),'keep me')
            self.assertFalse((target/'local-marker').exists())

    def test_corrupt_or_traversing_packages_do_not_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for name in ('proyecciones-svg/../outside','/outside','proyecciones-svg/a\\b','proyecciones-svg/C:bad'):
                package=folder/'bad.zip'
                with zipfile.ZipFile(package,'w') as archive:
                    archive.writestr(name,'bad')
                with self.assertRaises(ValueError):
                    install_skill.install(package,folder/'skills')
                self.assertFalse((folder/'skills').exists())
            package,_=release.build(destination=folder/'corrupt.zip')
            with zipfile.ZipFile(package,'a') as archive:
                archive.writestr('proyecciones-svg/unlisted.txt','bad')
            with self.assertRaisesRegex(ValueError,'sumas'):
                install_skill.install(package,folder/'skills')

    def test_budget_invalid_input_and_timeout_preserve_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            output=folder/'output'
            output.mkdir()
            marker=output/'vistas.svg'
            marker.write_text('previous output')
            model=folder/'bad.json'
            for content,extra in (('[]',[]),('{"type":"mesh"}',[]),
                    ((SOURCE/'assets'/'cuna.json').read_text(),['--max-bytes','1'])):
                model.write_text(content,encoding='utf-8')
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    generar.main([str(model),'--output-dir',str(output),'--mode','sheet','--force',*extra])
                self.assertEqual(marker.read_text(),'previous output')
            with mock.patch.object(generar.subprocess,'run',side_effect=subprocess.TimeoutExpired('worker',.01)):
                with self.assertRaisesRegex(ValueError,'interrumpida'):
                    generar.run_worker(['worker'],.01)
            self.assertEqual(marker.read_text(),'previous output')

    def test_real_timeout_kills_worker(self):
        with self.assertRaisesRegex(ValueError,'interrumpida'):
            generar.run_worker([sys.executable,'-c','import time; time.sleep(10)'],.05)

    def test_changing_product_selection_cannot_leave_a_stale_viewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            source=SOURCE/'assets'/'cuna.json'
            with contextlib.redirect_stdout(io.StringIO()):
                generar.main([str(source),'--output-dir',str(folder),'--frames','8','--viewer'])
            previous={p.name:p.read_bytes() for p in folder.iterdir()}
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                generar.main([str(source),'--output-dir',str(folder),'--mode','sheet','--force'])
            self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},previous)

    def test_every_supported_example_uses_common_entrypoint(self):
        for source in sorted((SOURCE/'assets').glob('*.json')):
            with self.subTest(source=source.name),tempfile.TemporaryDirectory() as tmp:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(generar.main([str(source),'--output-dir',tmp,'--mode','sheet']),0)
                report=json.loads((Path(tmp)/'informe.json').read_text())
                self.assertIn('vistas.svg',report['files'])
                self.assertEqual(report['type'],json.loads(source.read_text())['type'])

    def test_optional_cota_keeps_svg_geometry_and_viewer_byte_identical(self):
        import hashlib
        for name in ('cuna.json','cuatro-taladros.json'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for extra,folder in (([],root/'svg'),(['--export-cota'],root/'cota')):
                    with contextlib.redirect_stdout(io.StringIO()):
                        generar.main([str(SOURCE/'assets'/name),'--output-dir',str(folder),
                                      '--frames','8','--viewer',*extra])
                self.assertFalse((root/'svg'/'modelo.cota').exists())
                for product in ('vistas.svg','angulo.svg','giro.svg','visor.html','modelo.json'):
                    self.assertEqual((root/'svg'/product).read_bytes(),(root/'cota'/product).read_bytes(),product)
                report=json.loads((root/'cota'/'informe.json').read_text())
                self.assertEqual(report['files']['modelo.cota']['sha256'],
                                 hashlib.sha256((root/'cota'/'modelo.cota').read_bytes()).hexdigest())
                self.assertEqual(report['cota']['millimeters_per_source_unit'],10)

    def test_cota_budget_unit_errors_and_selection_preserve_previous_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'output'
            model=Path(tmp)/'modelo.json'
            data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
            model.write_text(json.dumps(data))
            common=[str(model),'--output-dir',str(folder),'--frames','8','--viewer']
            with contextlib.redirect_stdout(io.StringIO()):
                generar.main([*common,'--export-cota'])
            previous={p.name:p.read_bytes() for p in folder.iterdir()}
            budget=sum(len(previous[name]) for name in ('vistas.svg','angulo.svg','giro.svg','modelo.json','modelo.cota'))-1
            for extra in ([],['--export-cota','--max-bytes',str(budget)],
                          ['--export-cota','--cota-unit-mm','0'],['--cota-unit-mm','1']):
                with self.subTest(extra=extra),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    generar.main([*common,'--force',*extra])
                self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},previous)
            data['units']='relative'
            model.write_text(json.dumps(data))
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                generar.main([*common,'--export-cota','--force'])
            self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},previous)

    def test_sections_preserve_all_other_products_and_are_reported(self):
        import hashlib
        import xml.etree.ElementTree as ET
        for name in ('cuna.json','cuatro-taladros.json'):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for extra,folder in (([],root/'base'),(['--sections'],root/'cuts')):
                    with contextlib.redirect_stdout(io.StringIO()):
                        generar.main([str(SOURCE/'assets'/name),'--output-dir',str(folder),
                                      '--frames','8','--viewer','--export-cota',*extra])
                for product in ('vistas.svg','angulo.svg','giro.svg','modelo.json','modelo.cota'):
                    self.assertEqual((root/'base'/product).read_bytes(),(root/'cuts'/product).read_bytes(),product)
                report=json.loads((root/'cuts'/'informe.json').read_text())
                self.assertTrue(report['options']['sections'])
                self.assertEqual(report['files']['cortes.svg']['sha256'],hashlib.sha256((root/'cuts'/'cortes.svg').read_bytes()).hexdigest())
                self.assertEqual(len(report['sections']['planes']),2)
                self.assertEqual(report['sections']['units'],'cm')
                svg=ET.parse(root/'cuts'/'cortes.svg')
                self.assertEqual(len(svg.findall('.//*[@data-section]')),2)
                viewer=(root/'cuts'/'visor.html').read_text(encoding='utf-8')
                self.assertNotIn('__SECTIONS__',viewer)
                self.assertEqual('id="section-guides"' in viewer,name=='cuatro-taladros.json')

    def test_section_failures_budget_and_stale_selection_preserve_previous_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'output'
            model=Path(tmp)/'modelo.json'
            data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
            model.write_text(json.dumps(data))
            common=[str(model),'--output-dir',str(folder),'--mode','sheet','--export-cota']
            with contextlib.redirect_stdout(io.StringIO()):
                generar.main([*common,'--sections'])
            previous={p.name:p.read_bytes() for p in folder.iterdir()}
            for extra in ([],['--sections','--max-bytes','1']):
                with self.subTest(extra=extra),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    generar.main([*common,'--force',*extra])
                self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},previous)
            data['sections']=[{'origin':[0,0,100],'normal':[0,0,1]}]
            model.write_text(json.dumps(data))
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                generar.main([*common,'--sections','--force'])
            self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},previous)

    def test_scaled_sections_export_together_with_cota_and_original_units(self):
        import xml.etree.ElementTree as ET
        from test_escalas import scaled
        original=json.loads((SOURCE/'assets'/'cuatro-taladros.json').read_text())
        for factor in (1e-8,1,1e6):
            with self.subTest(factor=factor),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp)
                model=folder/'source.json'
                model.write_text(json.dumps(scaled(original,factor)))
                with contextlib.redirect_stdout(io.StringIO()):
                    generar.main([str(model),'--output-dir',str(folder/'out'),'--mode','sheet','--sections','--export-cota'])
                report=json.loads((folder/'out'/'informe.json').read_text())
                self.assertEqual(report['sections']['units'],'cm')
                cota=json.loads((folder/'out'/'modelo.cota').read_text())
                cutters=cota['entities'][0]['props']['operands'][1:]
                root=ET.parse(folder/'out'/'cortes.svg')
                diameter_labels=[float(n.get('data-diameter')) for n in root.iter() if n.get('data-diameter')]
                for label,cutter,expected in zip(diameter_labels,cutters,(1.2,.8,.6,.4)):
                    self.assertAlmostEqual(label/(expected*factor),1)
                    self.assertAlmostEqual(cutter['radius']/(expected*factor*5),1)


if __name__=='__main__':
    unittest.main()
