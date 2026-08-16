"""
Search Footprint Comparison Widget (File A vs File B)
Multi-projection (XY, XZ, YZ) Footprint Analysis: Absolute Difference, Relative Density & Occupancy.
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

from pastar_rv.metrics import FOOTPRINT_BINS, compute_footprint_data


class CanvasFootprint(QWidget):
    """
    Dual-file 2D Search Footprint Comparison Canvas.
    Visualizes absolute expansion difference, relative exploration density,
    and occupancy metrics across XY, XZ, and YZ projections.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(6)

        # ── 1. Top Metrics Table Banner ──
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; }"
        )
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(8, 6, 8, 6)
        banner_layout.setSpacing(4)

        header_row = QHBoxLayout()
        lbl_banner_title = QLabel("2D Projection Occupancy Metrics & Jaccard Overlap")
        lbl_banner_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_banner_title.setStyleSheet("color: #1e293b;")
        header_row.addWidget(lbl_banner_title)

        lbl_note = QLabel(
            "Note: 2D footprint is a projection of D-dimensional space; "
            "multiple distinct states may map to the same bin."
        )
        lbl_note.setFont(QFont("Segoe UI", 8))
        lbl_note.setStyleSheet("color: #64748b; font-style: italic;")
        header_row.addWidget(lbl_note)
        header_row.addStretch()
        banner_layout.addLayout(header_row)

        self.table_occ = QTableWidget()
        self.table_occ.setColumnCount(7)
        self.table_occ.setHorizontalHeaderLabels(
            [
                "Projection",
                "Occupied Cells (A)",
                "Occupied Cells (B)",
                "Shared Cells",
                "Only in A",
                "Only in B",
                "Jaccard Overlap",
            ]
        )
        self.table_occ.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_occ.setFixedHeight(105)
        self.table_occ.setFont(QFont("Segoe UI", 8))
        banner_layout.addWidget(self.table_occ)

        root_layout.addWidget(banner)

        # ── 2. Grid of Heatmap Projections (3 rows: XY, XZ, YZ) ──
        grid = QGridLayout()
        grid.setSpacing(4)

        self.proj_widgets = []
        rows_def = [
            ("XY (Top: Seq A vs Seq B)", "Seq A (i)", "Seq B (j)"),
            ("XZ (Front: Seq A vs Seq C)", "Seq A (i)", "Seq C (k)"),
            ("YZ (Side: Seq B vs Seq C)", "Seq B (j)", "Seq C (k)"),
        ]

        for r_idx, (r_title, xl, yl) in enumerate(rows_def):
            p_a = pg.PlotWidget(title=f"{r_title} · A (Log Count)")
            p_b = pg.PlotWidget(title=f"{r_title} · B (Log Count)")
            p_diff_abs = pg.PlotWidget(
                title=f"{r_title} · Absolute Difference (Blue=A more | Red=B more)"
            )
            p_diff_rel = pg.PlotWidget(
                title=f"{r_title} · Relative Density Diff (Blue=A denser | Red=B denser)"
            )

            for col_idx, p in enumerate([p_a, p_b, p_diff_abs, p_diff_rel]):
                p.setBackground("w")
                p.setLabel("bottom", xl)
                p.setLabel("left", yl)
                grid.addWidget(p, r_idx, col_idx)

            self.proj_widgets.append((p_a, p_b, p_diff_abs, p_diff_rel))

        root_layout.addLayout(grid)

    def set_data(self, da, db, la="A", lb="B"):
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key

        cA = da.get("coords")
        cB = db.get("coords")
        if cA is None or cB is None or len(cA) == 0 or len(cB) == 0:
            return

        cache_key = (id(da), id(db))
        if cache_key in self._cache:
            fp_xy, fp_xz, fp_yz = self._cache[cache_key]
        else:
            fp_xy = compute_footprint_data(cA, cB, proj_dims=(0, 1), n_bins=FOOTPRINT_BINS)
            fp_xz = compute_footprint_data(cA, cB, proj_dims=(0, 2), n_bins=FOOTPRINT_BINS)
            fp_yz = compute_footprint_data(cA, cB, proj_dims=(1, 2), n_bins=FOOTPRINT_BINS)
            self._cache[cache_key] = (fp_xy, fp_xz, fp_yz)

        pos_plasma = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        col_plasma = np.array(
            [
                [13, 8, 135, 255],
                [126, 3, 168, 255],
                [204, 71, 120, 255],
                [248, 149, 64, 255],
                [240, 249, 33, 255],
            ],
            dtype=np.ubyte,
        )
        lut_plasma = pg.ColorMap(pos_plasma, col_plasma).getLookupTable(0.0, 1.0, 256)

        pos_rdbu = np.array([0.0, 0.5, 1.0])
        col_rdbu = np.array(
            [[31, 119, 180, 255], [255, 255, 255, 255], [214, 39, 40, 255]],
            dtype=np.ubyte,
        )
        lut_rdbu = pg.ColorMap(pos_rdbu, col_rdbu).getLookupTable(0.0, 1.0, 256)

        projs_data = [
            ("XY (Top: Seq A vs Seq B)", fp_xy),
            ("XZ (Front: Seq A vs Seq C)", fp_xz),
            ("YZ (Side: Seq B vs Seq C)", fp_yz),
        ]

        self.table_occ.setRowCount(len(projs_data))
        for r, (p_name, fp) in enumerate(projs_data):
            self.table_occ.setItem(r, 0, QTableWidgetItem(p_name))
            self.table_occ.setItem(r, 1, QTableWidgetItem(f"{fp['n_occupied_a']:,}"))
            self.table_occ.setItem(r, 2, QTableWidgetItem(f"{fp['n_occupied_b']:,}"))
            self.table_occ.setItem(r, 3, QTableWidgetItem(f"{fp['n_shared']:,}"))
            self.table_occ.setItem(r, 4, QTableWidgetItem(f"{fp['n_only_a']:,}"))
            self.table_occ.setItem(r, 5, QTableWidgetItem(f"{fp['n_only_b']:,}"))
            item_j = QTableWidgetItem(f"{fp['jaccard']:.4f}")
            item_j.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_occ.setItem(r, 6, item_j)

        for (p_a, p_b, p_diff_abs, p_diff_rel), (p_name, fp) in zip(
            self.proj_widgets, projs_data, strict=False
        ):
            x0, x1, y0, y1 = fp["extent"]
            rect = pg.QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)

            HA = fp["HA"]
            HB = fp["HB"]
            diff_abs = fp["diff_abs"]
            diff_rel = fp["diff_rel"]

            vmax_raw = max(HA.max(), HB.max(), 1.0)
            img_data_a = np.log1p(HA) / np.log1p(vmax_raw)
            img_data_b = np.log1p(HB) / np.log1p(vmax_raw)

            p_a.clear()
            p_a.setTitle(f"{p_name} · A: {la} ({len(cA):,} nodes)")
            item_a = pg.ImageItem(img_data_a)
            item_a.setLookupTable(lut_plasma)
            item_a.setRect(rect)
            p_a.addItem(item_a)

            p_b.clear()
            p_b.setTitle(f"{p_name} · B: {lb} ({len(cB):,} nodes)")
            item_b = pg.ImageItem(img_data_b)
            item_b.setLookupTable(lut_plasma)
            item_b.setRect(rect)
            p_b.addItem(item_b)

            max_abs = max(abs(diff_abs.min()), abs(diff_abs.max()), 1.0)
            norm_diff_abs = (diff_abs / (2.0 * max_abs)) + 0.5

            p_diff_abs.clear()
            p_diff_abs.setTitle(f"{p_name} · Absolute Exp. Diff (Blue=A more | Red=B more)")
            item_diff_abs = pg.ImageItem(norm_diff_abs)
            item_diff_abs.setLookupTable(lut_rdbu)
            item_diff_abs.setRect(rect)
            p_diff_abs.addItem(item_diff_abs)

            max_rel = max(abs(diff_rel.min()), abs(diff_rel.max()), 1e-6)
            norm_diff_rel = (diff_rel / (2.0 * max_rel)) + 0.5

            p_diff_rel.clear()
            p_diff_rel.setTitle(f"{p_name} · Relative Density Diff (Blue=A denser | Red=B denser)")
            item_diff_rel = pg.ImageItem(norm_diff_rel)
            item_diff_rel.setLookupTable(lut_rdbu)
            item_diff_rel.setRect(rect)
            p_diff_rel.addItem(item_diff_rel)
