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
        QCheckBox,
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
        QCheckBox,
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
        self._band_res = None
        self._mode = None  # "single" or "comparison"
        self._label_a = ""
        self._label_b = ""
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

        self.chk_log_dist_abs = QCheckBox("Log Y")
        self.chk_log_dist_abs.setToolTip(TOOLTIPS["chk_log_band_dist_abs"])
        self.chk_log_dist_abs.toggled.connect(self._on_log_dist_abs_toggled)

        self.chk_log_dist_density = QCheckBox("Log Y")
        self.chk_log_dist_density.setToolTip(TOOLTIPS["chk_log_band_dist_density"])
        self.chk_log_dist_density.toggled.connect(self._on_log_dist_density_toggled)

        def wrap_band_plot(plot_widget, title_text, tooltip_key, log_checkbox=None):
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
            if log_checkbox is not None:
                log_checkbox.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                log_checkbox.setStyleSheet(
                    "QCheckBox { color: #475569; padding-right: 4px; }"
                    "QCheckBox:hover { color: #0f172a; }"
                )
                h_row.addWidget(log_checkbox)
            vbox.addLayout(h_row)
            vbox.addWidget(plot_widget)
            return container

        w_prof = wrap_band_plot(
            self.plot_profile, "Search Band Width by Progress", "plot_band_profile"
        )
        w_abs = wrap_band_plot(
            self.plot_dist_abs,
            "Deviation Distribution (Absolute Count)",
            "plot_band_dist_abs",
            self.chk_log_dist_abs,
        )
        w_dens = wrap_band_plot(
            self.plot_dist_density,
            "Deviation Distribution (Normalized Density)",
            "plot_band_dist_density",
            self.chk_log_dist_density,
        )

        plots_layout.addWidget(w_prof)
        plots_layout.addWidget(w_abs)
        plots_layout.addWidget(w_dens)

        root_layout.addLayout(plots_layout)

    def _on_log_dist_abs_toggled(self):
        if self._band_res is not None:
            self._render_dist_abs()

    def _on_log_dist_density_toggled(self):
        if self._band_res is not None:
            self._render_dist_density()

    def _render_dist_abs(self):
        if self._band_res is None:
            return
        bins = self._band_res["hist_bins"]
        is_log = self.chk_log_dist_abs.isChecked()

        self.plot_dist_abs.clear()
        self.plot_dist_abs.setLabel("bottom", "Deviation from Diagonal")

        if self._mode == "single":
            self.plot_dist_abs.setTitle(
                f"Deviation Distribution (Absolute Count) · {self._label_a}"
            )
            count_a = self._band_res["count_a"]
            if is_log:
                h_a = np.log10(np.maximum(count_a, 1.0))
                self._apply_log_count_ticks(self.plot_dist_abs, [h_a])
                self.plot_dist_abs.setLabel("left", "Count (Log₁₀)")
            else:
                h_a = count_a
                self.plot_dist_abs.getAxis("left").setTicks(None)
                self.plot_dist_abs.setLabel("left", "Count")

            bg = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_a,
                brush=pg.mkBrush("#1f77b4"),
                pen=pg.mkPen("w"),
            )
            self.plot_dist_abs.addItem(bg)
        else:
            self.plot_dist_abs.setTitle("Global Band Deviation Distribution (Absolute Count)")
            count_a = self._band_res["count_a"]
            count_b = self._band_res["count_b"]
            if is_log:
                h_a = np.log10(np.maximum(count_a, 1.0))
                h_b = np.log10(np.maximum(count_b, 1.0))
                self._apply_log_count_ticks(self.plot_dist_abs, [h_a, h_b])
                self.plot_dist_abs.setLabel("left", "Count (Log₁₀)")
            else:
                h_a = count_a
                h_b = count_b
                self.plot_dist_abs.getAxis("left").setTicks(None)
                self.plot_dist_abs.setLabel("left", "Count")

            bg_a = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_a,
                brush=pg.mkBrush(31, 119, 180, 140),
                pen=pg.mkPen(31, 119, 180, 200),
            )
            bg_b = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_b,
                brush=pg.mkBrush(214, 39, 40, 140),
                pen=pg.mkPen(214, 39, 40, 200),
            )
            self.plot_dist_abs.addItem(bg_a)
            self.plot_dist_abs.addItem(bg_b)

    def _render_dist_density(self):
        if self._band_res is None:
            return
        bins = self._band_res["hist_bins"]
        is_log = self.chk_log_dist_density.isChecked()

        self.plot_dist_density.clear()
        self.plot_dist_density.setLabel("bottom", "Deviation from Diagonal")

        if self._mode == "single":
            self.plot_dist_density.setTitle(
                f"Deviation Distribution (Normalized Density) · {self._label_a}"
            )
            density_a = self._band_res["density_a"]
            if is_log:
                # Map 10^-6..10^0 to 0..6
                FLOOR = -6.0
                log_a = np.where(density_a > 0, np.log10(np.maximum(density_a, 10**FLOOR)) - FLOOR, 0.0)
                self._apply_log_density_ticks(self.plot_dist_density, FLOOR)
                self.plot_dist_density.setLabel("left", "Density (Log₁₀ Scale)")
                h_da = log_a
            else:
                h_da = density_a
                self.plot_dist_density.getAxis("left").setTicks(None)
                self.plot_dist_density.setLabel("left", "Density")

            bg_d = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_da,
                brush=pg.mkBrush("#1f77b4"),
                pen=pg.mkPen("w"),
            )
            self.plot_dist_density.addItem(bg_d)
        else:
            self.plot_dist_density.setTitle(
                "Global Band Deviation Distribution (Normalized Density)"
            )
            density_a = self._band_res["density_a"]
            density_b = self._band_res["density_b"]
            if is_log:
                FLOOR = -6.0
                h_da = np.where(density_a > 0, np.log10(np.maximum(density_a, 10**FLOOR)) - FLOOR, 0.0)
                h_db = np.where(density_b > 0, np.log10(np.maximum(density_b, 10**FLOOR)) - FLOOR, 0.0)
                self._apply_log_density_ticks(self.plot_dist_density, FLOOR)
                self.plot_dist_density.setLabel("left", "Probability Density (Log₁₀ Scale)")
            else:
                h_da = density_a
                h_db = density_b
                self.plot_dist_density.getAxis("left").setTicks(None)
                self.plot_dist_density.setLabel("left", "Probability Density")

            bg_da = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_da,
                brush=pg.mkBrush(31, 119, 180, 140),
                pen=pg.mkPen(31, 119, 180, 200),
            )
            bg_db = pg.BarGraphItem(
                x0=bins[:-1],
                x1=bins[1:],
                height=h_db,
                brush=pg.mkBrush(214, 39, 40, 140),
                pen=pg.mkPen(214, 39, 40, 200),
            )
            self.plot_dist_density.addItem(bg_da)
            self.plot_dist_density.addItem(bg_db)

    def _apply_log_count_ticks(self, plot_widget, arrays):
        max_val = max([float(arr.max()) if len(arr) > 0 else 1.0 for arr in arrays])
        max_log = max(1, int(np.ceil(max_val)))
        labels = {
            0: "1",
            1: "10",
            2: "100",
            3: "1k",
            4: "10k",
            5: "100k",
            6: "1M",
            7: "10M",
            8: "100M",
        }
        tick_vals = [(i, labels.get(i, f"10^{i}")) for i in range(max_log + 1)]
        plot_widget.getAxis("left").setTicks([tick_vals])

    def _apply_log_density_ticks(self, plot_widget, floor_val=-6.0):
        # Maps 0..6 to 10^-6..10^0
        ticks = [
            (0, "10⁻⁶"),
            (1, "10⁻⁵"),
            (2, "10⁻⁴"),
            (3, "10⁻³"),
            (4, "10⁻²"),
            (5, "10⁻¹"),
            (6, "10⁰"),
        ]
        plot_widget.getAxis("left").setTicks([ticks])

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

        self._band_res = band_res
        self._mode = "single"
        self._label_a = label
        self._label_b = ""

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
        self._render_dist_abs()

        # 3. Density
        self._render_dist_density()

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

        self._band_res = band_res
        self._mode = "comparison"
        self._label_a = la
        self._label_b = lb

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
        self._render_dist_abs()

        # 3. Overlaid Normalized Density
        self._render_dist_density()
