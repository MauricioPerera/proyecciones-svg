"""Project small closed polyhedra to editable SVG using only Python's stdlib."""
from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

EPS = 1e-9
MAX_ASPECT = 1e6
MAX_VERTICES = 256
MAX_FACES = 512
MAX_FACE_VERTICES = 64
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def cross2(a, b):
    return a[0]*b[1]-a[1]*b[0]


def length(v):
    return math.sqrt(dot(v, v))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Las coordenadas y medidas deben ser números finitos.")
    return float(value)


def point(value, dimensions):
    if not isinstance(value, list) or len(value) != dimensions:
        raise ValueError(f"Se esperaba un punto de {dimensions} coordenadas.")
    return tuple(number(v) for v in value)


def signed_area(points):
    origin = points[0]
    local = [sub(v, origin) for v in points]
    return math.fsum(cross2(v, local[(i+1) % len(local)]) for i, v in enumerate(local))/2


def local_polygon(points):
    """Use the face's own scale rather than the complete object's scale."""
    origin = points[0]
    local = [sub(v, origin) for v in points]
    span = max(max(v[i] for v in local)-min(v[i] for v in local) for i in range(len(origin)))
    if span <= 0:
        raise ValueError("Perfil o cara sin extensión.")
    return [tuple(x/span for x in v) for v in local]


def segments_intersect(a, b, c, d):
    def side(p, q, r):
        return cross2(sub(q, p), sub(r, p))

    values = (side(a, b, c), side(a, b, d), side(c, d, a), side(c, d, b))
    if values[0]*values[1] < -EPS*EPS and values[2]*values[3] < -EPS*EPS:
        return True
    for value, p, q, r in ((values[0], a, b, c), (values[1], a, b, d),
                            (values[2], c, d, a), (values[3], c, d, b)):
        if abs(value) <= EPS and all(min(x, y)-EPS <= z <= max(x, y)+EPS for x, y, z in zip(p, q, r)):
            return True
    return False


def check_polygon(points):
    count = len(points)
    if count < 3 or len(set(points)) != count:
        raise ValueError("Un perfil/cara necesita al menos tres vértices diferentes, sin repetir el cierre.")
    points = local_polygon(points)
    for i in range(count):
        for j in range(i+1, count):
            if j == i+1 or (i == 0 and j == count-1):
                continue
            if segments_intersect(points[i], points[(i+1) % count], points[j], points[(j+1) % count]):
                raise ValueError("Perfil o cara autointersecante.")
    if abs(signed_area(points)) <= EPS:
        raise ValueError("Perfil o cara de área nula.")


def face_normal(vertices, face):
    local = local_polygon([vertices[index] for index in face])
    vectors = [cross(v, local[(i+1) % len(local)]) for i, v in enumerate(local)]
    total = [math.fsum(v[i] for v in vectors) for i in range(3)]
    size = length(total)
    if size <= EPS:
        raise ValueError("Cara degenerada.")
    return tuple(v/size for v in total)


def triangulate(vertices, face):
    normal = face_normal(vertices, face)
    origin = vertices[face[0]]
    face_span = max(length(sub(vertices[i], origin)) for i in face)
    if any(abs(dot(sub(vertices[i], origin), normal)) > face_span*EPS*100 for i in face):
        raise ValueError("Cara no plana; divídela en caras planas.")
    drop = max(range(3), key=lambda i: abs(normal[i]))
    projected = [tuple(v for j, v in enumerate(vertices[i]) if j != drop) for i in face]
    flat = dict(zip(face, local_polygon(projected)))
    check_polygon([flat[i] for i in face])
    indices = list(face)
    orientation = 1 if signed_area([flat[i] for i in indices]) > 0 else -1
    # Collinear boundary points are preserved in the mesh, omitted in triangulation.
    changed = True
    while changed and len(indices) > 3:
        changed = False
        for k, b in enumerate(indices):
            a, c = indices[k-1], indices[(k+1) % len(indices)]
            if abs(cross2(sub(flat[b], flat[a]), sub(flat[c], flat[b]))) <= EPS:
                indices.pop(k)
                changed = True
                break
    result = []
    while len(indices) > 3:
        for k, b in enumerate(indices):
            a, c = indices[k-1], indices[(k+1) % len(indices)]
            if orientation*cross2(sub(flat[b], flat[a]), sub(flat[c], flat[b])) <= EPS:
                continue
            def inside(i):
                p = flat[i]
                return all(orientation*cross2(sub(flat[v], flat[u]), sub(p, flat[u])) >= -EPS
                           for u, v in ((a, b), (b, c), (c, a)))
            if any(inside(i) for i in indices if i not in (a, b, c)):
                continue
            result.append((a, b, c))
            indices.pop(k)
            break
        else:
            raise ValueError("No se pudo triangular la cara; revisa vértices y autointersecciones.")
    result.append(tuple(indices))
    return normal, result


