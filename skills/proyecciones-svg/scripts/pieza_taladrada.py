"""Analytic vertical or inclined bore through a convex prism with a planar roof."""
from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import proyectar as p


class SlopedBore:
    def __init__(self, data):
        if not isinstance(data, dict) or data.get("type") != "sloped_prism_with_bore":
            raise ValueError("Se esperaba type=sloped_prism_with_bore.")
        footprint = [p.point(v, 2) for v in data.get("footprint", [])]
        if len(footprint) > p.MAX_FACE_VERTICES:
            raise ValueError(f"La base admite hasta {p.MAX_FACE_VERTICES} vértices.")
        if len(footprint) < 3:
            raise ValueError("La base necesita al menos tres vértices.")
        span = max(max(v[i] for v in footprint)-min(v[i] for v in footprint) for i in (0, 1))
        if span <= 0:
            raise ValueError("Base degenerada.")
        normalized = [(x/span, y/span) for x, y in footprint]
        p.check_polygon(normalized)
        if p.signed_area(normalized) < 0:
            footprint.reverse()
        if any(p.cross2(p.sub(footprint[i], footprint[i-1]), p.sub(footprint[(i+1) % len(footprint)], footprint[i])) <= span*span*p.EPS
               for i in range(len(footprint))):
            raise ValueError("Este constructor necesita una base estrictamente convexa, sin vértices colineales.")
        roof = data.get("roof", {})
        self.offset = p.number(roof.get("offset"))
        self.ax = p.number(roof.get("slope_x"))
        self.by = p.number(roof.get("slope_y"))
        if min(self.height(x, y) for x, y in footprint) <= span*p.EPS:
            raise ValueError("Toda la cubierta debe quedar por encima de la base z=0.")
        bore = data.get("bore", {})
        if bore.get("axis") not in ("z", "inclined") or bore.get("through") is not True:
            raise ValueError("Se admite un único taladro pasante con eje z o inclined.")
        self.cx, self.cy = p.point(bore.get("center"), 2)
        self.radius = p.number(bore.get("diameter"))/2
        if self.radius <= 0:
            raise ValueError("El diámetro debe ser positivo.")
        if bore.get("axis") == "z":
            if "direction" in bore:
                raise ValueError("Usa axis=inclined al especificar direction.")
            direction = (0.0, 0.0, 1.0)
        else:
            direction = p.point(bore.get("direction"), 3)
        magnitude = math.hypot(*direction)
        if magnitude <= 0 or direction[2] <= magnitude*1e-7:
            raise ValueError("La dirección debe ser no nula y apuntar hacia z positivo.")
        self.axis = tuple(c/magnitude for c in direction)
        normal = (-self.ax, -self.by, 1.0)
        roof_axis = p.dot(normal, self.axis)
        if roof_axis <= math.hypot(*normal)*1e-7:
            raise ValueError("El eje debe cruzar la base y la cubierta; no puede ser paralelo a ellas.")
        # Orthonormal radial basis: the diameter is measured normal to the axis.
        length_u = math.hypot(self.axis[0], self.axis[2])
        self.u = (self.axis[2]/length_u, 0.0, -self.axis[0]/length_u)
        self.v = p.cross(self.axis, self.u)
        self.hc = self.height(self.cx, self.cy)
        base_center = (self.cx, self.cy, 0.0)
        self.rim_centers = {
            False: base_center,
            True: tuple(base_center[i]+self.hc/roof_axis*self.axis[i] for i in range(3))}
        self.rim_u, self.rim_v = {}, {}
        for top, cap_normal, denominator in ((False, (0.0, 0.0, 1.0), self.axis[2]),
                                             (True, normal, roof_axis)):
            for radial, storage in ((self.u, self.rim_u), (self.v, self.rim_v)):
                along = p.dot(cap_normal, radial)/denominator
                storage[top] = tuple(self.radius*(radial[i]-along*self.axis[i]) for i in range(3))
            # The complete analytic ellipse, including its interior, must clear
            # every lateral half-space. Checking only the axis is insufficient.
            for a, b in zip(footprint, footprint[1:]+footprint[:1]):
                edge = p.sub(b, a)
                length = math.hypot(*edge)
                inward = (-edge[1]/length, edge[0]/length, 0.0)
                distance = p.dot(inward, p.sub(self.rim_centers[top], (*a, 0.0)))
                extent = math.hypot(p.dot(inward, self.rim_u[top]), p.dot(inward, self.rim_v[top]))
                if distance-extent <= span*p.EPS:
                    raise ValueError("Ambas bocas completas del taladro deben quedar dentro de las caras, sin cortar paredes laterales.")
        gap = self.rim_centers[True][2]-self.rim_centers[False][2]
        variation = math.hypot(self.rim_u[True][2]-self.rim_u[False][2],
                               self.rim_v[True][2]-self.rim_v[False][2])
        if gap-variation <= span*p.EPS:
            raise ValueError("Las dos bocas del cilindro deben estar separadas en toda su extensión.")
        n = len(footprint)
        vertices = [[x, y, 0] for x, y in footprint]+[[x, y, self.height(x, y)] for x, y in footprint]
        faces = [list(reversed(range(n))), list(range(n, 2*n))]
        faces += [[i, (i+1) % n, (i+1) % n+n, i+n] for i in range(n)]
        self.body = p.Model({"type": "mesh", "name": data.get("name", "Pieza inclinada con taladro"),
                             "units": data.get("units", "u"), "vertices": vertices, "faces": faces})
        self.body.data = data
        self.footprint = footprint
        self.center = tuple(a+(b-a)/2 for a, b in zip(self.body.minimum, self.body.maximum))
        self.span = self.body.span

    def height(self, x, y):
        return self.offset+self.ax*x+self.by*y

    def normalized(self, point):
        return tuple((a-b)/self.span for a, b in zip(point, self.center))

    def rim(self, t, top=True):
        return tuple(self.rim_centers[top][i]+self.rim_u[top][i]*math.cos(t)
                     +self.rim_v[top][i]*math.sin(t) for i in range(3))


