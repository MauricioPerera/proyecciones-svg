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
from prepare_release import approved_run,check_proof
from install_skill import verified_files


def fixtures(folder):
    sha='a'*40
    package=b'fixture package'
    for system in ('Linux','Windows','Darwin'):
        for version in ('3.10.20','3.14.4'):
            dest=folder/f'python-{system}-{version}'
            dest.mkdir()
            (dest/'package.zip').write_bytes(package)
            report={'commit':sha,'system':system,'python':version,'version':'1.0.0','status':'success',
                'suites':{name:{'tests':count,'failures':0,'errors':0,'skipped':0}
                          for name,count in (('geometry',69),('distribution',7))},
                'package':{'name':'package.zip','sha256':hashlib.sha256(package).hexdigest()}}
            (dest/'report.json').write_text(json.dumps(report),encoding='utf-8')
    (folder/'browser-evidence').mkdir()
    rows=[{'browser':browser,'model':model,'angles':24,'portable':True,'reducedMotion':True,'width320':True}
          for browser in ('chromium','firefox') for model in ('cuna','bloque-taladrado','cuatro-taladros')]
    (folder/'browser-evidence'/'report.json').write_text(json.dumps(rows),encoding='utf-8')
    return sha


class ReleaseGateTests(unittest.TestCase):
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


if __name__=='__main__':
    unittest.main()