class Model:
    def __init__(self, data):
        if not isinstance(data, dict):
            raise ValueError("El modelo JSON debe ser un objeto.")
        self.data = data
        self.name = str(data.get("name", "Pieza"))
        self.units = str(data.get("units", "u"))
        if data.get("type") == "extrusion":
            if not isinstance(data.get("profile"), list) or len(data["profile"]) > MAX_FACE_VERTICES:
                raise ValueError(f"El perfil debe ser una lista de hasta {MAX_FACE_VERTICES} puntos.")
            profile = [point(p, 2) for p in data.get("profile", [])]
            depth = number(data.get("depth"))
            if depth <= 0:
                raise ValueError("La profundidad debe ser positiva.")
            if len(profile) < 3:
                raise ValueError("El perfil necesita al menos tres puntos.")
            # Validation is done after normalization, avoiding unit-dependent epsilons.
            if signed_area(profile) < 0:
                profile.reverse()
            vertices = [(x, y, z) for y in (0.0, depth) for x, z in profile]
            n = len(profile)
            faces = [list(range(n)), list(reversed(range(n, 2*n)))]
            faces += [[(i+1) % n, i, i+n, (i+1) % n+n] for i in range(n)]
        elif data.get("type") == "mesh":
            if not isinstance(data.get("vertices"), list) or len(data["vertices"]) > MAX_VERTICES:
                raise ValueError(f"La malla admite hasta {MAX_VERTICES} vértices.")
            vertices = [point(p, 3) for p in data.get("vertices", [])]
            faces = data.get("faces", [])
        else:
            raise ValueError("type debe ser extrusion o mesh.")
        if len(vertices) < 4 or not isinstance(faces, list) or len(faces) < 4:
            raise ValueError("Se necesita un poliedro cerrado con al menos cuatro vértices y caras.")
        if len(faces) > MAX_FACES:
            raise ValueError(f"La malla admite hasta {MAX_FACES} caras.")
        self.minimum = tuple(min(v[i] for v in vertices) for i in range(3))
        self.maximum = tuple(max(v[i] for v in vertices) for i in range(3))
        self.size = sub(self.maximum, self.minimum)
        self.span = max(self.size)
        if self.span <= 0 or not math.isfinite(self.span) or min(self.size) <= 0:
            raise ValueError("La pieza debe tener extensión no nula en los tres ejes.")
        if self.span/min(self.size) > MAX_ASPECT:
            raise ValueError(f"La proporción entre dimensiones supera el límite numérico {MAX_ASPECT:g}:1.")
        center = tuple(a+(b-a)/2 for a, b in zip(self.minimum, self.maximum))
        self.vertices = [tuple((a-b)/self.span for a, b in zip(v, center)) for v in vertices]
        if len(set(self.vertices)) != len(self.vertices):
            raise ValueError("Hay vértices duplicados; comparte sus índices entre caras.")
        self.faces, self.normals, self.triangles = [], [], []
        edge_faces = defaultdict(list)
        directed = defaultdict(int)
        for face in faces:
            if (not isinstance(face, list) or not 3 <= len(face) <= MAX_FACE_VERTICES or
                any(type(i) is not int or i < 0 or i >= len(vertices) for i in face)):
                raise ValueError("Cara con índices inválidos.")
            normal, triangles = triangulate(self.vertices, face)
            face_index = len(self.faces)
            self.faces.append(face)
            self.normals.append(normal)
            self.triangles.extend(triangles)
            for a, b in zip(face, face[1:]+face[:1]):
                edge_faces[tuple(sorted((a, b)))].append(face_index)
                directed[(a, b)] += 1
        if any(len(owners) != 2 for owners in edge_faces.values()):
            raise ValueError("La malla no está cerrada: cada arista debe pertenecer a dos caras.")
        if set(i for face in self.faces for i in face) != set(range(len(self.vertices))):
            raise ValueError("Hay vértices sin usar; elimínalos para no alterar las cotas y la escala.")
        if any(directed[(a, b)] != 1 or directed[(b, a)] != 1 for a, b in edge_faces):
            raise ValueError("Orientación inconsistente: caras vecinas deben recorrer la arista en sentidos opuestos.")
        volume = math.fsum(dot(self.vertices[a], cross(self.vertices[b], self.vertices[c]))
                     for a, b, c in self.triangles)/6
        box_volume = math.prod(value/self.span for value in self.size)
        if abs(volume) <= box_volume*EPS:
            raise ValueError("El poliedro tiene volumen nulo o una orientación inválida.")
        self.edges = [edge for edge, (f, g) in edge_faces.items()
                      if abs(dot(self.normals[f], self.normals[g])) < 1-EPS*10]