def roof_facing(model, azimuth, elevation):
    direction = p.camera(azimuth, elevation)[2]
    return direction[2]-model.ax*direction[0]-model.by*direction[1]


def bottom_visible_arc(model, azimuth, elevation):
    direction = p.camera(azimuth, elevation)[2]
    normal = (-model.ax, -model.by, 1.0)
    denominator = p.dot(normal, direction)
    if denominator <= p.EPS or direction[2] <= p.EPS:
        return None
    axial = p.dot(direction, model.axis)
    perpendicular = tuple(direction[i]-axial*model.axis[i] for i in range(3))
    radial2 = p.dot(perpendicular, perpendicular)
    if radial2 <= 1e-16:
        return 0.0, 2*math.pi
    constant = model.hc*radial2
    cosine = -p.dot(normal, model.rim_u[False])*radial2+2*denominator*model.radius*p.dot(model.u, direction)
    sine = -p.dot(normal, model.rim_v[False])*radial2+2*denominator*model.radius*p.dot(model.v, direction)
    amplitude = math.hypot(cosine, sine)
    if amplitude <= constant:
        return None
    phase = math.atan2(sine, cosine)
    alpha = math.acos(max(-1.0, min(1.0, -constant/amplitude)))
    return phase+alpha, phase+2*math.pi-alpha


def ellipse_matrix(model, azimuth, elevation, mapping, top=True):
    def project_world(point):
        return mapping(p.project([model.normalized(point)], azimuth, elevation)[0])
    center_world = model.rim_centers[top]
    center = project_world(center_world)
    x = project_world(model.rim(0, top))
    y = project_world(model.rim(math.pi/2, top))
    # A unit circle transformed by this affine matrix is the exact projected rim.
    return (x[0]-center[0], x[1]-center[1], y[0]-center[0], y[1]-center[1], center[0], center[1])


def matrix_text(matrix):
    return "matrix("+" ".join(p.fmt(v) for v in matrix)+")"


def unit_arc(start, end):
    def point(t):
        return p.fmt(math.cos(t))+","+p.fmt(math.sin(t))
    if end-start >= 2*math.pi-1e-8:
        return f"M{point(start)} A1,1 0 0 1 {point((start+end)/2)} A1,1 0 0 1 {point(end)}"
    return f"M{point(start)} A1,1 0 {int(end-start > math.pi)} 1 {point(end)}"


