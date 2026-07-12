#!/usr/bin/env python3
"""
Combine Logo Studio
===================

An interactive PySide6 tool for building Combine "City" logos in the style
of Half-Life 2 -- the broken ring / coil emblem seen on Combine propaganda.
Made primarily for HL2 map makers who want a custom city logo (City 8,
City 24, ...) that matches the canonical construction, exported as a clean
PNG or SVG ready to be turned into a VTF/VMT overlay texture.

Model
-----
The ring is a grid: N equal-angle wedges x M concentric radial "ring"
bands. Every cell in that grid is independently clickable. The number
shown on a wedge is NOT an input -- it's simply a live count of how many
of that wedge's cells are currently filled. The "sum" is the total count
of filled cells across the whole logo. In the canonical City 17 logo that
sum is exactly 17 -- pick your cuts so the sum matches your city number.

Run:
    python3 combine_logo_studio.py

Left click a cell   -> toggle it filled / cut (gap)
Right click a cell  -> pick a new color for just that cell
"""

import sys
import json
import copy
import math
from dataclasses import dataclass, field, asdict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QSpinBox, QSlider, QCheckBox,
    QTableWidget, QHeaderView, QAbstractItemView,
    QColorDialog, QFileDialog, QGroupBox, QComboBox, QMessageBox,
    QToolBar, QStatusBar, QFrame, QSizePolicy, QLineEdit
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QBrush, QImage, QPixmap, QAction,
    QKeySequence, QFont
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QSize

try:
    from PySide6.QtSvg import QSvgGenerator
    HAVE_SVG = True
except Exception:
    HAVE_SVG = False

FONT_FAMILIES = ["Arial", "Segoe UI", "DejaVu Sans", "Liberation Sans", "sans-serif"]

# Built-in preset: the City 17 logo (Half-Life 2). Its wedge counts
# (2 + 3 + 1 + 4 + 3 + 4) sum to exactly 17. Loaded as the default project.
CITY17_PRESET = json.loads(
    '{"segments": [{"color": "#A8700D", "label": "", "cells": '
    '[{"cut": true, "color": ""}, {"cut": true, "color": ""}, {"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": true, "color": ""}], "angle_deg": 75.0}, '
    '{"color": "#A8700D", "label": "", "cells": [{"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}, {"cut": false, "color": ""}, {"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}], "angle_deg": 45.0}, '
    '{"color": "#A8700D", "label": "", "cells": [{"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}, {"cut": true, "color": ""}, {"cut": true, "color": ""}, '
    '{"cut": false, "color": ""}], "angle_deg": 60.0}, '
    '{"color": "#A8700D", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}, '
    '{"cut": false, "color": ""}], "angle_deg": 45.0}, '
    '{"color": "#A8700D", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}], "angle_deg": 90.0}, '
    '{"color": "#A8700D", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": false, "color": ""}, {"cut": false, "color": ""}, '
    '{"cut": true, "color": ""}], "angle_deg": 45.0}], "ring_count": 5, '
    '"inner_ratio": 0.4, "rotation": 15.0, "gap_deg": 0.0, "band_gap_frac": 0.0, '
    '"show_labels": true, "show_sum": false, "show_ticks": true, '
    '"show_cell_borders": true, "show_empty_outline": true, '
    '"fill_direction": "outer_in", "bg_mode": "transparent", "bg_color": "#ffffff"}'
)