def camera(azimuth, elevation):
    a, e = math.radians(azimuth), math.radians(elevation)
    right = (math.cos(a), math.sin(a), 0.0)
    toward = (math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e))
    return right, cross(toward, right), toward


def project(vertices, azimuth, elevation):
    basis = camera(azimuth, elevation)
    return [tuple(dot(v, axis) for axis in basis) for v in vertices]


def occluded_interval(p, q, triangle):
    """Edge parameter interval covered by a closer projected triangle, or None."""
    origin = triangle[0]
    span = max(math.hypot(v[0]-origin[0], v[1]-origin[1]) for v in triangle)
    if span == 0:
        return None
    # A small end face of a long piece still occludes. Evaluate its projected
    # area and depth in local units rather than using a whole-body area cutoff.
    def local(v):
        return tuple((v[i]-origin[i])/span for i in range(3))
    p, q = local(p), local(q)
    triangle = [local(v) for v in triangle]
    a, b, c = triangle
    ab, ac = sub(b, a), sub(c, a)
    determinant = cross2(ab, ac)
    if abs(determinant) <= EPS:
        return None  # An edge-on face has no projected area.
    orientation = 1 if determinant > 0 else -1
    delta = sub(q, p)
    lo, hi = 0.0, 1.0
    for u, v in ((a, b), (b, c), (c, a)):
        side = sub(v, u)
        initial = orientation*cross2(side, sub(p, u))
        slope = orientation*cross2(side, delta)
        if abs(slope) <= EPS:
            if initial < -EPS:
                return None
        elif slope > 0:
            lo = max(lo, -initial/slope)
        else:
            hi = min(hi, -initial/slope)
        if hi-lo <= EPS:
            return None
    kx = (ab[2]*ac[1]-ac[2]*ab[1])/determinant
    ky = (ab[0]*ac[2]-ac[0]*ab[2])/determinant
    difference = a[2]+kx*(p[0]-a[0])+ky*(p[1]-a[1])-p[2]
    slope = kx*delta[0]+ky*delta[1]-delta[2]
    if abs(slope) <= EPS:
        if difference <= EPS*20:
            return None
    elif slope > 0:
        lo = max(lo, (EPS*20-difference)/slope)
    else:
        hi = min(hi, (EPS*20-difference)/slope)
    return (max(0.0, lo), min(1.0, hi)) if hi-lo > EPS else None


