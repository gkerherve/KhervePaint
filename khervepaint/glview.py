"""OpenGL preview for the Molecule builder — real, GPU-lit 3D.

`GLPreview` is a drop-in replacement for `molview._Preview`'s public
surface (same signals, `rebuild()`), rendering the builder's live
(atoms, bonds[, edges, faces]) with a real depth buffer, Phong lighting
and smooth GLU spheres/cylinders instead of a flat isometric projection.
Orbiting, atom selection and atom-dragging are re-derived on the CPU from
the exact same (az, el) rotation `molecules._proj` uses, so the camera
lines up with the rest of the app's "standard views" — it's just rendered
with a real camera instead of one hand orthographic projection.

Nothing here is persisted: the builder still hands back az/el/bond/atoms
to the canvas on OK, which bakes the *usual* flat, editable vector items
(see `molview.MoleculeViewer.result`). This module only has to look good
while the dialog is open.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QSurfaceFormat
from PyQt5.QtWidgets import QOpenGLWidget

from . import molecules

try:
    from OpenGL import GL, GLU
    GL_AVAILABLE = True
except ImportError:                     # PyOpenGL not installed
    GL_AVAILABLE = False

if GL_AVAILABLE:
    _FMT = QSurfaceFormat()
    # macOS only offers fixed-function (glBegin/glLight/GLU quadrics) under
    # a 2.1 compatibility context — a Core Profile silently drops it all.
    _FMT.setProfile(QSurfaceFormat.CompatibilityProfile)
    _FMT.setVersion(2, 1)
    _FMT.setDepthBufferSize(24)
    _FMT.setSamples(4)
    QSurfaceFormat.setDefaultFormat(_FMT)

_HALF = math.pi / 2.0
_STICK_COLOR = "#6b6f76"
_FRAME_COLOR = "#202020"
_EDGE_COLOR = "#555555"
_SELECT_COLOR = "#2176c7"
_STICK_R = 0.15                          # bond radius, world units


def _hex_rgb(hexcolor):
    c = QColor(hexcolor)
    return c.redF(), c.greenF(), c.blueF()


def _rotation_rows(az, el):
    """The same (world → screen_x, screen_y_up, depth) rotation as
    `molecules._proj`, as three basis rows — reused for both the GL camera
    matrix and CPU-side picking/dragging, so they always agree exactly."""
    ca, sa = math.cos(az), math.sin(az)
    ce, se = math.cos(el), math.sin(el)
    row0 = (ca, -sa, 0.0)
    row1 = (-se * sa, -se * ca, ce)
    row2 = (ce * sa, ce * ca, se)
    return row0, row1, row2


def _dot(row, p):
    return row[0] * p[0] + row[1] * p[1] + row[2] * p[2]


def _gl_matrix(row0, row1, row2):
    """The 4x4 column-major array for `glMultMatrixf` that applies the
    rotation whose rows are (row0, row1, row2) to a world point."""
    return [row0[0], row1[0], row2[0], 0.0,
            row0[1], row1[1], row2[1], 0.0,
            row0[2], row1[2], row2[2], 0.0,
            0.0, 0.0, 0.0, 1.0]


def _face_normal(points):
    if len(points) < 3:
        return (0.0, 0.0, 1.0)
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = points[0], points[1], points[2]
    ux, uy, uz = x1 - x0, y1 - y0, z1 - z0
    vx, vy, vz = x2 - x0, y2 - y0, z2 - z0
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / n, ny / n, nz / n)


def _align_z_to(d):
    """(angle_degrees, axis) rotating the local +Z axis onto unit vector d,
    for `glRotatef` — used to orient a bond cylinder along its bond."""
    dx, dy, dz = d
    axis = (-dy, dx, 0.0)
    n = math.hypot(axis[0], axis[1])
    if n < 1e-8:
        return (0.0, (1.0, 0.0, 0.0)) if dz >= 0 else \
            (180.0, (1.0, 0.0, 0.0))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, dz))))
    return angle, (axis[0] / n, axis[1] / n, 0.0)


def _perp_to(d):
    ref = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (0.0, 1.0, 0.0)
    px = d[1] * ref[2] - d[2] * ref[1]
    py = d[2] * ref[0] - d[0] * ref[2]
    pz = d[0] * ref[1] - d[1] * ref[0]
    n = math.sqrt(px * px + py * py + pz * pz) or 1.0
    return (px / n, py / n, pz / n)


def _build_camera(geom, az, el, rscale, width, height):
    """Fit an orthographic camera to *geom* at view (az, el) — the same
    box-fit `molecules._model` does for the 2D projection, but keeping the
    real 3D rotation rows so GL rendering and CPU picking agree exactly."""
    row0, row1, row2 = _rotation_rows(az, el)
    pts = []
    for a in geom["atoms"]:
        r = molecules.ATOM_RADII.get(a[0], 0.55) * rscale
        pts.append(((a[1], a[2], a[3]), r))
    for p1, p2, _style in geom["edges"]:
        pts.append((p1, 0.0))
        pts.append((p2, 0.0))
    if not pts:
        pts = [((0.0, 0.0, 0.0), 1.0)]
    vxs, vys, depths = [], [], []
    for p, r in pts:
        vx, vy, dz = _dot(row0, p), _dot(row1, p), _dot(row2, p)
        vxs += [vx - r, vx + r]
        vys += [vy - r, vy + r]
        depths += [dz - r, dz + r]
    cx, cy = (min(vxs) + max(vxs)) / 2.0, (min(vys) + max(vys)) / 2.0
    half_w = max((max(vxs) - min(vxs)) / 2.0, 1e-3) * 1.18
    half_h = max((max(vys) - min(vys)) / 2.0, 1e-3) * 1.18
    aspect = max(width, 1) / max(height, 1)
    if half_w / half_h < aspect:
        half_w = half_h * aspect
    else:
        half_h = half_w / aspect
    depth_half = max((max(depths) - min(depths)) / 2.0, 1.0) + 2.0
    cam_dist = depth_half * 3.0 + 20.0
    return {
        "row0": row0, "row1": row1, "row2": row2,
        "left": cx - half_w, "right": cx + half_w,
        "bottom": cy - half_h, "top": cy + half_h,
        "near": cam_dist - depth_half - 5.0,
        "far": cam_dist + depth_half + 5.0,
        "cam_dist": cam_dist, "width": width, "height": height,
        "px_per_unit": width / (2.0 * half_w) if half_w else 1.0,
    }


def _project(cam, p):
    vx, vy, depth = _dot(cam["row0"], p), _dot(cam["row1"], p), \
        _dot(cam["row2"], p)
    sx = (vx - cam["left"]) / (cam["right"] - cam["left"]) * cam["width"]
    sy = (cam["top"] - vy) / (cam["top"] - cam["bottom"]) * cam["height"]
    return sx, sy, depth


class GLPreview(QOpenGLWidget):
    """Renders the model with a real GPU camera. Drag empty space to
    orbit; drag a sphere to move that atom; click a sphere to select it —
    same interaction as the flat preview it replaces."""

    atom_clicked = pyqtSignal(int)          # atom index, or -1 for empty
    rotated = pyqtSignal()
    atom_moved = pyqtSignal()

    def __init__(self, builder, parent=None):
        super().__init__(parent)
        self._b = builder
        self.setMinimumSize(360, 300)
        self._press = None
        self._press_atom = None
        self._mode = None                # None | "orbit" | "drag"
        self._frozen_centroid = None
        self._geom = None
        self._cam = None
        self._quad = None

    # -------------------------------------------------------------- GL
    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.95, 0.95, 0.95, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.35, 0.35, 0.35, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.55, 0.55, 0.55, 1.0])
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR,
                        [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, 48.0)
        GL.glEnable(GL.GL_NORMALIZE)
        GL.glShadeModel(GL.GL_SMOOTH)
        try:
            GL.glEnable(GL.GL_MULTISAMPLE)
        except Exception:
            pass
        self._quad = GLU.gluNewQuadric()
        GLU.gluQuadricNormals(self._quad, GLU.GLU_SMOOTH)

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, max(w, 1), max(h, 1))

    def paintGL(self):
        GL.glClearColor(0.965, 0.968, 0.973, 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        b = self._b
        geom = b.render_geometry(frozen_centroid=self._frozen_centroid)
        self._geom = geom
        cam = _build_camera(geom, b.az, b.el, geom["rscale"],
                            max(self.width(), 1), max(self.height(), 1))
        self._cam = cam

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(cam["left"], cam["right"], cam["bottom"], cam["top"],
                  cam["near"], cam["far"])
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        # a light fixed in eye space (a "headlamp") so the visible side
        # always reads, however the model is orbited
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [-0.3, 0.6, 1.0, 0.0])
        GL.glTranslatef(0.0, 0.0, -cam["cam_dist"])
        GL.glMultMatrixf(_gl_matrix(cam["row0"], cam["row1"], cam["row2"]))

        self._draw_edges(geom["edges"])
        self._draw_bonds(geom["atoms"], geom["bonds"], geom["rscale"])
        self._draw_faces(geom["faces"])
        self._draw_atoms(geom["atoms"], geom["rscale"])

    # ----------------------------------------------------------- drawing
    def _draw_edges(self, edges):
        if not edges:
            return
        GL.glDisable(GL.GL_LIGHTING)
        for p1, p2, style in edges:
            if style == "dash":
                GL.glEnable(GL.GL_LINE_STIPPLE)
                GL.glLineStipple(2, 0x0F0F)
                GL.glColor3f(*_hex_rgb(_EDGE_COLOR))
                GL.glLineWidth(1.6)
            else:
                GL.glColor3f(*_hex_rgb(_FRAME_COLOR))
                GL.glLineWidth(2.4)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(*p1)
            GL.glVertex3f(*p2)
            GL.glEnd()
            if style == "dash":
                GL.glDisable(GL.GL_LINE_STIPPLE)
        GL.glEnable(GL.GL_LIGHTING)

    def _draw_bonds(self, atoms, bonds, rscale):
        r = _STICK_R * rscale
        color = _hex_rgb(_STICK_COLOR)
        for i, j, order in bonds:
            p1 = atoms[i][1:4]
            p2 = atoms[j][1:4]
            d = tuple(p2[k] - p1[k] for k in range(3))
            length = math.sqrt(sum(v * v for v in d))
            if length < 1e-6:
                continue
            dn = tuple(v / length for v in d)
            order = max(1, min(3, order))
            if order == 1:
                rows, rad = [0.0], r
            elif order == 2:
                rows, rad = [-1.0, 1.0], r * 0.62
            else:
                rows, rad = [-1.0, 0.0, 1.0], r * 0.52
            sep = r * 1.7
            perp = _perp_to(dn)
            r1 = molecules.ATOM_RADII.get(atoms[i][0], 0.55) * rscale
            r2 = molecules.ATOM_RADII.get(atoms[j][0], 0.55) * rscale
            for o in rows:
                off = tuple(perp[k] * o * sep for k in range(3))
                a = tuple(p1[k] + off[k] for k in range(3))
                c = tuple(p2[k] + off[k] for k in range(3))
                self._draw_stick(a, c, r1, r2, rad, color, dn)

    def _draw_stick(self, p1, p2, r1, r2, radius, color, dn):
        length = math.sqrt(sum((p2[k] - p1[k]) ** 2 for k in range(3)))
        seg = length - r1 - r2
        if seg <= 0:
            return
        start = tuple(p1[k] + dn[k] * r1 for k in range(3))
        angle, axis = _align_z_to(dn)
        GL.glColor3f(*color)
        GL.glPushMatrix()
        GL.glTranslatef(*start)
        if angle:
            GL.glRotatef(angle, *axis)
        GLU.gluCylinder(self._quad, radius, radius, seg, 14, 1)
        GL.glPopMatrix()

    def _draw_faces(self, faces):
        if not faces:
            return
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glDepthMask(GL.GL_FALSE)
        for points, color in faces:
            r, g, bl = _hex_rgb(color)
            GL.glColor4f(r, g, bl, 0.35)
            GL.glBegin(GL.GL_POLYGON)
            GL.glNormal3f(*_face_normal(points))
            for p in points:
                GL.glVertex3f(*p)
            GL.glEnd()
        GL.glDepthMask(GL.GL_TRUE)
        GL.glDisable(GL.GL_BLEND)

    def _draw_atoms(self, atoms, rscale):
        b = self._b
        for idx, a in enumerate(atoms):
            r = molecules.ATOM_RADII.get(a[0], 0.55) * rscale
            GL.glColor3f(*_hex_rgb(a[4]))
            GL.glPushMatrix()
            GL.glTranslatef(a[1], a[2], a[3])
            GLU.gluSphere(self._quad, r, 28, 20)
            GL.glPopMatrix()
            if idx == b.selected:
                GL.glDisable(GL.GL_LIGHTING)
                GL.glColor3f(*_hex_rgb(_SELECT_COLOR))
                GLU.gluQuadricDrawStyle(self._quad, GLU.GLU_LINE)
                GL.glPushMatrix()
                GL.glTranslatef(a[1], a[2], a[3])
                GLU.gluSphere(self._quad, r * 1.22, 18, 12)
                GL.glPopMatrix()
                GLU.gluQuadricDrawStyle(self._quad, GLU.GLU_FILL)
                GL.glEnable(GL.GL_LIGHTING)

    # -------------------------------------------------------- interaction
    def rebuild(self):
        self.update()

    def _pick(self, x, y):
        if self._cam is None or self._geom is None:
            return None
        best, best_depth = None, None
        for idx, a in enumerate(self._geom["atoms"]):
            radius = molecules.ATOM_RADII.get(a[0], 0.55) * \
                self._geom["rscale"]
            sx, sy, depth = _project(self._cam, a[1:4])
            px_r = radius * self._cam["px_per_unit"]
            if math.hypot(x - sx, y - sy) <= px_r:
                if best_depth is None or depth > best_depth:
                    best, best_depth = idx, depth
        return best

    def _screen_delta_to_world(self, dx, dy):
        b = self._b
        cam = self._cam
        scale = cam["px_per_unit"] * (b.bond or 1.0)
        wx, wy = dx / scale, -dy / scale
        row0, row1 = cam["row0"], cam["row1"]
        return tuple(row0[k] * wx + row1[k] * wy for k in range(3))

    def mousePressEvent(self, event):
        self._press = event.pos()
        self._press_atom = self._pick(event.pos().x(), event.pos().y())
        self._mode = None

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        delta = event.pos() - self._press
        if self._mode is None:
            if abs(delta.x()) + abs(delta.y()) < 4:
                return
            b = self._b
            if self._press_atom is not None and b.editable:
                self._mode = "drag"
                self._frozen_centroid = molecules.centroid_of(b.atoms)
            else:
                self._mode = "orbit"
        self._press = event.pos()
        b = self._b
        if self._mode == "orbit":
            b.az = (b.az + delta.x() * 0.012) % (2 * math.pi)
            b.el = max(-_HALF, min(_HALF, b.el - delta.y() * 0.012))
            self.update()
            self.rotated.emit()
        else:
            d = self._screen_delta_to_world(delta.x(), delta.y())
            atom = b.atoms[self._press_atom]
            atom[1] += d[0]
            atom[2] += d[1]
            atom[3] += d[2]
            self.update()

    def mouseReleaseEvent(self, event):
        if self._mode == "drag":
            self._b.dirty = True
            self._frozen_centroid = None
            self.update()
            self.atom_moved.emit()
        elif self._mode is None and self._press is not None:
            self.atom_clicked.emit(self._press_atom if self._press_atom
                                   is not None else -1)
        self._press = None
        self._mode = None
