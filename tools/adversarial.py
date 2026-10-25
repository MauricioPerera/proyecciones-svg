"""Run the seeded adversarial battery and save reproducible local evidence."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.subcases=0
    def addSubTest(self,test,subtest,error):
        self.subcases+=1
        super().addSubTest(test,subtest,error)


def run(seed,output):
    os.environ['ADVERSARIAL_SEED']=str(seed)
    sys.path.insert(0,str(ROOT/'skills'/'proyecciones-svg'/'scripts'))
    sys.path.insert(0,str(ROOT/'tests'))
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_cortes_adversarial','test_adversarial_io'])
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    files=['tests/test_adversarial_io.py','tools/adversarial.py']
    files+=sorted(p.relative_to(ROOT).as_posix() for folder,pattern in
                  ((ROOT/'skills'/'proyecciones-svg'/'scripts','*.py'),(ROOT/'skills'/'proyecciones-svg'/'assets','*.json'),
                   (ROOT/'skills'/'proyecciones-svg'/'assets','*.html')) for p in folder.glob(pattern))
    report={'status':'success' if result.wasSuccessful() and not result.skipped else 'failure',
            'seed':seed,'system':platform.system(),'python':platform.python_version(),
            'created_at':datetime.now(timezone.utc).isoformat(),'tests':result.testsRun,'subcases':result.subcases,
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
            'details':[{'test':str(test),'traceback':trace} for test,trace in result.failures+result.errors],
            'scope':'Local unpublished source; no remote CI or stable publication.',
            'known_publication_limit':'Individual file replacements are atomic; an I/O error during publication can leave a mixed delivery.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','seed','tests','subcases','failures','errors')}))
    return report['status']=='success'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=20261025)
    parser.add_argument('--output',type=Path,default=ROOT/'build'/'adversarial'/'report.json')
    args=parser.parse_args()
    sys.exit(0 if run(args.seed,args.output) else 1)
