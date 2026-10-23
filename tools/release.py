"""Build a deterministic, checksummed skill ZIP using only the standard library."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills'/'proyecciones-svg'


def build(source=SOURCE, destination=None):
    version=(source/'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9.]+)?',version):
        raise ValueError('VERSION inválida.')
    destination=Path(destination) if destination else ROOT/'dist'/f'proyecciones-svg-{version}.zip'
    files={}
    for path in sorted(source.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.pyo'):
            if path.is_symlink():
                raise ValueError('No se empaquetan enlaces simbólicos: '+str(path))
            data=path.read_bytes()
            if path.suffix in ('.md','.py','.json','.yaml','.html') or path.name=='VERSION':
                data=data.replace(b'\r\n',b'\n')
            files[path.relative_to(source).as_posix()]=data
    manifest={'name':'proyecciones-svg','version':version,
              'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    files['RELEASE.json']=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Stored entries avoid zlib-version differences across OS/Python builds.
    # The source-only package is small enough to prefer byte reproducibility.
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo('proyecciones-svg/'+name,date_time=(2020,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_STORED
            info.create_system=3
            info.external_attr=0o100644<<16
            archive.writestr(info,data)
    digest=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.zip.sha256').write_text(digest+'  '+destination.name+'\n',encoding='ascii')
    return destination,digest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    path,digest=build(destination=args.output)
    print(path)
    print(digest)