def decorate(parent, model, azimuth, elevation, mapping, hidden, prefix):
    strokes = [node for node in parent if node.get("class") in ("edge", "hidden-edge")]
    for node in strokes:
        parent.remove(node)
    surface = p.svg_el(parent, "g", data_layer="bore-surface")
    concealed = p.svg_el(parent, "g", data_layer="bore-hidden")
    visible = p.svg_el(parent, "g", data_layer="bore-visible")
    top_matrix = matrix_text(ellipse_matrix(model, azimuth, elevation, mapping))
    bottom_matrix = matrix_text(ellipse_matrix(model, azimuth, elevation, mapping, False))
    facing = roof_facing(model, azimuth, elevation) > p.EPS
    direction = p.camera(azimuth, elevation)[2]
    axial_view = abs(p.dot(direction, model.axis)) > 1-1e-12
    if facing:
        defs = p.svg_el(surface, "defs")
        clip = p.svg_el(defs, "clipPath", id=prefix+"-opening", clipPathUnits="userSpaceOnUse")
        p.svg_el(clip, "circle", cx=0, cy=0, r=1, transform=top_matrix)
        p.svg_el(surface, "circle", cx=0, cy=0, r=1, transform=top_matrix, class_="bore-wall")
        if elevation > 1e-8:
            # Clip the *projected* bottom disk against the top disk. Put clipping
            # on an untransformed group, so it uses the same projected coordinates.
            aperture = p.svg_el(surface, "g", clip_path=f"url(#{prefix}-opening)")
            p.svg_el(aperture, "circle", cx=0, cy=0, r=1, transform=bottom_matrix, class_="face")
        p.svg_el(visible, "circle", cx=0, cy=0, r=1, transform=top_matrix,
                 class_="edge curve", data_feature="top-rim")
    elif hidden == "dash":
        p.svg_el(concealed, "circle", cx=0, cy=0, r=1, transform=top_matrix,
                 class_="hidden-edge curve", data_feature="top-rim-hidden")
    if not axial_view:
        arc = bottom_visible_arc(model, azimuth, elevation)
        if arc is not None:
            start, end = arc
            p.svg_el(visible, "path", d=unit_arc(start, end), transform=bottom_matrix,
                     class_="edge curve", data_feature="bottom-rim-visible")
            if hidden == "dash":
                p.svg_el(concealed, "path", d=unit_arc(end, start+2*math.pi), transform=bottom_matrix,
                         class_="hidden-edge curve", data_feature="bottom-rim-hidden")
        elif hidden == "dash" and elevation > 1e-8:
            p.svg_el(concealed, "path", d=unit_arc(0, 2*math.pi), transform=bottom_matrix,
                     class_="hidden-edge curve", data_feature="bottom-rim-hidden")
        if hidden == "dash":
            phase = math.atan2(p.dot(model.v, direction), p.dot(model.u, direction))
            for t in (phase+math.pi/2, phase-math.pi/2):
                points = [mapping(p.project([model.normalized(model.rim(t, top))], azimuth, elevation)[0]) for top in (False, True)]
                p.svg_el(concealed, "path", d=p.path_data(points), class_="hidden-edge", data_feature="bore-generator")
    for node in strokes:
        (concealed if node.get("class") == "hidden-edge" else visible).insert(0, node)


def add_style(root):
    root.find(f"{{{p.NS}}}style").text += "\n.curve{vector-effect:non-scaling-stroke}.bore-wall{fill:var(--ink);fill-opacity:.16}.axis{fill:none;stroke:var(--faint);stroke-width:1;stroke-dasharray:10 3 2 3}\n"


