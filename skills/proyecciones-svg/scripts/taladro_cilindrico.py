"""Analytic SVG for a rectangular block with one vertical through bore."""
from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import proyectar as p


class BoredBlock:
    def __init__(self, data):
        if not isinstance(data, dict) or data.get("type") != "block_with_bore":
            raise ValueError("Se esperaba type=block_with_bore.")
        self.size = p.point(data.get("size"), 3)
        self.width, self.depth, self.height = self.size
        if min(self.size) <= 0:
            raise ValueError("Las tres dimensiones del bloque deben ser positivas.")
        bore = data.get("bore", {})
        if not isinstance(bore, dict) or bore.get("axis") != "z" or bore.get("through") is not True:
            raise ValueError("Este constructor admite un único taladro pasante con eje z.")
        self.cx, self.cy = p.point(bore.get("center"), 2)
        self.radius = p.number(bore.get("diameter"))/2
        if not (self.radius > 0 and self.radius < self.cx < self.width-self.radius
                and self.radius < self.cy < self.depth-self.radius):
            raise ValueError("El círculo completo debe quedar estrictamente dentro del bloque.")
        self.box = p.Model({"name": data.get("name", "Bloque con taladro"), "units": data.get("units", "u"),
                            "type": "extrusion", "profile": [[0, 0], [self.width, 0],
                            [self.width, self.height], [0, self.height]], "depth": self.depth})
        self.box.data = data
        self.center = (self.width/2, self.depth/2, self.height/2)
        self.span = self.box.span

    def normalized(self, point):
        return tuple((a-b)/self.span for a, b in zip(point, self.center))

    def rim(self, t, z):
        return self.normalized((self.cx+self.radius*math.cos(t), self.cy+self.radius*math.sin(t), z))


def bottom_visible_arc(block, azimuth, elevation):
    """Angles on the bottom rim whose rays exit through the top opening."""
    if elevation <= 0:
        return None
    if elevation >= 90-1e-8:
        return 0.0, 2*math.pi
    shift = block.height/math.tan(math.radians(elevation))
    if shift >= 2*block.radius:
        return None
    phi = math.radians(azimuth)-math.pi/2
    alpha = math.acos(max(-1.0, min(0.0, -shift/(2*block.radius))))
    return phi+alpha, phi+2*math.pi-alpha


def arc_path(block, mapping, azimuth, elevation, z, start, end):
    def xy(t):
        return mapping(p.project([block.rim(t, z)], azimuth, elevation)[0])
    a, b = xy(start), xy(end)
    origin = mapping((0, 0, 0))
    scale = abs(mapping((1, 0, 0))[0]-origin[0])
    rx = block.radius/block.span*scale
    ry = rx*math.sin(math.radians(elevation))
    if end-start >= 2*math.pi-1e-8:
        mid = xy((start+end)/2)
        return (f"M{p.fmt(a[0])},{p.fmt(a[1])} A{p.fmt(rx)},{p.fmt(ry)} 0 0 0 {p.fmt(mid[0])},{p.fmt(mid[1])} "
                f"A{p.fmt(rx)},{p.fmt(ry)} 0 0 0 {p.fmt(b[0])},{p.fmt(b[1])}")
    large = int(end-start > math.pi)
    return f"M{p.fmt(a[0])},{p.fmt(a[1])} A{p.fmt(rx)},{p.fmt(ry)} 0 {large} 0 {p.fmt(b[0])},{p.fmt(b[1])}"


