"""
Search Footprint Comparison Widget (CanvasFootprint)
Pairwise Projections Matrix (Scatter-Matrix style for all D choose 2 pairs)
and Detailed 4-Heatmap Projection Analysis.
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QCheckBox,
        QComboBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

from pastar_rv.metrics import (
    FOOTPRINT_BINS,
    compute_all_pairwise_footprints,
    get_pair_label,
)
from pastar_rv.widgets.info_helper import TOOLTIPS, create_info_badge


class CanvasFootprint(QWidget):
    """
    Search Footprint Comparison Canvas with Pairwise Matrix:
    - Upper-triangular matrix of all (D choose 2) pairwise Absolute Expansion Differences.
    - Detailed 4-heatmap analysis (A, B, Abs Diff, Rel Density Diff) for any selected pair.
    - Dynamic occupancy & Jaccard overlap table for all pairs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._data_a = None
        self._data_b = None
        self._label_a = "A"
        self._label_b = "B"
        self._footprints_res = None
        self._lut_plasma = None
        self._lut_rdbu = None

        self._init_colormaps()
        self._build_ui()

    def _init_colormaps(self):
        # Plasma Colormap for log counts
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
        self._lut_plasma = pg.ColorMap(pos_plasma, col_plasma).getLookupTable(0.0, 1.0, 256)

        # RdBu Diverging Colormap (Blue=A more | White=Equal | Red=B more)
        pos_rdbu = np.array([0.0, 0.5, 1.0])
        col_rdbu = np.array(
            [[31, 119, 180, 255], [255, 255, 255, 255], [214, 39, 40, 255]],
            dtype=np.ubyte,
        )
        self._lut_rdbu = pg.ColorMap(pos_rdbu, col_rdbu).getLookupTable(0.0, 1.0, 256)

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(6)

        # ── 1. Top Banner & Occupancy Table ──
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; }"
        )
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(8, 6, 8, 6)
        banner_layout.setSpacing(4)

        header_row = QHBoxLayout()
        self.lbl_banner_title = QLabel("2D State Space Projections & Pairwise Footprint Overlap")
        self.lbl_banner_title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_banner_title.setStyleSheet("color: #1e293b;")
        header_row.addWidget(self.lbl_banner_title)
        header_row.addWidget(create_info_badge("footprint_table"))

        lbl_note = QLabel(
            "Note: 2D footprint is a projection of D-dimensional space; "
            "multiple distinct states map into the same 2D histogram bin."
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
                "Projection Pair",
                "Occupied Cells (A)",
                "Occupied Cells (B)",
                "Shared Cells",
                "Only in A",
                "Only in B",
                "Jaccard Overlap",
            ]
        )
        self.table_occ.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_occ.setFixedHeight(115)
        self.table_occ.setFont(QFont("Segoe UI", 8))
        self.table_occ.setToolTip(TOOLTIPS["footprint_table"])
        self.table_occ.cellClicked.connect(self._on_table_row_clicked)
        banner_layout.addWidget(self.table_occ)

        root_layout.addWidget(banner)

        # ── 2. View Tabs: Pairwise Matrix vs Detailed Pair ──
        self.view_tabs = QTabWidget()
        self.view_tabs.setFont(QFont("Segoe UI", 9))

        # ── Tab 1: Pairwise Projections Matrix (Upper-Triangular Grid) ──
        matrix_container = QWidget()
        matrix_outer_layout = QVBoxLayout(matrix_container)
        matrix_outer_layout.setContentsMargins(4, 4, 4, 4)
        matrix_outer_layout.setSpacing(4)

        matrix_hdr = QHBoxLayout()
        lbl_mat = QLabel(
            "<b>Pairwise Projections Matrix (All D*(D-1)/2 Pairs · Absolute Exp. Diff)</b>"
        )
        lbl_mat.setFont(QFont("Segoe UI", 9))
        lbl_mat.setStyleSheet("color: #1e293b;")
        matrix_hdr.addWidget(lbl_mat)
        matrix_hdr.addWidget(create_info_badge("matrix_view"))
        matrix_hdr.addStretch()
        matrix_outer_layout.addLayout(matrix_hdr)

        matrix_scroll = QScrollArea()
        matrix_scroll.setWidgetResizable(True)
        matrix_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.matrix_grid_widget = QWidget()
        self.matrix_grid_layout = QGridLayout(self.matrix_grid_widget)
        self.matrix_grid_layout.setSpacing(4)
        matrix_scroll.setWidget(self.matrix_grid_widget)

        matrix_outer_layout.addWidget(matrix_scroll)
        self.view_tabs.addTab(matrix_container, "📊 Pairwise Projections Matrix")
        self.view_tabs.setTabToolTip(0, TOOLTIPS["matrix_view"])

        # ── Tab 2: Detailed Pair Analysis (4 Heatmaps) ──
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(4, 4, 4, 4)
        detail_layout.setSpacing(6)

        # Selector Row for Detailed View
        detail_ctrl_row = QHBoxLayout()
        lbl_sel = QLabel("Inspect Pair:")
        lbl_sel.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        detail_ctrl_row.addWidget(lbl_sel)

        self.combo_detail_pair = QComboBox()
        self.combo_detail_pair.setFont(QFont("Segoe UI", 9))
        self.combo_detail_pair.setToolTip(TOOLTIPS["detail_pair_selector"])
        self.combo_detail_pair.currentIndexChanged.connect(self._on_detail_pair_changed)
        detail_ctrl_row.addWidget(self.combo_detail_pair)
        detail_ctrl_row.addWidget(create_info_badge("detail_pair_selector"))
        detail_ctrl_row.addSpacing(15)

        self.chk_log_intensity = QCheckBox("Log₁₊ scale intensity")
        self.chk_log_intensity.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.chk_log_intensity.setStyleSheet(
            "QCheckBox { color: #1e293b; padding-right: 4px; }"
            "QCheckBox:hover { color: #0284c7; }"
        )
        self.chk_log_intensity.setChecked(True)
        self.chk_log_intensity.setToolTip(TOOLTIPS["chk_log_footprint_intensity"])
        self.chk_log_intensity.toggled.connect(self._on_detail_pair_changed)
        detail_ctrl_row.addWidget(self.chk_log_intensity)
        detail_ctrl_row.addWidget(create_info_badge("chk_log_footprint_intensity"))
        detail_ctrl_row.addSpacing(15)

        self.lbl_detail_jaccard = QLabel("Jaccard: —")
        self.lbl_detail_jaccard.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_detail_jaccard.setStyleSheet("color: #0f172a;")
        detail_ctrl_row.addWidget(self.lbl_detail_jaccard)
        detail_ctrl_row.addStretch()
        detail_layout.addLayout(detail_ctrl_row)

        # 4 Detailed Plots Grid
        detail_grid = QGridLayout()
        detail_grid.setSpacing(6)

        self.plot_detail_a = pg.PlotWidget(title="A: Log Count")
        self.plot_detail_b = pg.PlotWidget(title="B: Log Count")
        self.plot_detail_diff_abs = pg.PlotWidget(
            title="Absolute Expansion Diff (Blue=A more | Red=B more)"
        )
        self.plot_detail_diff_rel = pg.PlotWidget(
            title="Relative Density Diff (Blue=A denser | Red=B denser)"
        )

        self.plot_detail_a.setToolTip(TOOLTIPS["plot_detail_a"])
        self.plot_detail_b.setToolTip(TOOLTIPS["plot_detail_b"])
        self.plot_detail_diff_abs.setToolTip(TOOLTIPS["plot_detail_diff_abs"])
        self.plot_detail_diff_rel.setToolTip(TOOLTIPS["plot_detail_diff_rel"])

        for p in (
            self.plot_detail_a,
            self.plot_detail_b,
            self.plot_detail_diff_abs,
            self.plot_detail_diff_rel,
        ):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")

        def wrap_detail(plot_widget, title_text, tooltip_key):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(2)
            h_row = QHBoxLayout()
            h_row.setContentsMargins(2, 0, 2, 0)
            h_row.setSpacing(4)
            lbl = QLabel(f"<b>{title_text}</b>")
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color: #1e293b;")
            h_row.addWidget(lbl)
            if tooltip_key and tooltip_key in TOOLTIPS:
                h_row.addWidget(create_info_badge(tooltip_key))
            h_row.addStretch()
            vbox.addLayout(h_row)
            vbox.addWidget(plot_widget)
            return container

        w_a = wrap_detail(self.plot_detail_a, "Dataset A (Log Count)", "plot_detail_a")
        w_b = wrap_detail(self.plot_detail_b, "Dataset B (Log Count)", "plot_detail_b")
        w_diff_abs = wrap_detail(
            self.plot_detail_diff_abs,
            "Absolute Expansion Diff (Blue=A | Red=B)",
            "plot_detail_diff_abs",
        )
        w_diff_rel = wrap_detail(
            self.plot_detail_diff_rel,
            "Relative Density Diff (Blue=A denser | Red=B denser)",
            "plot_detail_diff_rel",
        )

        detail_grid.addWidget(w_a, 0, 0)
        detail_grid.addWidget(w_b, 0, 1)
        detail_grid.addWidget(w_diff_abs, 1, 0)
        detail_grid.addWidget(w_diff_rel, 1, 1)
        detail_layout.addLayout(detail_grid)

        self.view_tabs.addTab(detail_container, "🔍 Detailed Pair View (4 Heatmaps)")
        self.view_tabs.setTabToolTip(1, TOOLTIPS["plot_detail_a"])

        root_layout.addWidget(self.view_tabs)

    # ── Data Loading & Matrix Population ──────

    def set_data(self, da, db, la="A", lb="B"):
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key

        self._data_a = da
        self._data_b = db
        self._label_a = la
        self._label_b = lb

        cA = da.get("coords")
        cB = db.get("coords")
        if cA is None or cB is None or len(cA) == 0 or len(cB) == 0:
            return

        dim_a = cA.shape[1] if cA.ndim > 1 else 0
        dim_b = cB.shape[1] if cB.ndim > 1 else 0
        d_dims = max(dim_a, dim_b, 2)

        # Compute all pairwise footprints in D-dimensional space
        self._footprints_res = compute_all_pairwise_footprints(
            cA, cB, dimensions=d_dims, n_bins=FOOTPRINT_BINS
        )

        pairs = self._footprints_res["pairs"]
        mean_jaccard = self._footprints_res["mean_jaccard"]

        self.lbl_banner_title.setText(
            f"2D State Space Projections & Pairwise Footprint Overlap "
            f"({len(pairs)} Pairs across {d_dims} Sequences · Mean Jaccard: {mean_jaccard:.4f})"
        )

        # 1. Populate Occupancy Table
        self.table_occ.setRowCount(len(pairs))
        for r, (d0, d1) in enumerate(pairs):
            fp = self._footprints_res["footprints"][(d0, d1)]
            pair_name = get_pair_label(d0, d1, prefix="Seq ")
            self.table_occ.setItem(r, 0, QTableWidgetItem(pair_name))
            self.table_occ.setItem(r, 1, QTableWidgetItem(f"{fp['n_occupied_a']:,}"))
            self.table_occ.setItem(r, 2, QTableWidgetItem(f"{fp['n_occupied_b']:,}"))
            self.table_occ.setItem(r, 3, QTableWidgetItem(f"{fp['n_shared']:,}"))
            self.table_occ.setItem(r, 4, QTableWidgetItem(f"{fp['n_only_a']:,}"))
            self.table_occ.setItem(r, 5, QTableWidgetItem(f"{fp['n_only_b']:,}"))
            item_j = QTableWidgetItem(f"{fp['jaccard']:.4f}")
            item_j.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_occ.setItem(r, 6, item_j)

        # 2. Populate Detail Combo Selector
        self.combo_detail_pair.blockSignals(True)
        self.combo_detail_pair.clear()
        for d0, d1 in pairs:
            label = f"{get_pair_label(d0, d1, prefix='Seq ')}  (Jaccard: {self._footprints_res['footprints'][(d0, d1)]['jaccard']:.4f})"
            self.combo_detail_pair.addItem(label, (d0, d1))
        self.combo_detail_pair.blockSignals(False)

        # 3. Build Pairwise Projections Matrix
        self._build_pairwise_matrix(d_dims, pairs)

        # 4. Render Detail View for current selection
        self._render_detailed_pair()

    def _build_pairwise_matrix(self, d_dims, pairs):
        # Clear existing widgets from matrix layout
        while self.matrix_grid_layout.count():
            item = self.matrix_grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Add Column Headers (S2 .. SD)
        for col_idx, j in enumerate(range(1, d_dims)):
            lbl = QLabel(f"<b>Seq {j + 1} (S{j + 1})</b>")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(
                "color: #1e293b; background: #e2e8f0; padding: 4px; border-radius: 4px;"
            )
            self.matrix_grid_layout.addWidget(lbl, 0, col_idx + 1)

        # Add Row Headers and Plots for Upper-Triangular Matrix
        for row_idx, i in enumerate(range(d_dims - 1)):
            lbl = QLabel(f"<b>Seq {i + 1}<br>(S{i + 1})</b>")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(
                "color: #1e293b; background: #e2e8f0; padding: 4px; border-radius: 4px;"
            )
            self.matrix_grid_layout.addWidget(lbl, row_idx + 1, 0)

            for col_idx, j in enumerate(range(1, d_dims)):
                if j > i:
                    pair = (i, j)
                    fp = self._footprints_res["footprints"].get(pair)
                    if fp is None:
                        continue

                    # Create compact heatmap plot for (i, j)
                    p_diff = pg.PlotWidget(
                        title=f"S{i + 1} vs S{j + 1} · Abs Diff (J={fp['jaccard']:.3f})"
                    )
                    p_diff.setBackground("w")
                    p_diff.setLabel("bottom", f"S{i + 1}", size="8pt")
                    p_diff.setLabel("left", f"S{j + 1}", size="8pt")
                    p_diff.setMinimumSize(180, 160)

                    x0, x1, y0, y1 = fp["extent"]
                    rect = pg.QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)
                    diff_abs = fp["diff_abs"]

                    max_abs = max(abs(diff_abs.min()), abs(diff_abs.max()), 1.0)
                    norm_diff_abs = (diff_abs / (2.0 * max_abs)) + 0.5

                    item_img = pg.ImageItem(norm_diff_abs)
                    item_img.setLookupTable(self._lut_rdbu)
                    item_img.setRect(rect)
                    p_diff.addItem(item_img)

                    # Add diagonal alignment guideline
                    lim = max(x1, y1)
                    diag = pg.PlotCurveItem(
                        [0, lim],
                        [0, lim],
                        pen=pg.mkPen(
                            color=(100, 100, 100, 150),
                            width=1.0,
                            style=pg.QtCore.Qt.PenStyle.DashLine,
                        ),
                    )
                    p_diff.addItem(diag)

                    self.matrix_grid_layout.addWidget(p_diff, row_idx + 1, col_idx + 1)
                else:
                    # Empty lower triangle placeholder
                    empty_cell = QLabel("—")
                    empty_cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    empty_cell.setStyleSheet("color: #cbd5e1;")
                    self.matrix_grid_layout.addWidget(empty_cell, row_idx + 1, col_idx + 1)

    def _on_table_row_clicked(self, row, col):
        if self._footprints_res and row < len(self._footprints_res["pairs"]):
            self.combo_detail_pair.setCurrentIndex(row)
            self.view_tabs.setCurrentIndex(1)  # switch to detailed view

    def _on_detail_pair_changed(self):
        self._render_detailed_pair()

    def _render_detailed_pair(self):
        if self._footprints_res is None or self._data_a is None or self._data_b is None:
            return

        pair = self.combo_detail_pair.currentData()
        if pair is None:
            if not self._footprints_res["pairs"]:
                return
            pair = self._footprints_res["pairs"][0]

        d0, d1 = pair
        fp = self._footprints_res["footprints"].get(pair)
        if fp is None:
            return

        cA = self._data_a["coords"]
        cB = self._data_b["coords"]
        la = self._label_a
        lb = self._label_b

        pair_title = get_pair_label(d0, d1, prefix="Seq ")
        self.lbl_detail_jaccard.setText(
            f"Pair: {pair_title}  |  Jaccard Overlap: {fp['jaccard']:.4f}  |  "
            f"Shared: {fp['n_shared']:,}  |  Only A: {fp['n_only_a']:,}  |  Only B: {fp['n_only_b']:,}"
        )

        x0, x1, y0, y1 = fp["extent"]
        rect = pg.QtCore.QRectF(x0, y0, x1 - x0, y1 - y0)

        HA = fp["HA"]
        HB = fp["HB"]
        diff_abs = fp["diff_abs"]
        diff_rel = fp["diff_rel"]

        is_log = self.chk_log_intensity.isChecked()
        scale_tag = "[Log₁₊ Count]" if is_log else "[Linear Count]"

        vmax_raw = max(HA.max(), HB.max(), 1.0)
        if is_log:
            img_data_a = np.log1p(HA) / np.log1p(vmax_raw)
            img_data_b = np.log1p(HB) / np.log1p(vmax_raw)
        else:
            img_data_a = HA / vmax_raw
            img_data_b = HB / vmax_raw

        # 1. Dataset A Heatmap
        self.plot_detail_a.clear()
        self.plot_detail_a.setTitle(f"{pair_title} · A: {la} ({len(cA):,} nodes) {scale_tag}")
        self.plot_detail_a.setLabel("bottom", f"Seq {d0 + 1}")
        self.plot_detail_a.setLabel("left", f"Seq {d1 + 1}")
        item_a = pg.ImageItem(img_data_a)
        item_a.setLookupTable(self._lut_plasma)
        item_a.setRect(rect)
        self.plot_detail_a.addItem(item_a)

        # 2. Dataset B Heatmap
        self.plot_detail_b.clear()
        self.plot_detail_b.setTitle(f"{pair_title} · B: {lb} ({len(cB):,} nodes) {scale_tag}")
        self.plot_detail_b.setLabel("bottom", f"Seq {d0 + 1}")
        self.plot_detail_b.setLabel("left", f"Seq {d1 + 1}")
        item_b = pg.ImageItem(img_data_b)
        item_b.setLookupTable(self._lut_plasma)
        item_b.setRect(rect)
        self.plot_detail_b.addItem(item_b)

        # 3. Absolute Expansion Difference
        max_abs = max(abs(diff_abs.min()), abs(diff_abs.max()), 1.0)
        norm_diff_abs = (diff_abs / (2.0 * max_abs)) + 0.5

        self.plot_detail_diff_abs.clear()
        self.plot_detail_diff_abs.setTitle(
            f"{pair_title} · Absolute Exp. Diff (Blue=A more | Red=B more)"
        )
        self.plot_detail_diff_abs.setLabel("bottom", f"Seq {d0 + 1}")
        self.plot_detail_diff_abs.setLabel("left", f"Seq {d1 + 1}")
        item_diff_abs = pg.ImageItem(norm_diff_abs)
        item_diff_abs.setLookupTable(self._lut_rdbu)
        item_diff_abs.setRect(rect)
        self.plot_detail_diff_abs.addItem(item_diff_abs)

        # 4. Relative Density Difference
        max_rel = max(abs(diff_rel.min()), abs(diff_rel.max()), 1e-6)
        norm_diff_rel = (diff_rel / (2.0 * max_rel)) + 0.5

        self.plot_detail_diff_rel.clear()
        self.plot_detail_diff_rel.setTitle(
            f"{pair_title} · Relative Density Diff (Blue=A denser | Red=B denser)"
        )
        self.plot_detail_diff_rel.setLabel("bottom", f"Seq {d0 + 1}")
        self.plot_detail_diff_rel.setLabel("left", f"Seq {d1 + 1}")
        item_diff_rel = pg.ImageItem(norm_diff_rel)
        item_diff_rel.setLookupTable(self._lut_rdbu)
        item_diff_rel.setRect(rect)
        self.plot_detail_diff_rel.addItem(item_diff_rel)