def sheet(model, system, hidden):
    root = p.sheet_svg(model.body, system, hidden)
    add_style(root)
    for group in root.findall(f"{{{p.NS}}}g"):
        name = group.get("data-view")
        if name is None:
            continue
        azimuth, elevation = {"Alzado": (0, 0), "Planta": (0, 90), "Perfil derecho": (90, 0)}[name]
        heading = group.find(f"{{{p.NS}}}text")
        scale = float(group.get("data-scale"))
        width = model.body.size[1] if name == "Perfil derecho" else model.body.size[0]
        left = float(heading.get("x"))-width/model.span*scale/2
        top = float(heading.get("y"))+20
        projected = p.project(model.body.vertices, azimuth, elevation)
        min_x, max_y = min(v[0] for v in projected), max(v[1] for v in projected)
        mapping = lambda v: (left+(v[0]-min_x)*scale, top+(max_y-v[1])*scale)
        decorate(group, model, azimuth, elevation, mapping, hidden, "sheet-"+name.replace(" ", "-"))
        centers = [mapping(p.project([model.normalized(model.rim_centers[cap])], azimuth, elevation)[0]) for cap in (False, True)]
        dx, dy = p.sub(centers[1], centers[0])
        length = math.hypot(dx, dy)
        if length > 1e-6:
            points = [(centers[0][0]-12*dx/length, centers[0][1]-12*dy/length),
                      (centers[1][0]+12*dx/length, centers[1][1]+12*dy/length)]
            p.svg_el(group, "path", d=p.path_data(points), class_="axis", data_feature="bore-axis")
        else:
            cx, cy = centers[1]
            radius = model.radius/model.span*scale+8
            p.svg_el(group, "path", d=f"M{p.fmt(cx-radius)},{p.fmt(cy)}h{p.fmt(2*radius)} M{p.fmt(cx)},{p.fmt(cy-radius)}v{p.fmt(2*radius)}", class_="axis", data_feature="bore-axis")
        if name == "Planta":
            start = mapping(p.project([model.normalized(model.rim(math.pi/4))], azimuth, elevation)[0])
            end = (start[0]+15, start[1]-15)
            p.svg_el(group, "path", d=p.path_data([start, end]), class_="dimension")
            p.label(group, end[0]+6, end[1]-3, "Ø "+p.fmt_measurement(model.radius*2), "start")
    return root


def view(model, args):
    root = p.view_svg(model.body, args.azimuth, args.elevation, args.hidden)
    add_style(root)
    decorate(root.find(f"{{{p.NS}}}g"), model, args.azimuth, args.elevation, p.angle_mapping(model.body), args.hidden, "view")
    return root


def animation(model, args):
    root = p.animation_svg(model.body, args)
    add_style(root)
    for group in root.iter(f"{{{p.NS}}}g"):
        if group.get("data-frame") is not None:
            index = int(group.get("data-frame"))
            azimuth = args.azimuth+args.sweep*index/(args.frames if args.loop else args.frames-1)
            decorate(group, model, azimuth, args.elevation, p.angle_mapping(model.body), args.hidden, "frame-"+str(index))
        elif group.get("class") == "still-frame":
            decorate(group, model, args.azimuth, args.elevation, p.angle_mapping(model.body), args.hidden, "still")
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("sheet", "view", "animation", "all"), default="all")
    parser.add_argument("--system", choices=("third", "first"), default="third")
    parser.add_argument("--hidden", choices=("dash", "omit"), default="dash")
    parser.add_argument("--azimuth", type=float, default=45)
    parser.add_argument("--elevation", type=float, default=50)
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--sweep", type=float, default=360)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if (not all(math.isfinite(v) for v in (args.azimuth, args.elevation, args.seconds, args.sweep))
        or not 0 <= args.elevation <= 90 or args.seconds <= 0 or not 8 <= args.frames <= 240):
        parser.error("Se requiere elevación 0..90°, duración positiva y 8..240 fotogramas.")
    try:
        model = SlopedBore(json.loads(args.model.read_text(encoding="utf-8-sig")))
        jobs = []
        if args.mode in ("sheet", "all"):
            jobs.append(("vistas.svg", lambda: sheet(model, args.system, args.hidden)))
        if args.mode in ("view", "all"):
            jobs.append(("angulo.svg", lambda: view(model, args)))
        if args.mode in ("animation", "all"):
            jobs.append(("giro.svg", lambda: animation(model, args)))
        if not args.force and any((args.output_dir/name).exists() for name, _ in jobs):
            raise ValueError("Ya existen archivos de salida; usa otra carpeta o --force.")
        documents = [(name, create()) for name, create in jobs]
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, root in documents:
            path = args.output_dir/name
            ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
            print(path.resolve())
    except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError) as error:
        parser.exit(2, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
