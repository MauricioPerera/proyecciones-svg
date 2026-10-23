"""Validate and install a release, preserving an existing skill on update."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path,PurePosixPath
import tempfile
import zipfile

NAME='proyecciones-svg'
MAX_PACKAGE=16*1024*1024


def verified_files(package):
    with zipfile.ZipFile(package) as archive:
        entries=archive.infolist()
        if len(entries)>256 or sum(info.file_size for info in entries)>MAX_PACKAGE:
            raise ValueError('Paquete demasiado grande.')
        files={}
        for info in entries:
            path=PurePosixPath(info.filename)
            if ('\\' in info.filename or ':' in info.filename or path.is_absolute() or '..' in path.parts
                or not path.parts or path.parts[0]!=NAME or len(path.parts)<2
                or info.is_dir() or ((info.external_attr>>16)&0o170000)==0o120000):
                raise ValueError('Ruta no permitida en el paquete: '+info.filename)
            name='/'.join(path.parts[1:])
            if name in files or any(key.casefold()==name.casefold() for key in files):
                raise ValueError('Ruta duplicada en el paquete.')
            files[name]=archive.read(info)
    if 'RELEASE.json' not in files:
        raise ValueError('El paquete no contiene RELEASE.json.')
    manifest=json.loads(files.pop('RELEASE.json'))
    if not isinstance(manifest,dict):
        raise ValueError('RELEASE.json debe ser un objeto.')
    actual={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    if manifest.get('name')!=NAME or manifest.get('files')!=actual:
        raise ValueError('Las sumas del paquete no coinciden con RELEASE.json.')
    if ('VERSION' not in files or 'SKILL.md' not in files
        or files['VERSION'].decode().strip()!=manifest.get('version')):
        raise ValueError('Identidad de versión inválida.')
    return files,manifest


def install(package, skills_dir, update=False):
    files,manifest=verified_files(package)
    parent=Path(skills_dir).resolve()
    target=parent/NAME
    if target.is_symlink():
        raise ValueError('La instalación existente es un enlace simbólico.')
    if target.exists() and not update:
        raise ValueError('La skill ya existe; --update conserva una copia antes de actualizar.')
    parent.mkdir(parents=True,exist_ok=True)
    backup=None
    with tempfile.TemporaryDirectory(prefix='.proyecciones-install-',dir=parent) as staging:
        candidate=Path(staging)/NAME
        candidate.mkdir()
        for name,data in files.items():
            path=candidate/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        (candidate/'RELEASE.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        if target.exists():
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            # Backups live outside skills/ so they are not discovered as a
            # second skill. Both paths are direct children of known parents.
            backups=parent.parent/'skill-backups'
            backups.mkdir(exist_ok=True)
            backup=backups/(NAME+'-'+stamp)
            target.rename(backup)
        try:
            candidate.rename(target)
        except OSError:
            if backup:
                backup.rename(target)
            raise
    return target,backup


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('--skills-dir',type=Path,required=True)
    parser.add_argument('--update',action='store_true')
    args=parser.parse_args()
    try:
        target,backup=install(args.package,args.skills_dir,args.update)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as error:
        parser.exit(2,f'Error: {error}\n')
    print(target)
    if backup:
        print('Copia anterior: '+str(backup))
