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
                '--frames','8','--viewer'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((folder/'output'/'visor.html').is_file())
            self.assertNotIn(str(ROOT),(folder/'output'/'visor.html').read_text(encoding='utf-8'))
            self.assertEqual((target/'VERSION').read_text().strip(),(SOURCE/'VERSION').read_text().strip())

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


if __name__=='__main__':
    unittest.main()