def decorate(parent, block, azimuth, elevation, mapping, hidden, prefix):
    """Keep fill -> hidden -> visible ordering; all curves are SVG ellipses/arcs."""
    strokes = [node for node in parent if node.get("class") in ("edge", "hidden-edge")]
    for node in strokes:
        parent.remove(node)
    shade = p.svg_el(parent, "g", data_layer="bore-surface")
    concealed = p.svg_el(parent, "g", data_layer="bore-hidden")
    visible = p.svg_el(parent, "g", data_layer="bore-visible")
    flat = abs(math.cos(math.radians(elevation))) < 1e-8
    horizontal = elevation <= 1e-8
    if not horizontal:
        center_top = mapping(p.project([block.normalized((block.cx, block.cy, block.height))], azimuth, elevation)[0])
        center_bottom = mapping(p.project([block.normalized((block.cx, block.cy, 0))], azimuth, elevation)[0])
        scale = abs(mapping((1, 0, 0))[0]-mapping((0, 0, 0))[0])
        rx = block.radius/block.span*scale
        ry = rx*math.sin(math.radians(elevation))
        ellipse = {"cx": p.fmt(center_top[0]), "cy": p.fmt(center_top[1]), "rx": p.fmt(rx), "ry": p.fmt(ry)}
        defs = p.svg_el(shade, "defs")
        clip = p.svg_el(defs, "clipPath", id=prefix+"-opening", clipPathUnits="userSpaceOnUse")
        p.svg_el(clip, "ellipse", **ellipse)
        p.svg_el(shade, "ellipse", **ellipse, class_="bore-wall")
        p.svg_el(shade, "ellipse", cx=p.fmt(center_bottom[0]), cy=p.fmt(center_bottom[1]),
                 rx=p.fmt(rx), ry=p.fmt(ry), class_="face", clip_path=f"url(#{prefix}-opening)")
        p.svg_el(visible, "ellipse", **ellipse, class_="edge", data_feature="top-rim")
        if not flat:
            arc = bottom_visible_arc(block, azimuth, elevation)
            if arc is not None:
                start, end = arc
                p.svg_el(visible, "path", d=arc_path(block, mapping, azimuth, elevation, 0, start, end),
                         class_="edge", data_feature="bottom-rim-visible")
                if hidden == "dash":
                    p.svg_el(concealed, "path", d=arc_path(block, mapping, azimuth, elevation, 0, end, start+2*math.pi),
                             class_="hidden-edge", data_feature="bottom-rim-hidden")
            elif hidden == "dash":
                p.svg_el(concealed, "path", d=arc_path(block, mapping, azimuth, elevation, 0, 0, 2*math.pi),
                         class_="hidden-edge", data_feature="bottom-rim-hidden")
    if not flat and hidden == "dash":
        phi = math.radians(azimuth)-math.pi/2
        for t in (phi+math.pi/2, phi-math.pi/2):
            points = [mapping(p.project([block.rim(t, z)], azimuth, elevation)[0]) for z in (0, block.height)]
            p.svg_el(concealed, "path", d=p.path_data(points), class_="hidden-edge", data_feature="bore-generator")
    # All outer edges of this convex box retain their visibility after boring:
    # a ray entering material at an outside edge is occluded immediately.
    for node in strokes:
        (concealed if node.get("class") == "hidden-edge" else visible).insert(0, node)


def add_style(root):
    style = root.find(f"{{{p.NS}}}style")
    style.text += "\n.bore-wall{fill:var(--ink);fill-opacity:.16}.axis{fill:none;stroke:var(--faint);stroke-width:1;stroke-dasharray:10 3 2 3}\n"