def merge_intervals(intervals):
    merged = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1]+EPS*10:
            merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
        else:
            merged.append((lo, hi))
    return merged


def edge_segments(model, projected):
    triangles = [[projected[i] for i in face] for face in model.triangles]
    result = {"visible": [], "hidden": []}
    for i, j in model.edges:
        p, q = projected[i], projected[j]
        if math.hypot(q[0]-p[0], q[1]-p[1]) <= EPS:
            continue
        intervals = merge_intervals([interval for tri in triangles
                                    if (interval := occluded_interval(p, q, tri)) is not None])
        visible, cursor = [], 0.0
        for lo, hi in intervals:
            if lo-cursor > EPS:
                visible.append((cursor, lo))
            cursor = max(cursor, hi)
        if 1-cursor > EPS:
            visible.append((cursor, 1.0))
        for kind, ranges in (("visible", visible), ("hidden", intervals)):
            for lo, hi in ranges:
                endpoints = [tuple(p[k]+t*(q[k]-p[k]) for k in range(2)) for t in (lo, hi)]
                result[kind].append((endpoints[0], endpoints[1]))
    return result


def svg_el(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{NS}}}{tag}", {key.rstrip('_').replace('_', '-'): str(value)
                                                for key, value in attrs.items()})


def fmt(value):
    return f"{value:.4f}".rstrip('0').rstrip('.') if abs(value) > EPS else "0"


