"""
Diagonal Band Deviation Widget using PyQtGraph
Supports single file inspection and dual-file comparative search band profiling.
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QVBoxLayout,
        QWidget,
    )

from pastar_rv.metrics import (
    PROGRESS_BINS,
    compute_band_comparison,
    compute_geometric_alignment_progress,
)
from pastar_rv.widgets.info_helper import TOOLTIPS, create_info_badge


class CanvasBand(QWidget):
    """
    Search Band Deviation Canvas.
    Profiles distance from diagonal over geometric alignment progress
    and provides absolute count vs normalized density comparisons.
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

        # Plot Layout
        plots_layout = QHBoxLayout()
        plots_layout.setSpacing(6)

        # Plot 1: Band profile by Geometric Progress
        self.plot_profile = pg.PlotWidget(
            title="Search Band Width by Geometric Progress (Median & P25/P75/P90)"
        )
        # Plot 2: Global Deviation Distribution (Absolute Count)
        self.plot_dist_abs = pg.PlotWidget(
            title="Global Band Deviation Distribution (Absolute Count)"
        )
        # Plot 3: Global Deviation Distribution (Normalized Density)
        self.plot_dist_density = pg.PlotWidget(
            title="Global Band Deviation Distribution (Normalized Density)"
        )

        self.plot_profile.setToolTip(TOOLTIPS["plot_band_profile"])
        self.plot_dist_abs.setToolTip(TOOLTIPS["plot_band_dist_abs"])
        self.plot_dist_density.setToolTip(TOOLTIPS["plot_band_dist_density"])

        for p in (self.plot_profile, self.plot_dist_abs, self.plot_dist_density):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")
            p.addLegend(offset=(10, 10))

        def wrap_band_plot(plot_widget, title_text, tooltip_key):
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

        w_prof = wrap_band_plot(
            self.plot_profile, "Search Band Width by Progress", "plot_band_profile"
        )
        w_abs = wrap_band_plot(
            self.plot_dist_abs, "Deviation Distribution (Absolute Count)", "plot_band_dist_abs"
        )
        w_dens = wrap_band_plot(
            self.plot_dist_density,
            "Deviation Distribution (Normalized Density)",
            "plot_band_dist_density",
        )

        plots_layout.addWidget(w_prof)
        plots_layout.addWidget(w_abs)
        plots_layout.addWidget(w_dens)

        root_layout.addLayout(plots_layout)

    def set_data(self, data, label=""):
        """Single file display mode."""
        data_key = id(data)
        if self._current_key == data_key:
            return
        self._current_key = data_key

        dev = data.get("dev")
        coords = data.get("coords")
        if dev is None or len(dev) == 0:
            return

        prog = compute_geometric_alignment_progress(coords)
        band_res = compute_band_comparison(prog, dev, None, None, n_bins=PROGRESS_BINS)

        # 1. Profile Plot
        self.plot_profile.clear()
        self.plot_profile.setTitle(f"Search Band Width by Geometric Progress · {label}")
        self.plot_profile.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_profile.setLabel("left", "Deviation from Diagonal")

        prof = band_res["profile_a"]
        bc = prof["bin_centers"]
        v = ~np.isnan(prof["median"])
        if np.any(v):
            self.plot_profile.plot(
                bc[v],
                prof["median"][v],
                pen=pg.mkPen("#1f77b4", width=2.5),
                name="Median",
            )
            self.plot_profile.plot(
                bc[v],
                prof["percentiles"][25][v],
                pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
                name="P25 / P75",
            )
            self.plot_profile.plot(
                bc[v],
                prof["percentiles"][75][v],
                pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
            )
            self.plot_profile.plot(
                bc[v],
                prof["percentiles"][90][v],
                pen=pg.mkPen("#ff7f0e", width=1.0, style=Qt.PenStyle.DotLine),
                name="P90",
            )

        # 2. Absolute Count
        self.plot_dist_abs.clear()
        self.plot_dist_abs.setTitle(f"Deviation Distribution (Absolute Count) · {label}")
        self.plot_dist_abs.setLabel("bottom", "Deviation")
        self.plot_dist_abs.setLabel("left", "Count")

        bins = band_res["hist_bins"]
        bg = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["count_a"],
            brush=pg.mkBrush("#1f77b4"),
            pen=pg.mkPen("w"),
        )
        self.plot_dist_abs.addItem(bg)

        # 3. Density
        self.plot_dist_density.clear()
        self.plot_dist_density.setTitle(f"Deviation Distribution (Normalized Density) · {label}")
        self.plot_dist_density.setLabel("bottom", "Deviation")
        self.plot_dist_density.setLabel("left", "Density")

        bg_d = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["density_a"],
            brush=pg.mkBrush("#1f77b4"),
            pen=pg.mkPen("w"),
        )
        self.plot_dist_density.addItem(bg_d)

    def set_data_comparison(self, da, db, la="A", lb="B"):
        """Dual file comparison mode."""
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key

        cA = da.get("coords")
        cB = db.get("coords")
        devA = da.get("dev")
        devB = db.get("dev")
        if cA is None or cB is None or devA is None or devB is None:
            return

        ref_coords = np.maximum(cA.max(axis=0), cB.max(axis=0))
        prog_a = compute_geometric_alignment_progress(cA, ref_coords)
        prog_b = compute_geometric_alignment_progress(cB, ref_coords)

        band_res = compute_band_comparison(prog_a, devA, prog_b, devB, n_bins=PROGRESS_BINS)

        # 1. Profile Plot (A vs B)
        self.plot_profile.clear()
        self.plot_profile.setTitle("Search Band Width by Geometric Progress (A vs B)")
        self.plot_profile.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_profile.setLabel("left", "Deviation from Diagonal")

        prof_a = band_res["profile_a"]
        prof_b = band_res["profile_b"]
        bc = prof_a["bin_centers"]

        # A: Blue
        v_a = ~np.isnan(prof_a["median"])
        if np.any(v_a):
            self.plot_profile.plot(
                bc[v_a],
                prof_a["median"][v_a],
                pen=pg.mkPen("#1f77b4", width=2.5),
                name=f"A: {la} (Median)",
            )
            self.plot_profile.plot(
                bc[v_a],
                prof_a["percentiles"][25][v_a],
                pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
            )
            self.plot_profile.plot(
                bc[v_a],
                prof_a["percentiles"][75][v_a],
                pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
            )

        # B: Red
        v_b = ~np.isnan(prof_b["median"])
        if np.any(v_b):
            self.plot_profile.plot(
                bc[v_b],
                prof_b["median"][v_b],
                pen=pg.mkPen("#d62728", width=2.5),
                name=f"B: {lb} (Median)",
            )
            self.plot_profile.plot(
                bc[v_b],
                prof_b["percentiles"][25][v_b],
                pen=pg.mkPen("#d62728", width=1.0, style=Qt.PenStyle.DashLine),
            )
            self.plot_profile.plot(
                bc[v_b],
                prof_b["percentiles"][75][v_b],
                pen=pg.mkPen("#d62728", width=1.0, style=Qt.PenStyle.DashLine),
            )

        # 2. Overlaid Absolute Count
        self.plot_dist_abs.clear()
        self.plot_dist_abs.setTitle("Global Band Deviation Distribution (Absolute Count)")
        self.plot_dist_abs.setLabel("bottom", "Deviation")
        self.plot_dist_abs.setLabel("left", "Count")

        bins = band_res["hist_bins"]
        bg_a = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["count_a"],
            brush=pg.mkBrush(31, 119, 180, 140),
            pen=pg.mkPen(31, 119, 180, 200),
        )
        bg_b = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["count_b"],
            brush=pg.mkBrush(214, 39, 40, 140),
            pen=pg.mkPen(214, 39, 40, 200),
        )
        self.plot_dist_abs.addItem(bg_a)
        self.plot_dist_abs.addItem(bg_b)

        # 3. Overlaid Normalized Density
        self.plot_dist_density.clear()
        self.plot_dist_density.setTitle("Global Band Deviation Distribution (Normalized Density)")
        self.plot_dist_density.setLabel("bottom", "Deviation")
        self.plot_dist_density.setLabel("left", "Probability Density")

        bg_da = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["density_a"],
            brush=pg.mkBrush(31, 119, 180, 140),
            pen=pg.mkPen(31, 119, 180, 200),
        )
        bg_db = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=band_res["density_b"],
            brush=pg.mkBrush(214, 39, 40, 140),
            pen=pg.mkPen(214, 39, 40, 200),
        )
        self.plot_dist_density.addItem(bg_da)
        self.plot_dist_density.addItem(bg_db)
