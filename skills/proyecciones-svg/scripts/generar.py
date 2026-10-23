"""Entrada portable y acotada para todos los modelos de proyecciones-svg."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
MAX_INPUT = 1024 * 1024


def renderers(data, args):
    """Select a single geometric model, shared by every requested projection."""
    import proyectar as p
    kind = data.get('type')
    if kind in ('extrusion', 'mesh'):
        model = p.Model(data)
        return {
            'vistas.svg': lambda: p.sheet_svg(model, args.system, args.hidden),
            'angulo.svg': lambda: p.view_svg(model, args.azimuth, args.elevation, args.hidden),
            'giro.svg': lambda: p.animation_svg(model, args),
        }
    if args.elevation < 0:
        raise ValueError('Los modelos taladrados requieren elevación 0..90°.')
    if kind == 'block_with_bore':
        import taladro_cilindrico as module
        model = module.BoredBlock(data)
    elif kind == 'sloped_prism_with_bore':
        import pieza_taladrada as module
        model = module.SlopedBore(data)
    else:
        import taladros_cruzados as base
        if kind == 'crossed_bores':
            constructor, decorator = base.CrossedBores, base.decorate
        elif kind == 'unequal_crossed_bores':
            from taladros_desiguales import UnequalBores, decorate
            constructor, decorator = UnequalBores, decorate
        elif kind in ('triple_crossed_bores', 'quadruple_crossed_bores'):
            from tres_taladros import ThreeBores, decorate
            from cuatro_taladros import FourBores
            constructor = ThreeBores if kind == 'triple_crossed_bores' else FourBores
            decorator = decorate
        else:
            raise ValueError('Tipo de modelo no admitido: '+str(kind))
        model = constructor(data)
        return {
            'vistas.svg': lambda: base.sheet(model, args.system, args.hidden, decorator),
            'angulo.svg': lambda: base.view(model, args, decorator),
            'giro.svg': lambda: base.animation(model, args, decorator),
        }
    return {
        'vistas.svg': lambda: module.sheet(model, args.system, args.hidden),
        'angulo.svg': lambda: module.view(model, args),
        'giro.svg': lambda: module.animation(model, args),
    }


def requested(args):
    names = {'sheet':['vistas.svg'], 'view':['angulo.svg'], 'animation':['giro.svg'],
             'all':['vistas.svg','angulo.svg','giro.svg']}[args.mode]
    return names + ['modelo.json', 'informe.json'] + (['visor.html'] if args.viewer else [])


def size_check(folder, limit):
    size = sum(path.stat().st_size for path in folder.iterdir() if path.is_file())
    if size > limit:
        raise ValueError(f'La salida supera el presupuesto de {limit} bytes ({size} bytes).')


def check_target(target, args):
    names=requested(args)
    known={'vistas.svg','angulo.svg','giro.svg','modelo.json','informe.json','visor.html'}
    if any((target/name).exists() for name in known-set(names)):
        raise ValueError('La carpeta contiene productos fuera del modo solicitado; usa otra carpeta para no mezclar entregas.')
    if not args.force and any((target/name).exists() for name in names):
        raise ValueError('Ya existen salidas; usa otra carpeta o --force.')


def worker(args):
    start = time.monotonic()
    data = json.loads(args.model.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('El JSON debe ser un objeto de modelo.')
    jobs = renderers(data, args)
    for name in requested(args):
        if name in jobs:
            root = jobs[name]()
            ET.ElementTree(root).write(args.output_dir/name, encoding='utf-8', xml_declaration=True)
            size_check(args.output_dir, args.max_bytes)
    (args.output_dir/'modelo.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if args.viewer:
        from visor import create_viewer
        create_viewer(args.output_dir, args.seconds, args.loop)
    report = {
        'version': (HERE.parent/'VERSION').read_text(encoding='utf-8').strip(),
        'type': data['type'], 'seconds': round(time.monotonic()-start, 4),
        'options': {key:getattr(args,key) for key in ('mode','system','hidden','azimuth','elevation','frames','seconds','sweep','loop')},
        'files': {path.name:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in sorted(args.output_dir.iterdir()) if path.is_file()},
    }
    (args.output_dir/'informe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    size_check(args.output_dir, args.max_bytes)


def run_worker(command, timeout):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=timeout,
                                env={**os.environ, 'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1'})
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'Generación interrumpida al alcanzar {timeout:g} segundos; no se publicaron salidas.') from error
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'El generador no pudo completar el modelo.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--mode',choices=('sheet','view','animation','all'),default='all')
    parser.add_argument('--system',choices=('third','first'),default='third')
    parser.add_argument('--hidden',choices=('dash','omit'),default='dash')
    parser.add_argument('--azimuth',type=float,default=45)
    parser.add_argument('--elevation',type=float,default=35.2643897)
    parser.add_argument('--frames',type=int,default=72)
    parser.add_argument('--seconds',type=float,default=6)
    parser.add_argument('--sweep',type=float,default=360)
    parser.add_argument('--loop',action='store_true')
    parser.add_argument('--viewer',action='store_true',help='HTML autónomo con plano, giro y controles; requiere --mode all.')
    parser.add_argument('--timeout',type=float,default=180,help='Presupuesto de tiempo: 0 < segundos <= 600.')
    parser.add_argument('--max-bytes',type=int,default=16*1024*1024,help='Presupuesto total de salida: 1..67108864 bytes.')
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--_worker',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if (not all(math.isfinite(v) for v in (args.azimuth,args.elevation,args.seconds,args.sweep,args.timeout))
            or not -90<=args.elevation<=90 or args.seconds<=0 or not 8<=args.frames<=240
            or not 0<args.timeout<=600 or not 1<=args.max_bytes<=64*1024*1024):
            raise ValueError('Parámetros fuera de límites; consulta --help.')
        if args.viewer and args.mode!='all':
            raise ValueError('--viewer requiere --mode all.')
        if args.model.stat().st_size>MAX_INPUT:
            raise ValueError('El JSON supera el límite de 1 MiB.')
        if args._worker:
            worker(args)
            return 0
        target = args.output_dir.resolve()
        names = requested(args)
        check_target(target,args)
        target.parent.mkdir(parents=True,exist_ok=True)
        # This function creates and owns the temporary directory. Invalid inputs,
        # timeout and output-budget failures leave existing deliverables intact.
        with tempfile.TemporaryDirectory(prefix='.proyecciones-',dir=target.parent) as staging:
            folder = Path(staging)
            forwarded = list(sys.argv[1:] if argv is None else argv)
            # Append overrides instead of rewriting arbitrary path strings.
            command = [sys.executable,'-B',str(Path(__file__).resolve()),*forwarded,
                       '--output-dir',str(folder),'--_worker']
            run_worker(command,args.timeout)
            target.mkdir(parents=True,exist_ok=True)
            check_target(target,args)
            for name in names:
                os.replace(folder/name,target/name)
                print(target/name)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,RecursionError) as error:
        parser.exit(2,f'Error: {error}\n')
    return 0


if __name__=='__main__':
    sys.exit(main())