def fmt_measurement(value):
    """Physical dimensions retain significant digits regardless of SVG scale."""
    if value == 0:
        return "0"
    text = format(value, ".11e" if abs(value) >= 1e6 else ".12g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        return mantissa.rstrip("0").rstrip(".")+"e"+str(int(exponent))
    return text


def label(parent, x, y, text, anchor="middle", class_="label"):
    node = svg_el(parent, "text", x=fmt(x), y=fmt(y), text_anchor=anchor, class_=class_)
    node.text = text
    return node


def svg_root(model, width, height, description):
    root = ET.Element(f"{{{NS}}}svg", {"viewBox": f"0 0 {width} {height}", "width": str(width),
                                    "height": str(height), "role": "img", "aria-labelledby": "title desc"})
    svg_el(root, "title", id="title").text = model.name
    svg_el(root, "desc", id="desc").text = description
    svg_el(root, "metadata").text = json.dumps(model.data, ensure_ascii=False, allow_nan=False)
    svg_el(root, "style").text = """
      :root { --paper:#fff; --ink:#202a35; --faint:#76818d; }
      @media(prefers-color-scheme:dark) { :root { --paper:#151a20; --ink:#e7edf3; --faint:#a5b0bb; } }
      .paper,.face { fill:var(--paper); stroke:none; }
      .edge { fill:none; stroke:var(--ink); stroke-width:1.65; stroke-linecap:round; stroke-linejoin:round; }
      .hidden-edge { fill:none; stroke:var(--faint); stroke-width:1; stroke-dasharray:5 4; }
      .dimension { fill:none; stroke:var(--faint); stroke-width:1; }
      .label { fill:var(--ink); font:14px Arial,sans-serif; }
      .heading { fill:var(--ink); font:500 18px Arial,sans-serif; }
      .note { fill:var(--faint); font:12px Arial,sans-serif; }
      .still-frame { display:none; }
      @media(prefers-reduced-motion:reduce) { .motion-frames { display:none; } .still-frame { display:inline; } }
    """
    svg_el(root, "rect", width="100%", height="100%", class_="paper")
    return root


def path_data(points, close=False):
    return " ".join(("M" if i == 0 else "L")+fmt(p[0])+","+fmt(p[1]) for i, p in enumerate(points))+(" Z" if close else "")


def draw_projection(parent, model, projected, mapping, hidden):
    for face in model.faces:
        svg_el(parent, "path", d=path_data([mapping(projected[i]) for i in face], True), class_="face")
    segments = edge_segments(model, projected)
    for kind, cls in (("hidden", "hidden-edge"), ("visible", "edge")):
        if kind == "hidden" and hidden == "omit":
            continue
        paths = [path_data([mapping(p), mapping(q)]) for p, q in segments[kind]]
        if paths:
            svg_el(parent, "path", d=" ".join(paths), class_=cls, data_segments=len(paths))


def dimension(parent, p, q, text, vertical=False):
    svg_el(parent, "path", d=path_data([p, q]), class_="dimension")
    for x, y in (p, q):
        marks = [(x-3, y), (x+3, y)] if vertical else [(x, y-3), (x, y+3)]
        svg_el(parent, "path", d=path_data(marks), class_="dimension")
    if vertical:
        label(parent, p[0]-8, (p[1]+q[1])/2+4, text, "end")
    else:
        label(parent, (p[0]+q[0])/2, p[1]+18, text)


def sheet_svg(model, system="third", hidden="dash"):
    width, height, gap = 800, 640, 86
    nx, ny, nz = (n/model.span for n in model.size)
    scale = min((width-180-gap)/(nx+ny), (height-180-gap)/(ny+nz))
    front_size, top_size, right_size = (nx*scale, nz*scale), (nx*scale, ny*scale), (ny*scale, nz*scale)
    if system == "third":
        positions = {"Planta": (90, 100), "Alzado": (90, 100+top_size[1]+gap),
                     "Perfil derecho": (90+front_size[0]+gap, 100+top_size[1]+gap)}
    else:
        positions = {"Perfil derecho": (90, 100), "Alzado": (90+right_size[0]+gap, 100),
                     "Planta": (90+right_size[0]+gap, 100+front_size[1]+gap)}
    system_name = "Tercer diedro" if system == "third" else "Primer diedro"
    root = svg_root(model, width, height, f"Alzado, planta y perfil derecho. {system_name}; cotas generales en {model.units}.")
    label(root, 28, 29, model.name, "start", "heading")
    label(root, 28, 53, f"{system_name} · cotas en {model.units} · ocultas {'discontinuas' if hidden == 'dash' else 'omitidas'}", "start", "note")
    for name, angles, size in (("Planta", (0, 90), top_size), ("Alzado", (0, 0), front_size),
                               ("Perfil derecho", (90, 0), right_size)):
        x, y = positions[name]
        projected = project(model.vertices, *angles)
        low = min(p[0] for p in projected)
        high = max(p[1] for p in projected)
        group = svg_el(root, "g", data_view=name, data_scale=fmt(scale))
        draw_projection(group, model, projected, lambda p: (x+(p[0]-low)*scale, y+(high-p[1])*scale), hidden)
        label(group, x+size[0]/2, y-20, name)
    x, y = positions["Alzado"]
    dimension(root, (x, y+front_size[1]+13), (x+front_size[0], y+front_size[1]+13), fmt_measurement(model.size[0]))
    dimension(root, (x-17, y), (x-17, y+front_size[1]), fmt_measurement(model.size[2]), True)
    x, y = positions["Planta"]
    dimension(root, (x-17, y), (x-17, y+top_size[1]), fmt_measurement(model.size[1]), True)
    x, y = positions["Perfil derecho"]
    dimension(root, (x, y+right_size[1]+13), (x+right_size[0], y+right_size[1]+13), fmt_measurement(model.size[1]))
    label(root, 28, height-18, "Misma escala en las tres vistas · cotas generales", "start", "note")
    return root


def angle_mapping(model, width=640, height=460):
    radius = max(length(v) for v in model.vertices)
    scale = min((width-110)/(2*radius), (height-115)/(2*radius))
    return lambda p: (width/2+p[0]*scale, (height+35)/2-p[1]*scale)


def view_svg(model, azimuth, elevation, hidden):
    root = svg_root(model, 640, 460, f"Proyección ortográfica desde azimut {azimuth:g}°, elevación {elevation:g}°.")
    label(root, 24, 28, model.name, "start", "heading")
    label(root, 24, 51, f"Azimut {azimuth:g}° · elevación {elevation:g}° · ocultas {'discontinuas' if hidden == 'dash' else 'omitidas'}", "start", "note")
    draw_projection(svg_el(root, "g"), model, project(model.vertices, azimuth, elevation), angle_mapping(model), hidden)
    return root


def animation_svg(model, args):
    root = svg_root(model, 640, 460, "Giro ortográfico vectorial calculado por ángulos, con visibilidad recalculada. Alternativa estática si se prefiere movimiento reducido.")
    label(root, 24, 28, model.name, "start", "heading")
    label(root, 24, 51, f"Giro {args.sweep:g}° · elevación {args.elevation:g}° · {args.frames} muestras vectoriales", "start", "note")
    moving = svg_el(root, "g", class_="motion-frames")
    mapping = angle_mapping(model)
    for i in range(args.frames):
        fraction = i/(args.frames if args.loop else args.frames-1)
        azimuth = args.azimuth+args.sweep*fraction
        group = svg_el(moving, "g", visibility="visible" if i == 0 else "hidden", data_frame=i,
                       data_azimuth=fmt(azimuth), data_elevation=fmt(args.elevation))
        draw_projection(group, model, project(model.vertices, azimuth, args.elevation), mapping, args.hidden)
        start, end = i/args.frames, (i+1)/args.frames
        if i == 0:
            times, values = [0, end, 1], ["visible", "hidden", "hidden"]
        elif i == args.frames-1:
            times, values = [0, start, 1], ["hidden", "visible", "visible"]
        else:
            times, values = [0, start, end, 1], ["hidden", "visible", "hidden", "hidden"]
        svg_el(group, "animate", attributeName="visibility", values=";".join(values),
               keyTimes=";".join(f"{t:.9f}" for t in times), calcMode="discrete",
               dur=f"{args.seconds:g}s", repeatCount="indefinite" if args.loop else "1", fill="freeze")
    still = svg_el(root, "g", class_="still-frame")
    draw_projection(still, model, project(model.vertices, args.azimuth, args.elevation), mapping, args.hidden)
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("sheet", "view", "animation", "all"), default="sheet")
    parser.add_argument("--system", choices=("third", "first"), default="third")
    parser.add_argument("--hidden", choices=("dash", "omit"), default="dash")
    parser.add_argument("--azimuth", type=float, default=45)
    parser.add_argument("--elevation", type=float, default=35.2643897)
    parser.add_argument("--frames", type=int, default=72)
    parser.add_argument("--seconds", type=float, default=6)
    parser.add_argument("--sweep", type=float, default=360)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if (not all(math.isfinite(v) for v in (args.azimuth, args.elevation, args.seconds, args.sweep)) or
        not -90 <= args.elevation <= 90 or args.seconds <= 0 or not 8 <= args.frames <= 240):
        parser.error("Ángulos/duración inválidos: elevación -90..90, duración > 0 y 8..240 fotogramas.")
    try:
        model = Model(json.loads(args.model.read_text(encoding="utf-8-sig")))
        jobs = []
        if args.mode in ("sheet", "all"):
            jobs.append(("vistas.svg", lambda: sheet_svg(model, args.system, args.hidden)))
        if args.mode in ("view", "all"):
            jobs.append(("angulo.svg", lambda: view_svg(model, args.azimuth, args.elevation, args.hidden)))
        if args.mode in ("animation", "all"):
            jobs.append(("giro.svg", lambda: animation_svg(model, args)))
        if not args.force:
            collisions = [str(args.output_dir/name) for name, _ in jobs if (args.output_dir/name).exists()]
            if collisions:
                raise ValueError("Ya existen archivos de salida; usa otra carpeta o --force: "+", ".join(collisions))
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