def sheet(block, system, hidden):
    root = p.sheet_svg(block.box, system, hidden)
    add_style(root)
    for group in root.findall(f"{{{p.NS}}}g"):
        name = group.get("data-view")
        if name is None:
            continue
        heading = group.find(f"{{{p.NS}}}text")
        scale = float(group.get("data-scale"))
        azimuth, elevation = {"Alzado": (0, 0), "Planta": (0, 90), "Perfil derecho": (90, 0)}[name]
        left = float(heading.get("x"))-(block.width if name != "Perfil derecho" else block.depth)/block.span*scale/2
        top = float(heading.get("y"))+20
        projected = p.project(block.box.vertices, azimuth, elevation)
        min_x, max_y = min(v[0] for v in projected), max(v[1] for v in projected)
        mapping = lambda v: (left+(v[0]-min_x)*scale, top+(max_y-v[1])*scale)
        decorate(group, block, azimuth, elevation, mapping, hidden, "sheet-"+name.replace(" ", "-"))
        if name == "Planta":
            cx, cy = mapping(p.project([block.normalized((block.cx, block.cy, block.height))], azimuth, elevation)[0])
            rr = block.radius/block.span*scale
            x0, y0 = mapping((min_x, max_y, 0))
            p.svg_el(group, "path", d=f"M{p.fmt(x0-8)},{p.fmt(cy)}h{p.fmt(block.width/block.span*scale+16)} M{p.fmt(cx)},{p.fmt(y0-8)}v{p.fmt(block.depth/block.span*scale+16)}", class_="axis")
            a = (cx+rr/math.sqrt(2), cy-rr/math.sqrt(2))
            b = (cx+rr*1.25, cy-rr*1.25)
            p.svg_el(group, "path", d=p.path_data([a, b]), class_="dimension")
            p.label(group, b[0]+6, b[1]-3, "Ø "+p.fmt_measurement(block.radius*2), "start")
        else:
            center = mapping(p.project([block.normalized((block.cx, block.cy, block.height/2))], azimuth, elevation)[0])
            p.svg_el(group, "path", d=f"M{p.fmt(center[0])},{p.fmt(top-8)}v{p.fmt(block.height/block.span*scale+16)}", class_="axis")
    return root


def view(block, args):
    root = p.view_svg(block.box, args.azimuth, args.elevation, args.hidden)
    add_style(root)
    decorate(root.find(f"{{{p.NS}}}g"), block, args.azimuth, args.elevation, p.angle_mapping(block.box), args.hidden, "view")
    return root


def animation(block, args):
    root = p.animation_svg(block.box, args)
    add_style(root)
    for group in root.iter(f"{{{p.NS}}}g"):
        if group.get("data-frame") is not None:
            index = int(group.get("data-frame"))
            fraction = index/(args.frames if args.loop else args.frames-1)
            decorate(group, block, args.azimuth+args.sweep*fraction, args.elevation, p.angle_mapping(block.box), args.hidden, "frame-"+str(index))
        elif group.get("class") == "still-frame":
            decorate(group, block, args.azimuth, args.elevation, p.angle_mapping(block.box), args.hidden, "still")
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("sheet", "view", "animation", "all"), default="all")
    parser.add_argument("--system", choices=("third", "first"), default="third")
    parser.add_argument("--hidden", choices=("dash", "omit"), default="dash")
    parser.add_argument("--azimuth", type=float, default=45)
    parser.add_argument("--elevation", type=float, default=45)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--sweep", type=float, default=360)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if (not all(math.isfinite(v) for v in (args.azimuth, args.elevation, args.seconds, args.sweep))
        or not 0 <= args.elevation <= 90 or args.seconds <= 0 or not 8 <= args.frames <= 240):
        parser.error("Se requiere elevación entre 0 y 90°, duración positiva y 8..240 fotogramas.")
    try:
        block = BoredBlock(json.loads(args.model.read_text(encoding="utf-8-sig")))
        jobs = []
        if args.mode in ("sheet", "all"):
            jobs.append(("vistas.svg", lambda: sheet(block, args.system, args.hidden)))
        if args.mode in ("view", "all"):
            jobs.append(("angulo.svg", lambda: view(block, args)))
        if args.mode in ("animation", "all"):
            jobs.append(("giro.svg", lambda: animation(block, args)))
        if not args.force and any((args.output_dir/name).exists() for name, _ in jobs):
            raise ValueError("Ya existen archivos de salida; usa otra carpeta o --force.")
        documents = [(name, create()) for name, create in jobs]
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, root in documents:
            path = args.output_dir/name
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
            print(path.resolve())
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        parser.exit(2, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