# Built-in preset: the City 10 logo (Entropy : Zero). NOTE: its wedge counts
# (2 + 3 + 1 + 1 + 1 + 2 + 2) surprisingly do NOT add up to 10 -- they sum to
# 12. That is intentional and stays that way: the layout matches the exact
# dimensions of the actual Entropy : Zero logo, and fidelity beats numerology.
CITY10_PRESET = json.loads(
    '{"segments": [{"color": "#b83c3b", "label": "", "cells": '
    '[{"cut": false, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}], "angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": true, "color": ""}, '
    '{"cut": true, "color": ""}, {"cut": false, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": true, "color": ""}, {"cut": true, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": true, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}, '
    '{"color": "#b83c3b", "label": "", "cells": [{"cut": false, "color": ""}, '
    '{"cut": false, "color": ""}, {"cut": true, "color": ""}, {"cut": true, "color": ""}], '
    '"angle_deg": 51.42857142857143}], "ring_count": 4, '
    '"inner_ratio": 0.4, "rotation": 0.0, "gap_deg": 0.0, "band_gap_frac": 0.0, '
    '"show_labels": false, "show_sum": false, "show_ticks": false, '
    '"show_cell_borders": false, "show_empty_outline": true, '
    '"fill_direction": "outer_in", "bg_mode": "transparent", "bg_color": "#ffffff"}'
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class RingCell:
    cut: bool = False
    color: str = ""     # "" = inherit the segment's base color


@dataclass
class Segment:
    color: str = "#A8700D"      # base/default color for this wedge's cells
    label: str = ""             # optional override, else shows the live filled count
    cells: list = field(default_factory=list)   # list[RingCell]
    angle_deg: float = None     # angular width; None = "not yet assigned", auto-normalized

    def filled_count(self) -> int:
        return sum(1 for c in self.cells if not c.cut)

    def display_label(self) -> str:
        return self.label if self.label else str(self.filled_count())


def segments_from_dict(data):
    segs = []
    for s in data["segments"]:
        cells = [RingCell(cut=c.get("cut", False), color=c.get("color", ""))
                 for c in s.get("cells", [])]
        segs.append(Segment(color=s.get("color", "#A8700D"), label=s.get("label", ""),
                             cells=cells, angle_deg=s.get("angle_deg")))
    ring_count = data.get("ring_count", 4)
    return segs, ring_count


def default_segments_and_ring_count():
    return segments_from_dict(CITY17_PRESET)


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------
class RingCanvas(QWidget):
    cellClicked = Signal(int, int)      # segment_index, ring_index
    segmentsChanged = Signal()          # live update during interaction (no undo push)
    layoutChanged = Signal()            # discrete edit finished (should push undo)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments, self.ring_count = default_segments_and_ring_count()
        self.inner_ratio = 0.40
        self.rotation = 0.0
        self.gap_deg = 0.0                 # angular gap between wedges
        self.band_gap_frac = 0.0           # radial gap between ring bands (fraction of band width)
        self.show_labels = True
        self.show_ticks = True
        self.show_empty_outline = True     # ghost outline for cut cells (editing aid only)
        self.show_cell_borders = False     # solid outline around filled cells
        self.fill_direction = "outer_in"   # "outer_in" or "inner_out", used by quick-set
        self.bg_mode = "transparent"       # transparent | white | black | custom
        self.bg_color = QColor("#ffffff")
        self.show_sum = False
        self.snap_deg = 5.0                # boundary-drag angle snapping, 0 = off
        self.selected = None               # (seg_idx, ring_idx) or None
        self.hover = None
        self._boundaries = []              # cached (start,end) per segment, math-deg
        self._drag = None                  # active boundary-resize drag state, or None

        self.setMinimumSize(320, 320)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ensure_cells()
        self.normalize_angles()

    # -- data upkeep ---------------------------------------------------
    def ensure_cells(self):
        for seg in self.segments:
            if len(seg.cells) < self.ring_count:
                seg.cells.extend(RingCell() for _ in range(self.ring_count - len(seg.cells)))
            elif len(seg.cells) > self.ring_count:
                del seg.cells[self.ring_count:]

    def total_filled(self) -> int:
        return sum(seg.filled_count() for seg in self.segments)

    def total_cells(self) -> int:
        return len(self.segments) * self.ring_count

    # -- angle management ---------------------------------------------------
    def normalize_angles(self):
        """Ensure every segment has a positive angle_deg and the set sums to
        exactly 360. Safe to call any time; a no-op if already normalized."""
        n = len(self.segments)
        if n == 0:
            return
        for seg in self.segments:
            if not seg.angle_deg or seg.angle_deg <= 0:
                seg.angle_deg = 360.0 / n
        total = sum(seg.angle_deg for seg in self.segments)
        if total <= 0:
            for seg in self.segments:
                seg.angle_deg = 360.0 / n
            return
        scale = 360.0 / total
        if abs(scale - 1.0) > 1e-9:
            for seg in self.segments:
                seg.angle_deg *= scale

    def equalize_angles(self):
        n = len(self.segments)
        if n == 0:
            return
        for seg in self.segments:
            seg.angle_deg = 360.0 / n

    def set_wedge_angle(self, idx, new_angle):
        """Set one wedge's angle exactly, redistributing the remainder
        proportionally among the other wedges. Keeps sum == 360 exactly."""
        n = len(self.segments)
        if n < 2:
            self.segments[idx].angle_deg = 360.0
            return
        min_each = 1.0
        new_angle = max(min_each, min(360.0 - min_each * (n - 1), new_angle))
        remaining = 360.0 - new_angle
        others_sum = sum((s.angle_deg or 0) for k, s in enumerate(self.segments) if k != idx)
        if others_sum <= 0:
            share = remaining / (n - 1)
            for k, s in enumerate(self.segments):
                if k != idx:
                    s.angle_deg = share
        else:
            scale = remaining / others_sum
            for k, s in enumerate(self.segments):
                if k != idx:
                    s.angle_deg = (s.angle_deg or 0) * scale
        self.segments[idx].angle_deg = new_angle

    # -- geometry helpers ---------------------------------------------------
    @staticmethod
    def _polar(cx, cy, r, deg):
        rad = math.radians(deg)
        return QPointF(cx + r * math.cos(rad), cy - r * math.sin(rad))

    def _compute_boundaries(self):
        self.normalize_angles()
        n = len(self.segments)
        boundaries = []
        if n == 0:
            return boundaries
        angle = 90.0 + self.rotation
        for seg in self.segments:
            end = angle
            start = angle - seg.angle_deg
            boundaries.append((start, end))
            angle = start
        return boundaries

    def _build_wedge_path(self, cx, cy, r_in, r_out, start_deg, end_deg):
        path = QPainterPath()
        outer_rect = QRectF(cx - r_out, cy - r_out, 2 * r_out, 2 * r_out)
        inner_rect = QRectF(cx - r_in, cy - r_in, 2 * r_in, 2 * r_in)
        sweep = end_deg - start_deg
        path.moveTo(self._polar(cx, cy, r_out, start_deg))
        path.arcTo(outer_rect, start_deg, sweep)
        path.lineTo(self._polar(cx, cy, r_in, end_deg))
        path.arcTo(inner_rect, end_deg, -sweep)
        path.closeSubpath()
        return path

    def _band_radii(self, inner_r, outer_r):
        """List of (r0, r1) per ring band, index 0 = outermost."""
        span = (outer_r - inner_r) / self.ring_count
        bands = []
        for j in range(self.ring_count):
            r_out_j = outer_r - j * span
            r_in_j = outer_r - (j + 1) * span
            gap = span * self.band_gap_frac / 2
            bands.append((r_in_j + gap, r_out_j - gap))
        return bands

    def _label_font(self, band_thickness):
        f = QFont()
        f.setFamilies(FONT_FAMILIES)
        f.setWeight(QFont.Bold)
        f.setStyleStrategy(QFont.PreferAntialias)
        size = max(8.0, min(34.0, band_thickness * 0.55))
        f.setPointSizeF(size)
        return f

    # -- drawing --------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        self._draw(painter, self.rect())
        painter.end()

    def _draw(self, painter: QPainter, rect, for_export=False):
        self.ensure_cells()
        w, h = rect.width(), rect.height()
        cx, cy = rect.center().x(), rect.center().y()
        margin = 0.14 * min(w, h)
        outer_r = min(w, h) / 2 - margin
        inner_r = outer_r * self.inner_ratio

        if self.bg_mode == "white":
            painter.fillRect(rect, QColor("#ffffff"))
        elif self.bg_mode == "black":
            painter.fillRect(rect, QColor("#000000"))
        elif self.bg_mode == "custom":
            painter.fillRect(rect, self.bg_color)

        self._boundaries = self._compute_boundaries()
        if not self._boundaries:
            return

        bands = self._band_radii(inner_r, outer_r)
        border_pen_color = QColor("#000000") if self.bg_mode != "black" else QColor("#ffffff")
        selected = None if for_export else self.selected
        hover = None if for_export else self.hover
        show_empty_outline = False if for_export else self.show_empty_outline

        # Adjacent filled cells are drawn as separate paths; when they're meant to be
        # perfectly flush (gap = 0) independent antialiasing on each path's edge leaves
        # a faint translucent seam between them. Fix: when NOT drawing a border stroke,
        # inflate each filled cell's geometry by a hairline so touching neighbors overlap
        # slightly instead of exactly kissing. Tiny enough to be invisible once a real
        # gap is requested, but enough to fully cover the antialiasing seam at gap = 0.
        eps_r = 0.0 if self.show_cell_borders else 0.75
        eps_a = 0.0 if self.show_cell_borders else math.degrees(0.75 / max(outer_r, 1))

        for i, (seg, (start, end)) in enumerate(zip(self.segments, self._boundaries)):
            gap = min(self.gap_deg / 2, (end - start) / 2 - 0.05)
            gap = max(gap, 0)
            s2, e2 = start + gap, end - gap
            if e2 <= s2:
                continue
            s_fill, e_fill = s2 - eps_a, e2 + eps_a

            for j, (r0, r1) in enumerate(bands):
                cell = seg.cells[j]
                is_hover = hover == (i, j)
                is_selected = selected == (i, j)

                if not cell.cut:
                    r0_fill = max(r0 - eps_r, 0)
                    r1_fill = r1 + eps_r
                    path = self._build_wedge_path(cx, cy, r0_fill, r1_fill, s_fill, e_fill)
                    color = QColor(cell.color) if cell.color else QColor(seg.color)
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(border_pen_color, 1.0) if self.show_cell_borders else Qt.NoPen)
                    painter.drawPath(path)
                    if is_hover:
                        painter.setBrush(QBrush(QColor(255, 255, 255, 70)))
                        painter.setPen(Qt.NoPen)
                        painter.drawPath(path)
                elif show_empty_outline:
                    path = self._build_wedge_path(cx, cy, r0, r1, s2, e2)
                    painter.setBrush(Qt.NoBrush)
                    painter.setPen(QPen(QColor(120, 120, 120, 130), 1, Qt.DashLine))
                    painter.drawPath(path)
                    if is_hover:
                        painter.setBrush(QBrush(QColor(160, 160, 160, 45)))
                        painter.setPen(Qt.NoPen)
                        painter.drawPath(path)

                if is_selected:
                    sel_path = self._build_wedge_path(cx, cy, r0, r1, s2, e2)
                    painter.setBrush(Qt.NoBrush)
                    painter.setPen(QPen(QColor("#3d9bff"), 2.2, Qt.DashLine))
                    painter.drawPath(sel_path)

            if self.show_labels and seg.filled_count() > 0:
                mid = (s2 + e2) / 2
                rm = (inner_r + outer_r) / 2
                pt = self._polar(cx, cy, rm, mid)
                band_thickness = (outer_r - inner_r) / max(self.ring_count, 1)
                painter.setFont(self._label_font(band_thickness * 1.6))
                painter.setPen(QPen(QColor("#ffffff")))
                painter.drawText(QRectF(pt.x() - 45, pt.y() - 22, 90, 44),
                                  Qt.AlignCenter, seg.display_label())

            if self.show_ticks:
                painter.setPen(QPen(border_pen_color, 1))
                for a in (s2, e2):
                    p0 = self._polar(cx, cy, inner_r * 0.92, a)
                    p1 = self._polar(cx, cy, outer_r + margin * 0.55, a)
                    painter.drawLine(p0, p1)

        if self.show_sum:
            painter.setFont(self._label_font(inner_r * 0.5))
            painter.setPen(QPen(border_pen_color))
            painter.drawText(QRectF(cx - inner_r, cy - inner_r, 2 * inner_r, 2 * inner_r),
                              Qt.AlignCenter, f"sum = {self.total_filled()}")

        if self._drag is not None and not for_export:
            i2 = self._drag["i2"]
            # shared edge = fixed low edge of wedge i2 plus its current angle
            a = self._drag["outerB"] + self.segments[i2].angle_deg
            painter.setPen(QPen(QColor("#3d9bff"), 2.5))
            p0 = self._polar(cx, cy, inner_r * 0.8, a)
            p1 = self._polar(cx, cy, outer_r + margin * 0.75, a)
            painter.drawLine(p0, p1)

    def render_to_image(self, width, height) -> QImage:
        img = QImage(width, height, QImage.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        self._draw(painter, QRectF(0, 0, width, height).toRect(), for_export=True)
        painter.end()
        return img

    def render_to_svg(self, path, width=800, height=800):
        if not HAVE_SVG:
            raise RuntimeError("QtSvg module not available")
        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(QSize(width, height))
        gen.setViewBox(QRectF(0, 0, width, height))
        gen.setTitle("Combine City Logo")
        painter = QPainter(gen)
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw(painter, QRectF(0, 0, width, height).toRect(), for_export=True)
        painter.end()

    # -- interaction ------------------------------------------------------
    def _angle_and_radius(self, pos):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        dx, dy = pos.x() - cx, pos.y() - cy
        r = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(-dy, dx)) % 360
        return angle, r

    def _cell_at(self, pos):
        w, h = self.width(), self.height()
        margin = 0.14 * min(w, h)
        outer_r = min(w, h) / 2 - margin
        inner_r = outer_r * self.inner_ratio
        angle, r = self._angle_and_radius(pos)
        if not (inner_r <= r <= outer_r):
            return None

        angle0 = 90.0 + self.rotation
        diff = (angle0 - angle) % 360
        normalized = angle0 - diff
        seg_idx = None
        for i, (start, end) in enumerate(self._boundaries):
            if start - 1e-6 <= normalized <= end + 1e-6:
                seg_idx = i
                break
        if seg_idx is None:
            return None

        span = (outer_r - inner_r) / self.ring_count
        ring_idx = int((outer_r - r) / span)
        ring_idx = max(0, min(self.ring_count - 1, ring_idx))
        return seg_idx, ring_idx

    def _boundary_at(self, pos):
        """Return the boundary index near pos (the edge between wedge i and
        wedge (i+1)%n), or None. Boundaries are draggable across the full
        ring band plus a little past the outer edge, matching the tick marks."""
        n = len(self.segments)
        if n < 2:
            return None
        w, h = self.width(), self.height()
        margin = 0.14 * min(w, h)
        outer_r = min(w, h) / 2 - margin
        inner_r = outer_r * self.inner_ratio
        angle, r = self._angle_and_radius(pos)
        if not (inner_r * 0.8 <= r <= outer_r + margin * 0.8):
            return None
        if not self._boundaries:
            return None
        tol_deg = math.degrees(7.0 / max(r, 1.0))
        best, best_d = None, None
        for i, (start, _end) in enumerate(self._boundaries):
            diff = abs((angle - start) % 360)
            d = min(diff, 360 - diff)
            if d < tol_deg and (best_d is None or d < best_d):
                best_d, best = d, i
        return best

    def _start_boundary_drag(self, i):
        # The shared edge sits between wedge i (clockwise-before it, higher
        # absolute angle) and wedge i2 (clockwise-after it, lower angle).
        # We capture the two OUTER edges of this pair as fixed absolute angles;
        # only the shared edge between them moves during the drag, so no other
        # wedge is disturbed. For the "seam" (the edge that coincides with the
        # layout anchor at 12 o'clock, i2 == 0) we additionally slide the layout
        # rotation so the anchor tracks the moving seam -- otherwise growing
        # wedge 0 would cascade-shift every downstream wedge.
        n = len(self.segments)
        i2 = (i + 1) % n
        # shared edge = high edge of the "after" wedge = end of seg i2
        S = self._boundaries[i2][1]
        a_i = self.segments[i].angle_deg
        a_i2 = self.segments[i2].angle_deg
        self._drag = {
            "i": i, "i2": i2,
            "S": S,
            "outerA": S + a_i,        # fixed high edge of wedge i
            "outerB": S - a_i2,       # fixed low edge of wedge i2
            "is_seam": (i2 == 0),
        }
        self.setCursor(Qt.SizeHorCursor)

    def _update_boundary_drag(self, event):
        d = self._drag
        angle, _r = self._angle_and_radius(event.position().toPoint())

        # Unwrap the cursor angle to be continuous with the shared edge S,
        # so dragging across the 0/360 or the 12-o'clock seam behaves smoothly.
        S = d["S"]
        t = angle
        while t - S > 180:
            t -= 360
        while t - S < -180:
            t += 360

        outerA, outerB = d["outerA"], d["outerB"]
        min_gap = 1.0

        if self.snap_deg > 0 and not (event.modifiers() & Qt.ShiftModifier):
            snapped = round(t / self.snap_deg) * self.snap_deg
            if outerB + min_gap <= snapped <= outerA - min_gap:
                t = snapped
        t = max(outerB + min_gap, min(outerA - min_gap, t))

        i, i2 = d["i"], d["i2"]
        self.segments[i].angle_deg = outerA - t
        self.segments[i2].angle_deg = t - outerB
        if d["is_seam"]:
            rot = (t - 90.0) % 360.0
            if rot > 180.0:
                rot -= 360.0
            self.rotation = rot
        self.segmentsChanged.emit()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            b = self._boundary_at(event.position().toPoint())
            if b is not None:
                self._start_boundary_drag(b)
                return

        cell = self._cell_at(event.position().toPoint())
        if cell is None:
            return
        i, j = cell
        if event.button() == Qt.LeftButton:
            self.segments[i].cells[j].cut = not self.segments[i].cells[j].cut
            self.selected = cell
            self.cellClicked.emit(i, j)
            self.segmentsChanged.emit()
            self.update()
        elif event.button() == Qt.RightButton:
            current = self.segments[i].cells[j]
            base = QColor(current.color) if current.color else QColor(self.segments[i].color)
            col = QColorDialog.getColor(base, self, "Pick cell color")
            if col.isValid():
                self.segments[i].cells[j].color = col.name()
                self.segments[i].cells[j].cut = False
                self.selected = cell
                self.cellClicked.emit(i, j)
                self.segmentsChanged.emit()
                self.update()

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self._update_boundary_drag(event)
            return

        cell = self._cell_at(event.position().toPoint())
        if cell != self.hover:
            self.hover = cell
            self.update()

        b = self._boundary_at(event.position().toPoint())
        self.setCursor(Qt.SizeHorCursor if b is not None else Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if self._drag is not None and event.button() == Qt.LeftButton:
            self._drag = None
            self.setCursor(Qt.ArrowCursor)
            self.layoutChanged.emit()
            self.update()

    def leaveEvent(self, event):
        self.hover = None
        if self._drag is None:
            self.setCursor(Qt.ArrowCursor)
        self.update()

    # -- quick-set helper -------------------------------------------------
    def set_wedge_filled_count(self, idx, target):
        target = max(0, min(self.ring_count, target))
        seg = self.segments[idx]
        order = range(self.ring_count) if self.fill_direction == "outer_in" \
            else range(self.ring_count - 1, -1, -1)
        order = list(order)
        for rank, ring_idx in enumerate(order):
            seg.cells[ring_idx].cut = not (rank < target)


# ---------------------------------------------------------------------------
# Small preview thumbnail widget
# ---------------------------------------------------------------------------
class PreviewCard(QLabel):
    def __init__(self, bg: QColor, parent=None):
        super().__init__(parent)
        self.bg = bg
        self.setFixedSize(140, 140)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #444; border-radius: 6px;")

    def update_preview(self, canvas: RingCanvas):
        img = QImage(140, 140, QImage.Format_ARGB32)
        img.fill(self.bg)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        canvas._draw(painter, QRectF(0, 0, 140, 140).toRect(), for_export=True)
        painter.end()
        self.setPixmap(QPixmap.fromImage(img))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Combine Logo Studio")
        self.resize(1220, 760)

        self.undo_stack: list[str] = []
        self.redo_stack: list[str] = []
        self._suspend_snapshot = False

        self.canvas = RingCanvas()
        self.canvas.cellClicked.connect(self._on_cell_clicked)
        self.canvas.segmentsChanged.connect(self._on_canvas_changed)
        self.canvas.layoutChanged.connect(self._on_layout_changed)

        self._build_ui()
        self._build_toolbar()
        # Apply the full built-in preset (angles, rotation, borders, ...) so the
        # startup state matches "Load City 17" exactly.
        self._suspend_snapshot = True
        self._restore(json.dumps(CITY17_PRESET))
        self._suspend_snapshot = False
        self._push_undo(initial=True)
        self._refresh_previews()

    # -- UI construction ----------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        layout = QHBoxLayout(central)

        left = QVBoxLayout()
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "background: repeating-conic-gradient(#e9e9e9 0% 25%, #ffffff 0% 50%) 50% / 20px 20px;"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.addWidget(self.canvas)
        left.addWidget(frame, stretch=1)

        hint = QLabel("Left-click a cell: toggle cut/fill.  Right-click a cell: change its color.  "
                      "Drag a wedge boundary line: resize it (hold Shift to ignore snapping).")
        hint.setStyleSheet("color:#888; font-size:11px;")
        left.addWidget(hint)

        prev_row = QHBoxLayout()
        self.preview_light = PreviewCard(QColor("#ffffff"))
        self.preview_dark = PreviewCard(QColor("#1e1e1e"))
        for card, name in ((self.preview_light, "On light"), (self.preview_dark, "On dark")):
            col = QVBoxLayout()
            lab = QLabel(name)
            lab.setAlignment(Qt.AlignCenter)
            col.addWidget(card)
            col.addWidget(lab)
            prev_row.addLayout(col)
        prev_row.addStretch()
        left.addLayout(prev_row)

        layout.addLayout(left, stretch=3)

        right = QVBoxLayout()
        right.addWidget(self._build_segment_group())
        right.addWidget(self._build_appearance_group())
        right.addWidget(self._build_presets_group())
        right.addStretch()
        right_container = QWidget()
        right_container.setLayout(right)
        right_container.setFixedWidth(380)
        layout.addWidget(right_container)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self._update_status()

    def _build_segment_group(self):
        box = QGroupBox("Segments (wedges)")
        v = QVBoxLayout(box)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Filled", "Angle", "Color", "Set to", "Label"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        v.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add wedge")
        add_btn.clicked.connect(self._add_segment)
        dup_btn = QPushButton("Duplicate")
        dup_btn.clicked.connect(self._duplicate_segment)
        rem_btn = QPushButton("Remove")
        rem_btn.clicked.connect(self._remove_segment)
        up_btn = QPushButton("↑")
        up_btn.setFixedWidth(30)
        up_btn.clicked.connect(lambda: self._move_segment(-1))
        down_btn = QPushButton("↓")
        down_btn.setFixedWidth(30)
        down_btn.clicked.connect(lambda: self._move_segment(1))
        for b in (add_btn, dup_btn, rem_btn, up_btn, down_btn):
            btn_row.addWidget(b)
        v.addLayout(btn_row)

        self.sum_label = QLabel("Sum: 0")
        self.sum_label.setStyleSheet("font-weight:bold;")
        v.addWidget(self.sum_label)

        return box

    def _build_appearance_group(self):
        box = QGroupBox("Appearance")
        grid = QGridLayout(box)
        row = 0

        grid.addWidget(QLabel("Rings per wedge"), row, 0)
        self.rings_spin = QSpinBox()
        self.rings_spin.setRange(1, 12)
        self.rings_spin.setValue(self.canvas.ring_count)
        self.rings_spin.valueChanged.connect(self._on_ring_count_changed)
        grid.addWidget(self.rings_spin, row, 1)
        row += 1

        grid.addWidget(QLabel("Ring thickness"), row, 0)
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setRange(5, 90)
        self.thickness_slider.setValue(int(self.canvas.inner_ratio * 100))
        self.thickness_slider.valueChanged.connect(self._on_thickness_changed)
        grid.addWidget(self.thickness_slider, row, 1)
        row += 1

        grid.addWidget(QLabel("Rotation"), row, 0)
        self.rotation_slider = QSlider(Qt.Horizontal)
        self.rotation_slider.setRange(-180, 180)
        self.rotation_slider.setValue(int(self.canvas.rotation))
        self.rotation_slider.valueChanged.connect(self._on_rotation_changed)
        grid.addWidget(self.rotation_slider, row, 1)
        row += 1

        grid.addWidget(QLabel("Wedge gap"), row, 0)
        self.gap_slider = QSlider(Qt.Horizontal)
        self.gap_slider.setRange(0, 30)
        self.gap_slider.setValue(int(self.canvas.gap_deg))
        self.gap_slider.valueChanged.connect(self._on_gap_changed)
        grid.addWidget(self.gap_slider, row, 1)
        row += 1

        grid.addWidget(QLabel("Ring band gap"), row, 0)
        self.band_gap_slider = QSlider(Qt.Horizontal)
        self.band_gap_slider.setRange(0, 40)
        self.band_gap_slider.setValue(int(self.canvas.band_gap_frac * 100))
        self.band_gap_slider.valueChanged.connect(self._on_band_gap_changed)
        grid.addWidget(self.band_gap_slider, row, 1)
        row += 1

        grid.addWidget(QLabel("Quick-set fill direction"), row, 0)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Outer -> in", "Inner -> out"])
        self.direction_combo.currentIndexChanged.connect(self._on_direction_changed)
        grid.addWidget(self.direction_combo, row, 1)
        row += 1

        grid.addWidget(QLabel("Wedge resize snap"), row, 0)
        self.snap_spin = QSpinBox()
        self.snap_spin.setRange(0, 45)
        self.snap_spin.setSuffix("°")
        self.snap_spin.setSpecialValueText("Off")
        self.snap_spin.setValue(int(self.canvas.snap_deg))
        self.snap_spin.valueChanged.connect(self._on_snap_changed)
        grid.addWidget(self.snap_spin, row, 1)
        row += 1

        equalize_btn = QPushButton("Equalize wedge angles")
        equalize_btn.clicked.connect(self._equalize_angles)
        grid.addWidget(equalize_btn, row, 0, 1, 2)
        row += 1

        self.labels_cb = QCheckBox("Show value labels")
        self.labels_cb.setChecked(True)
        self.labels_cb.stateChanged.connect(self._on_toggle_options)
        grid.addWidget(self.labels_cb, row, 0, 1, 2)
        row += 1

        self.sum_cb = QCheckBox("Show sum in center")
        self.sum_cb.setChecked(False)
        self.sum_cb.stateChanged.connect(self._on_toggle_options)
        grid.addWidget(self.sum_cb, row, 0, 1, 2)
        row += 1

        self.ticks_cb = QCheckBox("Show boundary ticks")
        self.ticks_cb.setChecked(True)
        self.ticks_cb.stateChanged.connect(self._on_toggle_options)
        grid.addWidget(self.ticks_cb, row, 0, 1, 2)
        row += 1

        self.borders_cb = QCheckBox("Show cell borders (off = seamless fill)")
        self.borders_cb.setChecked(False)
        self.borders_cb.stateChanged.connect(self._on_toggle_options)
        grid.addWidget(self.borders_cb, row, 0, 1, 2)
        row += 1

        self.outline_cb = QCheckBox("Show ghost outline on cut cells (editing only, never exported)")
        self.outline_cb.setChecked(True)
        self.outline_cb.stateChanged.connect(self._on_toggle_options)
        grid.addWidget(self.outline_cb, row, 0, 1, 2)
        row += 1

        grid.addWidget(QLabel("Background"), row, 0)
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Transparent", "White", "Black", "Custom…"])
        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)
        grid.addWidget(self.bg_combo, row, 1)
        row += 1

        apply_all_btn = QPushButton("Apply one color to all wedges")
        apply_all_btn.clicked.connect(self._apply_color_all)
        grid.addWidget(apply_all_btn, row, 0, 1, 2)
        row += 1

        fill_all_btn = QPushButton("Fill every cell")
        fill_all_btn.clicked.connect(lambda: self._set_all_cells(cut=False))
        grid.addWidget(fill_all_btn, row, 0)
        cut_all_btn = QPushButton("Cut every cell")
        cut_all_btn.clicked.connect(lambda: self._set_all_cells(cut=True))
        grid.addWidget(cut_all_btn, row, 1)

        return box

    def _build_presets_group(self):
        box = QGroupBox("Presets / Project")
        v = QVBoxLayout(box)

        row1 = QHBoxLayout()
        c17_btn = QPushButton("Load City 17")
        c17_btn.setToolTip("The canonical Half-Life 2 logo — its wedge counts sum to exactly 17.")
        c17_btn.clicked.connect(lambda: self._load_preset(CITY17_PRESET))
        c10_btn = QPushButton("Load City 10")
        c10_btn.setToolTip("The Entropy : Zero logo. Surprisingly its wedge counts do NOT add up "
                           "to 10 — they sum to 12. Kept that way on purpose so the layout matches "
                           "the exact dimensions of the actual Entropy : Zero logo.")
        c10_btn.clicked.connect(lambda: self._load_preset(CITY10_PRESET))
        rand_btn = QPushButton("Randomize cuts")
        rand_btn.clicked.connect(self._randomize_cuts)
        row1.addWidget(c17_btn)
        row1.addWidget(c10_btn)
        row1.addWidget(rand_btn)
        v.addLayout(row1)

        row2 = QHBoxLayout()
        save_btn = QPushButton("Save Project…")
        save_btn.clicked.connect(self._save_project)
        load_btn = QPushButton("Open Project…")
        load_btn.clicked.connect(self._open_project)
        row2.addWidget(save_btn)
        row2.addWidget(load_btn)
        v.addLayout(row2)

        row3 = QHBoxLayout()
        png_btn = QPushButton("Export PNG…")
        png_btn.clicked.connect(self._export_png)
        svg_btn = QPushButton("Export SVG…")
        svg_btn.clicked.connect(self._export_svg)
        row3.addWidget(png_btn)
        row3.addWidget(svg_btn)
        v.addLayout(row3)

        copy_btn = QPushButton("Copy PNG to clipboard")
        copy_btn.clicked.connect(self._copy_clipboard)
        v.addWidget(copy_btn)

        return box

    def _build_toolbar(self):
        tb = QToolBar("Main")
        self.addToolBar(tb)

        undo_act = QAction("Undo", self)
        undo_act.setShortcut(QKeySequence.Undo)
        undo_act.triggered.connect(self._undo)
        tb.addAction(undo_act)

        redo_act = QAction("Redo", self)
        redo_act.setShortcut(QKeySequence.Redo)
        redo_act.triggered.connect(self._redo)
        tb.addAction(redo_act)

        tb.addSeparator()

        new_act = QAction("New", self)
        new_act.triggered.connect(self._new_project)
        tb.addAction(new_act)

    # -- table sync -----------------------------------------------------
    def _refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.canvas.segments))
        for i, seg in enumerate(self.canvas.segments):
            filled_lbl = QLabel(f"{seg.filled_count()} / {self.canvas.ring_count}")
            filled_lbl.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(i, 0, filled_lbl)

            angle_cell = QWidget()
            al = QHBoxLayout(angle_cell)
            al.setContentsMargins(2, 2, 2, 2)
            angle_spin = QSpinBox()
            angle_spin.setRange(1, 359)
            angle_spin.setSuffix("°")
            angle_spin.setValue(round(seg.angle_deg or 0))
            angle_spin.setFixedWidth(60)
            angle_set_btn = QPushButton("Set")
            angle_set_btn.setFixedWidth(32)
            angle_set_btn.clicked.connect(
                lambda _, idx=i, sp=angle_spin: self._set_angle(idx, sp.value()))
            al.addWidget(angle_spin)
            al.addWidget(angle_set_btn)
            self.table.setCellWidget(i, 1, angle_cell)

            color_btn = QPushButton()
            color_btn.setFixedWidth(36)
            color_btn.setStyleSheet(f"background-color:{seg.color};")
            color_btn.clicked.connect(lambda _, idx=i: self._pick_base_color(idx))
            self.table.setCellWidget(i, 2, color_btn)

            cell = QWidget()
            l = QHBoxLayout(cell)
            l.setContentsMargins(2, 2, 2, 2)
            spin = QSpinBox()
            spin.setRange(0, self.canvas.ring_count)
            spin.setValue(seg.filled_count())
            spin.setFixedWidth(40)
            set_btn = QPushButton("Set")
            set_btn.setFixedWidth(32)
            set_btn.clicked.connect(lambda _, idx=i, sp=spin: self._quick_set(idx, sp.value()))
            l.addWidget(spin)
            l.addWidget(set_btn)
            self.table.setCellWidget(i, 3, cell)

            label_edit = QLineEdit(seg.label)
            label_edit.setPlaceholderText(str(seg.filled_count()))
            label_edit.textChanged.connect(lambda text, idx=i: self._set_label(idx, text))
            self.table.setCellWidget(i, 4, label_edit)

        self.table.blockSignals(False)
        self._update_sum()

    def _update_sum(self):
        self.sum_label.setText(
            f"Sum: {self.canvas.total_filled()} filled / {self.canvas.total_cells()} cells "
            f"({len(self.canvas.segments)} wedges x {self.canvas.ring_count} rings)"
        )

    def _update_status(self):
        msg = (f"{len(self.canvas.segments)} wedges x {self.canvas.ring_count} rings | "
               f"sum = {self.canvas.total_filled()} / {self.canvas.total_cells()}")
        drag = self.canvas._drag
        if drag is not None:
            i, i2 = drag["i"], drag["i2"]
            a1 = self.canvas.segments[i].angle_deg
            a2 = self.canvas.segments[i2].angle_deg
            msg += f"   |   resizing wedges {i + 1} & {i2 + 1}: {a1:.1f}° / {a2:.1f}°"
        self.statusBar().showMessage(msg)

    def _refresh_previews(self):
        self.preview_light.update_preview(self.canvas)
        self.preview_dark.update_preview(self.canvas)

    # -- segment table callbacks -----------------------------------------
    def _set_label(self, idx, text):
        self.canvas.segments[idx].label = text
        self._commit(refresh_table=False)

    def _pick_base_color(self, idx):
        col = QColorDialog.getColor(QColor(self.canvas.segments[idx].color), self)
        if col.isValid():
            self.canvas.segments[idx].color = col.name()
            self._commit()

    def _quick_set(self, idx, target):
        self.canvas.set_wedge_filled_count(idx, target)
        self._commit()

    def _set_angle(self, idx, target):
        self.canvas.set_wedge_angle(idx, float(target))
        self._commit()

    def _on_table_selection(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            self.canvas.selected = (rows[0].row(), 0)
        else:
            self.canvas.selected = None
        self.canvas.update()

    def _on_cell_clicked(self, seg_idx, ring_idx):
        self.table.blockSignals(True)
        self.table.selectRow(seg_idx)
        self.table.blockSignals(False)
        self._commit(push_undo=True, refresh_table=True)

    def _on_layout_changed(self):
        # A boundary drag just finished -- commit it as one undo-able step.
        # A seam drag can also change rotation, so keep that slider in sync.
        self._suspend_snapshot = True
        self.rotation_slider.blockSignals(True)
        self.rotation_slider.setValue(int(round(self.canvas.rotation)))
        self.rotation_slider.blockSignals(False)
        self._suspend_snapshot = False
        self._commit(push_undo=True, refresh_table=True)

    def _on_canvas_changed(self):
        self._refresh_previews()
        self._update_status()

    # -- segment list ops -------------------------------------------------
    def _add_segment(self):
        self.canvas.segments.append(Segment(color="#A8700D"))
        self.canvas.ensure_cells()
        self.canvas.normalize_angles()   # new wedge takes a proportional share from all
        self._commit()

    def _duplicate_segment(self):
        rows = self.table.selectionModel().selectedRows()
        idx = rows[0].row() if rows else len(self.canvas.segments) - 1
        if 0 <= idx < len(self.canvas.segments):
            seg = copy.deepcopy(self.canvas.segments[idx])
            half = (self.canvas.segments[idx].angle_deg or 0) / 2
            self.canvas.segments[idx].angle_deg = half
            seg.angle_deg = half
            self.canvas.segments.insert(idx + 1, seg)   # splits the wedge in two, others untouched
            self._commit()

    def _remove_segment(self):
        rows = self.table.selectionModel().selectedRows()
        idx = rows[0].row() if rows else len(self.canvas.segments) - 1
        if len(self.canvas.segments) > 1 and 0 <= idx < len(self.canvas.segments):
            del self.canvas.segments[idx]
            self.canvas.normalize_angles()   # freed angle redistributes proportionally
            self._commit()

    def _move_segment(self, direction):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        new_idx = idx + direction
        if 0 <= new_idx < len(self.canvas.segments):
            segs = self.canvas.segments
            segs[idx], segs[new_idx] = segs[new_idx], segs[idx]
            self._commit()
            self.table.selectRow(new_idx)

    def _apply_color_all(self):
        col = QColorDialog.getColor(QColor(self.canvas.segments[0].color), self)
        if col.isValid():
            for seg in self.canvas.segments:
                seg.color = col.name()
                for c in seg.cells:
                    c.color = ""
            self._commit()

    def _set_all_cells(self, cut: bool):
        for seg in self.canvas.segments:
            for c in seg.cells:
                c.cut = cut
        self._commit()

    # -- appearance callbacks ----------------------------------------------
    def _on_ring_count_changed(self, val):
        self.canvas.ring_count = val
        self.canvas.ensure_cells()
        self._commit(push_undo=True, refresh_table=True)

    def _on_thickness_changed(self, val):
        self.canvas.inner_ratio = val / 100.0
        self._commit(push_undo=False, refresh_table=False)

    def _on_rotation_changed(self, val):
        self.canvas.rotation = float(val)
        self._commit(push_undo=False, refresh_table=False)

    def _on_gap_changed(self, val):
        self.canvas.gap_deg = float(val)
        self._commit(push_undo=False, refresh_table=False)

    def _on_band_gap_changed(self, val):
        self.canvas.band_gap_frac = val / 100.0
        self._commit(push_undo=False, refresh_table=False)

    def _on_direction_changed(self, index):
        self.canvas.fill_direction = "outer_in" if index == 0 else "inner_out"
        self._commit(push_undo=False, refresh_table=False)

    def _on_snap_changed(self, val):
        self.canvas.snap_deg = float(val)

    def _equalize_angles(self):
        self.canvas.equalize_angles()
        self._commit()

    def _on_toggle_options(self):
        self.canvas.show_labels = self.labels_cb.isChecked()
        self.canvas.show_sum = self.sum_cb.isChecked()
        self.canvas.show_ticks = self.ticks_cb.isChecked()
        self.canvas.show_cell_borders = self.borders_cb.isChecked()
        self.canvas.show_empty_outline = self.outline_cb.isChecked()
        self._commit(push_undo=False, refresh_table=False)

    def _on_bg_changed(self, index):
        mapping = {0: "transparent", 1: "white", 2: "black", 3: "custom"}
        mode = mapping.get(index, "transparent")
        if mode == "custom":
            col = QColorDialog.getColor(self.canvas.bg_color, self)
            if col.isValid():
                self.canvas.bg_color = col
        self.canvas.bg_mode = mode
        self._commit(push_undo=False, refresh_table=False)

    # -- presets -----------------------------------------------------------
    def _load_preset(self, preset):
        # Restore the full preset so angles, rotation, borders and all other
        # settings come along -- not just the segments and ring count.
        self._restore(json.dumps(preset))
        self._push_undo()

    def _randomize_cuts(self):
        import random
        for seg in self.canvas.segments:
            for c in seg.cells:
                c.cut = random.random() < 0.3
        self._commit()

    def _new_project(self):
        self.canvas.segments = [Segment(color="#A8700D") for _ in range(7)]
        self.canvas.ring_count = 4
        self.canvas.ensure_cells()
        self.canvas.normalize_angles()
        self.canvas.selected = None
        self._suspend_snapshot = True
        self.rings_spin.setValue(4)
        self._suspend_snapshot = False
        self._commit()

    # -- commit / undo -------------------------------------------------
    def _commit(self, push_undo=True, refresh_table=True):
        if refresh_table:
            self._refresh_table()
        self.canvas.update()
        self._refresh_previews()
        self._update_status()
        if push_undo and not self._suspend_snapshot:
            self._push_undo()

    def _snapshot(self):
        return json.dumps({
            "segments": [asdict(s) for s in self.canvas.segments],
            "ring_count": self.canvas.ring_count,
            "inner_ratio": self.canvas.inner_ratio,
            "rotation": self.canvas.rotation,
            "gap_deg": self.canvas.gap_deg,
            "band_gap_frac": self.canvas.band_gap_frac,
            "show_labels": self.canvas.show_labels,
            "show_sum": self.canvas.show_sum,
            "show_ticks": self.canvas.show_ticks,
            "show_cell_borders": self.canvas.show_cell_borders,
            "show_empty_outline": self.canvas.show_empty_outline,
            "fill_direction": self.canvas.fill_direction,
            "bg_mode": self.canvas.bg_mode,
            "bg_color": self.canvas.bg_color.name(),
        })

    def _restore(self, snap_json):
        data = json.loads(snap_json)
        segs, ring_count = segments_from_dict(data)
        self.canvas.segments = segs
        self.canvas.ring_count = ring_count
        self.canvas.inner_ratio = data.get("inner_ratio", 0.4)
        self.canvas.rotation = data.get("rotation", 0.0)
        self.canvas.gap_deg = data.get("gap_deg", 0.0)
        self.canvas.band_gap_frac = data.get("band_gap_frac", 0.0)
        self.canvas.show_labels = data.get("show_labels", True)
        self.canvas.show_sum = data.get("show_sum", False)
        self.canvas.show_ticks = data.get("show_ticks", True)
        self.canvas.show_cell_borders = data.get("show_cell_borders", False)
        self.canvas.show_empty_outline = data.get("show_empty_outline", True)
        self.canvas.fill_direction = data.get("fill_direction", "outer_in")
        self.canvas.bg_mode = data.get("bg_mode", "transparent")
        self.canvas.bg_color = QColor(data.get("bg_color", "#ffffff"))
        self.canvas.selected = None
        self.canvas.ensure_cells()
        self.canvas.normalize_angles()

        self._suspend_snapshot = True
        self.rings_spin.setValue(self.canvas.ring_count)
        self.thickness_slider.setValue(int(self.canvas.inner_ratio * 100))
        self.rotation_slider.setValue(int(self.canvas.rotation))
        self.gap_slider.setValue(int(self.canvas.gap_deg))
        self.band_gap_slider.setValue(int(self.canvas.band_gap_frac * 100))
        self.direction_combo.setCurrentIndex(0 if self.canvas.fill_direction == "outer_in" else 1)
        self.labels_cb.setChecked(self.canvas.show_labels)
        self.sum_cb.setChecked(self.canvas.show_sum)
        self.ticks_cb.setChecked(self.canvas.show_ticks)
        self.borders_cb.setChecked(self.canvas.show_cell_borders)
        self.outline_cb.setChecked(self.canvas.show_empty_outline)
        bg_index = {"transparent": 0, "white": 1, "black": 2, "custom": 3}.get(
            self.canvas.bg_mode, 0)
        self.bg_combo.setCurrentIndex(bg_index)
        self.snap_spin.setValue(int(self.canvas.snap_deg))
        self._refresh_table()
        self.canvas.update()
        self._refresh_previews()
        self._update_status()
        self._suspend_snapshot = False

    def _push_undo(self, initial=False):
        snap = self._snapshot()
        if self.undo_stack and self.undo_stack[-1] == snap:
            return
        self.undo_stack.append(snap)
        if not initial:
            self.redo_stack.clear()

    def _undo(self):
        if len(self.undo_stack) <= 1:
            return
        self.redo_stack.append(self.undo_stack.pop())
        self._restore(self.undo_stack[-1])

    def _redo(self):
        if not self.redo_stack:
            return
        snap = self.redo_stack.pop()
        self.undo_stack.append(snap)
        self._restore(snap)

    # -- file operations -----------------------------------------------
    def _save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "logo.json",
                                               "JSON Project (*.json)")
        if not path:
            return
        with open(path, "w") as f:
            f.write(self._snapshot())
        self.statusBar().showMessage(f"Saved {path}", 3000)

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "",
                                               "JSON Project (*.json)")
        if not path:
            return
        with open(path) as f:
            self._restore(f.read())
        self._push_undo()
        self.statusBar().showMessage(f"Loaded {path}", 3000)

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "logo.png",
                                               "PNG Image (*.png)")
        if not path:
            return
        img = self.canvas.render_to_image(1024, 1024)
        img.save(path)
        self.statusBar().showMessage(f"Exported {path}", 3000)

    def _export_svg(self):
        if not HAVE_SVG:
            QMessageBox.warning(self, "SVG unavailable", "QtSvg module is not installed.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "logo.svg",
                                               "SVG Image (*.svg)")
        if not path:
            return
        self.canvas.render_to_svg(path, 1024, 1024)
        self.statusBar().showMessage(f"Exported {path}", 3000)

    def _copy_clipboard(self):
        img = self.canvas.render_to_image(1024, 1024)
        QApplication.clipboard().setPixmap(QPixmap.fromImage(img))
        self.statusBar().showMessage("Copied to clipboard", 2000)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
