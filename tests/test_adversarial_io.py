"""Adversarial CLI/template/file-publication tests, confined to temporary dirs."""
import contextlib
import copy
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills'/'proyecciones-svg'
sys.path.insert(0,str(SOURCE/'scripts'))
import generar


class AuditHTML(HTMLParser):
    def __init__(self,text):
        super().__init__();self.scripts=0;self.events=[];self.urls=[]
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        self.scripts+=tag=='script'
        for key,value in attrs:
            if key.startswith('on'):self.events.append((key,value))
            if key in ('href','src'):self.urls.append(value)


class AdversarialIOTests(unittest.TestCase):
    def write_model(self,folder,data):
        path=folder/'source.json';path.write_text(json.dumps(data,ensure_ascii=True),encoding='utf-8');return path

    def run_generator(self,source,target,*extra):
        with contextlib.redirect_stdout(io.StringIO()):
            return generar.main([str(source),'--output-dir',str(target),*extra])

    def test_template_markers_in_valid_user_text_are_rendered_literally(self):
        for marker in ('__SHEET__','__ROTATION__','__SETTINGS__','__SECTIONS__'):
            with self.subTest(marker=marker),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
                data['name']=marker
                data['sections']=[{'name':marker,'origin':[3,2,1],'normal':[0,1,0]}]
                source=self.write_model(folder,data)
                self.assertEqual(self.run_generator(source,folder/'out','--sections','--viewer','--frames','8','--export-cota'),0)
                viewer=(folder/'out'/'visor.html').read_text(encoding='utf-8')
                self.assertIn(marker,viewer)
                self.assertNotIn('const settings=__SETTINGS__',viewer)

    def test_markup_like_names_do_not_become_scripts_events_or_network_urls(self):
        payloads=('</script><script>alert(1)</script>','<img src="https://invalid.example/" onerror="alert(1)">',
                  '../../escape', 'sección & < > " comillas', '\u202e--sections')
        for payload in payloads:
            with self.subTest(payload=payload),tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
                data['name']=payload;data['units']=payload
                data['sections']=[{'name':payload,'origin':[3,2,1],'normal':[0,1,0]}]
                self.run_generator(self.write_model(folder,data),folder/'out','--sections','--viewer','--frames','8','--export-cota','--cota-unit-mm','1')
                audit=AuditHTML((folder/'out'/'visor.html').read_text(encoding='utf-8'))
                self.assertEqual(audit.scripts,1)
                self.assertEqual(audit.events,[])
                self.assertTrue(all(url=='cortes.svg' for url in audit.urls),audit.urls)
                root=ET.parse(folder/'out'/'cortes.svg').getroot()
                self.assertEqual(root.findall('.//{http://www.w3.org/2000/svg}script'),[])
                self.assertEqual({p.name for p in folder.iterdir()},{'source.json','out'})

    def test_invalid_source_text_or_planes_preserve_every_previous_product(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
            source=self.write_model(folder,data);target=folder/'out'
            args=('--sections','--viewer','--frames','8','--export-cota')
            self.run_generator(source,target,*args)
            (target/'keep.txt').write_text('user content')
            previous={p.name:p.read_bytes() for p in target.iterdir()}
            mutations=[{'name':'bad\0name'},{'name':'bad\ud800name'},{'sections':None},
                       {'sections':[{'origin':[0,0,100],'normal':[0,0,1]}]},
                       {'sections':[{'origin':[3,2,1],'normal':[True,0,1]}]}]
            for change in mutations:
                with self.subTest(change=repr(change)):
                    self.write_model(folder,data)
                    self.run_generator(source,target,*args,'--force')
                    previous={p.name:p.read_bytes() for p in target.iterdir()}
                    broken={**copy.deepcopy(data),**change};self.write_model(folder,broken)
                    error=io.StringIO()
                    with contextlib.redirect_stderr(error),self.assertRaises(SystemExit):
                        self.run_generator(source,target,*args,'--force')
                    self.assertNotIn('Traceback',error.getvalue())
                    self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},previous)
                    self.assertFalse(any(p.name.startswith('.proyecciones-') for p in folder.iterdir()))

    def test_budget_timeout_and_worker_failure_do_not_publish_partial_calculations(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
            source=self.write_model(folder,data);target=folder/'out'
            self.run_generator(source,target,'--sections','--mode','sheet','--export-cota')
            previous={p.name:p.read_bytes() for p in target.iterdir()}
            for extra in (['--max-bytes','1'],['--timeout','0.000001']):
                with self.subTest(extra=extra),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    self.run_generator(source,target,'--sections','--mode','sheet','--export-cota','--force',*extra)
                self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},previous)
            with mock.patch.object(generar,'run_worker',side_effect=ValueError('injected failure')):
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    self.run_generator(source,target,'--sections','--mode','sheet','--export-cota','--force')
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},previous)

    def test_publication_io_failure_is_reported_and_files_are_never_truncated(self):
        # Documented guarantee: atomic per file, not a multi-file transaction.
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);data=json.loads((SOURCE/'assets'/'cuna.json').read_text())
            source=self.write_model(folder,data);target=folder/'out'
            args=('--sections','--mode','sheet','--export-cota')
            self.run_generator(source,target,*args)
            previous={p.name:p.read_bytes() for p in target.iterdir()}
            data['depth']*=.75;self.write_model(folder,data)
            self.run_generator(source,folder/'expected',*args)
            expected={p.name:p.read_bytes() for p in (folder/'expected').iterdir()}
            replace=os.replace;calls=[]
            def fail_second(a,b):
                calls.append(Path(b).name)
                if len(calls)==2:raise OSError('injected publication failure')
                replace(a,b)
            with mock.patch.object(generar.os,'replace',side_effect=fail_second):
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    self.run_generator(source,target,*args,'--force')
            self.assertEqual(len(calls),2)
            self.assertEqual((target/calls[0]).read_bytes(),expected[calls[0]])
            for name,old in previous.items():
                self.assertIn((target/name).read_bytes(),(old,expected[name]))


if __name__=='__main__':unittest.main()
