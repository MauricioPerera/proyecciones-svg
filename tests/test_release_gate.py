import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import validate_matrix
import release
from prepare_release import approved_run,check_proof,prepare,write_assets
from install_skill import verified_files


def fixtures(folder,systems=('Linux','Windows','Darwin')):
    sha='a'*40
    package=b'fixture package'
    for system in systems:
        for version in ('3.10.20','3.14.4'):
            dest=folder/f'python-{system}-{version}'
            dest.mkdir()
            (dest/'package.zip').write_bytes(package)
            report={'commit':sha,'system':system,'python':version,'version':'1.0.0','status':'success',
                'suites':{name:{'tests':count,'failures':0,'errors':0,'skipped':0}
                          for name,count in (('geometry',69),('distribution',16))},
                'package':{'name':'package.zip','sha256':hashlib.sha256(package).hexdigest()}}
            (dest/'report.json').write_text(json.dumps(report),encoding='utf-8')
    (folder/'browser-evidence').mkdir()
    rows=[{'browser':browser,'model':model,'angles':24,'portable':True,'reducedMotion':True,'width320':True}
          for browser in ('chromium','firefox') for model in ('cuna','bloque-taladrado','cuatro-taladros')]
    (folder/'browser-evidence'/'report.json').write_text(json.dumps(rows),encoding='utf-8')
    return sha


class ReleaseGateTests(unittest.TestCase):
    def test_windows_linux_profile_is_explicit_and_keeps_macos_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            sha=fixtures(folder,systems=('Windows','Linux'))
            with self.assertRaises(ValueError):
                validate_matrix.validate(folder,sha)
            result=validate_matrix.validate(folder,sha,'windows-linux')
            self.assertEqual(result['validated_systems'],['Linux','Windows'])
            self.assertEqual(result['pending_systems'],['Darwin'])
            check_proof(result,sha,'1.0.0',result['package_sha256'],'windows-linux')
            with self.assertRaises(ValueError):
                check_proof(result,sha,'1.0.0',result['package_sha256'])

    def test_scoped_profile_still_rejects_missing_failed_or_changed_results(self):
        for fault in ('missing','failed','changed'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)
                sha=fixtures(folder,systems=('Windows','Linux'))
                report=next(folder.glob('python-*/report.json'))
                if fault=='missing':
                    report.unlink()
                elif fault=='failed':
                    data=json.loads(report.read_text())
                    data['suites']['distribution']['errors']=1
                    report.write_text(json.dumps(data),encoding='utf-8')
                else:
                    (report.parent/'package.zip').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    validate_matrix.validate(folder,sha,'windows-linux')

    def test_complete_matrix_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            sha=fixtures(folder)
            result=validate_matrix.validate(folder,sha)
            self.assertEqual(len(result['python_jobs']),6)
            self.assertEqual(len(result['browsers']),6)

    def test_missing_job_wrong_commit_and_skipped_tests_cannot_pass(self):
        for fault in ('missing','commit','skipped'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)
                sha=fixtures(folder)
                path=next(folder.glob('python-*/report.json'))
                data=json.loads(path.read_text())
                if fault=='missing':
                    path.unlink()
                else:
                    if fault=='commit': data['commit']='b'*40
                    else: data['suites']['geometry']['skipped']=1
                    path.write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaises(ValueError):
                    validate_matrix.validate(folder,sha)

    def test_changed_or_different_platform_packages_cannot_pass(self):
        for update_digest in (False,True):
            with self.subTest(update_digest=update_digest),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp)
                sha=fixtures(folder)
                path=next(folder.glob('python-*/package.zip'))
                path.write_bytes(b'different')
                if update_digest:
                    report=path.parent/'report.json'
                    data=json.loads(report.read_text())
                    data['package']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                    report.write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaises(ValueError):
                    validate_matrix.validate(folder,sha)

    def test_incomplete_browser_evidence_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            sha=fixtures(folder)
            path=folder/'browser-evidence'/'report.json'
            rows=json.loads(path.read_text())
            rows.pop()
            path.write_text(json.dumps(rows),encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_matrix.validate(folder,sha)

    def test_release_contains_the_selected_license(self):
        with tempfile.TemporaryDirectory() as temp:
            package,_=release.build(destination=Path(temp)/'release.zip')
            files,manifest=verified_files(package)
            self.assertEqual(files['LICENSE'],(ROOT/'LICENSE').read_bytes().replace(b'\r\n',b'\n'))
            self.assertEqual(manifest['version'],(release.SOURCE/'VERSION').read_text().strip())

    def test_draft_preparation_rejects_unapproved_commits_and_mismatched_packages(self):
        commit='a'*40
        runs=[{'headSha':commit,'conclusion':'success','event':'pull_request'},
              {'headSha':'b'*40,'conclusion':'success','event':'push'},
              {'headSha':commit,'conclusion':'failure','event':'push'}]
        self.assertIsNone(approved_run(runs,commit))
        runs.append({'headSha':commit,'conclusion':'success','event':'push'})
        self.assertEqual(approved_run(runs,commit),runs[-1])
        proof={'commit':commit,'version':'1.0.0','status':'success','package_sha256':'digest',
               'python_jobs':[{}]*6,'browsers':[{}]*6}
        check_proof(proof,commit,'1.0.0','digest')
        for key,value in (('commit','b'*40),('version','1.0.1'),('package_sha256','other'),('status','failure'),('python_jobs',[])):
            with self.subTest(key=key),self.assertRaises(ValueError):
                check_proof({**proof,key:value},commit,'1.0.0','digest')

    def test_local_preparation_is_explicitly_pending_and_cannot_create_a_draft(self):
        with self.assertRaisesRegex(ValueError,'no permite'):
            prepare('owner/repo',create_draft=True,local_only=True)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            version=(release.SOURCE/'VERSION').read_text().strip()
            package,digest=release.build(destination=folder/f'proyecciones-svg-{version}.zip')
            write_assets(folder,package,'a'*40,version,digest,{'status':'pending'})
            self.assertTrue((folder/'ci-status.json').exists())
            self.assertFalse((folder/'release-readiness.json').exists())
            self.assertIn('CI remota pendiente',(folder/'RELEASE_NOTES.md').read_text(encoding='utf-8'))
            for line in (folder/'SHA256SUMS').read_text().splitlines():
                expected,name=line.split('  ',1)
                self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(),expected)


if __name__=='__main__':
    unittest.main()
