"""
Heuristic Behaviour Comparison Canvas (File A vs File B)
Analyzes g(n), h(n), f(n) profiles over geometric alignment progress,
Δh distributions, and h_A × h_B correlation on common unique states.
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
        QLabel,
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
        QLabel,
        QVBoxLayout,
        QWidget,
    )

from pastar_rv.metrics import (
    MAX_SCATTER_POINTS,
    PROGRESS_BINS,
    compute_binned_percentiles,
    compute_common_states_analysis,
    compute_geometric_alignment_progress,
)
from pastar_rv.widgets.info_helper import TOOLTIPS, create_info_badge


class CanvasHeuristicComparison(QWidget):
    """
    Dual-file Heuristic Behaviour & Common State Analysis Canvas.
    Profiles h, g, f across geometric alignment progress and evaluates
    heuristic difference (Δh = h_B - h_A) on exact common states.
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

        # ── 1. Top Diagnostic Banner ──
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; }"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(20)

        def make_card(title, initial_val="—", color="#1e293b", tooltip_key=None):
            card_layout = QVBoxLayout()
            card_layout.setSpacing(2)
            t_row = QHBoxLayout()
            t_row.setSpacing(4)
            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_title.setStyleSheet("color: #64748b; text-transform: uppercase;")
            t_row.addWidget(lbl_title)
            if tooltip_key:
                t_row.addWidget(create_info_badge(tooltip_key))
            t_row.addStretch()

            lbl_val = QLabel(initial_val)
            lbl_val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {color};")
            card_layout.addLayout(t_row)
            card_layout.addWidget(lbl_val)
            banner_layout.addLayout(card_layout)
            return lbl_val

        self.card_common = make_card("Valid Common States", "—", "#0f172a", "kpi_common_states")
        self.card_mean_dh = make_card("Mean Δh (h_B − h_A)", "—", "#2563eb", "group_heur_adv")
        self.card_median_dh = make_card("Median Δh", "—", "#2563eb", "group_heur_adv")
        self.card_pct_pos = make_card("% Δh > 0 (B > A)", "—", "#16a34a", "group_heur_adv")
        self.card_g_diag = make_card("Common g Match (g_A == g_B)", "—", "#7c3aed", "group_diag")
        self.card_f_diag = make_card("f == g + h Log Check", "—", "#059669", "group_diag")
        banner_layout.addStretch()

        root_layout.addWidget(banner)

        # ── 2. Grid of Plots ──
        grid = QGridLayout()
        grid.setSpacing(6)

        self.plot_h_profile = pg.PlotWidget(
            title="Heuristic Value h(n) by Geometric Alignment Progress"
        )
        self.plot_g_profile = pg.PlotWidget(title="Path Cost g(n) by Geometric Alignment Progress")
        self.plot_f_profile = pg.PlotWidget(
            title="Evaluation f(n) = g(n) + h(n) by Geometric Alignment Progress"
        )

        self.plot_dh_hist = pg.PlotWidget(
            title="Δh on Valid Common Unique States (h_B - h_A) [Δh > 0 means B is more informed]"
        )
        self.plot_scatter_h = pg.PlotWidget(
            title="h_A × h_B on Valid Common Unique States (Reference: y = x)"
        )

        self.plot_h_profile.setToolTip(TOOLTIPS["plot_h_profile"])
        self.plot_g_profile.setToolTip(TOOLTIPS["plot_g_profile"])
        self.plot_f_profile.setToolTip(TOOLTIPS["plot_f_profile"])
        self.plot_dh_hist.setToolTip(TOOLTIPS["plot_dh_hist"])
        self.plot_scatter_h.setToolTip(TOOLTIPS["plot_scatter_h"])

        for p in (
            self.plot_h_profile,
            self.plot_g_profile,
            self.plot_f_profile,
            self.plot_dh_hist,
            self.plot_scatter_h,
        ):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")
            p.addLegend(offset=(10, 10))

        def wrap_heur_plot(plot_widget, title_text, tooltip_key):
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

        w_h = wrap_heur_plot(
            self.plot_h_profile, "Heuristic h(n) Profile by Progress", "plot_h_profile"
        )
        w_g = wrap_heur_plot(
            self.plot_g_profile, "Path Cost g(n) Profile by Progress", "plot_g_profile"
        )
        w_f = wrap_heur_plot(
            self.plot_f_profile, "Evaluation f(n) Profile by Progress", "plot_f_profile"
        )
        w_dh = wrap_heur_plot(
            self.plot_dh_hist, "Δh Distribution (h_B − h_A) on Common States", "plot_dh_hist"
        )
        w_sc = wrap_heur_plot(
            self.plot_scatter_h, "h_A × h_B Scatter on Common States", "plot_scatter_h"
        )

        top_row = QHBoxLayout()
        top_row.addWidget(w_h)
        top_row.addWidget(w_g)
        top_row.addWidget(w_f)
        grid.addLayout(top_row, 0, 0, 1, 2)

        grid.addWidget(w_dh, 1, 0)
        grid.addWidget(w_sc, 1, 1)

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
            common_res, p_h_a, p_h_b, p_g_a, p_g_b, p_f_a, p_f_b = self._cache[cache_key]
        else:
            ref_coords = np.maximum(cA.max(axis=0), cB.max(axis=0))
            prog_a = compute_geometric_alignment_progress(cA, ref_coords)
            prog_b = compute_geometric_alignment_progress(cB, ref_coords)

            p_h_a = compute_binned_percentiles(
                prog_a, da["h"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )
            p_h_b = compute_binned_percentiles(
                prog_b, db["h"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )

            p_g_a = compute_binned_percentiles(
                prog_a, da["g"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )
            p_g_b = compute_binned_percentiles(
                prog_b, db["g"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )

            p_f_a = compute_binned_percentiles(
                prog_a, da["f"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )
            p_f_b = compute_binned_percentiles(
                prog_b, db["f"], n_bins=PROGRESS_BINS, percentiles=(25, 50, 75)
            )

            common_res = compute_common_states_analysis(
                cA,
                da["h"],
                da["g"],
                da["f"],
                cB,
                db["h"],
                db["g"],
                db["f"],
                max_scatter_points=MAX_SCATTER_POINTS,
            )

            self._cache[cache_key] = (
                common_res,
                p_h_a,
                p_h_b,
                p_g_a,
                p_g_b,
                p_f_a,
                p_f_b,
            )

        n_valid = common_res["num_valid_h_common"]
        self.card_common.setText(f"{n_valid:,} unique")
        if n_valid > 0:
            self.card_mean_dh.setText(f"{common_res['mean_delta_h']:+.2f}")
            self.card_median_dh.setText(f"{common_res['median_delta_h']:+.2f}")
            self.card_pct_pos.setText(f"{common_res['pct_delta_h_pos']:.1f} %")
        else:
            self.card_mean_dh.setText("N/A")
            self.card_median_dh.setText("N/A")
            self.card_pct_pos.setText("N/A")

        if common_res["num_valid_g_common"] > 0:
            self.card_g_diag.setText(f"{common_res['pct_g_match']:.1f} % match")
        else:
            self.card_g_diag.setText("N/A")

        f_match_a = common_res["f_diag_a"]["match_pct"]
        f_match_b = common_res["f_diag_b"]["match_pct"]
        self.card_f_diag.setText(f"A: {f_match_a:.0f}% | B: {f_match_b:.0f}%")

        def plot_profile(plot_widget, prof_a, prof_b, y_label):
            plot_widget.clear()
            plot_widget.setLabel("bottom", "Geometric Alignment Progress")
            plot_widget.setLabel("left", y_label)

            bc = prof_a["bin_centers"]
            v_a = ~np.isnan(prof_a["median"])
            if np.any(v_a):
                plot_widget.plot(
                    bc[v_a],
                    prof_a["median"][v_a],
                    pen=pg.mkPen("#1f77b4", width=2.5),
                    name=f"A: {la} (Median)",
                )
                plot_widget.plot(
                    bc[v_a],
                    prof_a["percentiles"][25][v_a],
                    pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
                )
                plot_widget.plot(
                    bc[v_a],
                    prof_a["percentiles"][75][v_a],
                    pen=pg.mkPen("#1f77b4", width=1.0, style=Qt.PenStyle.DashLine),
                )

            v_b = ~np.isnan(prof_b["median"])
            if np.any(v_b):
                plot_widget.plot(
                    bc[v_b],
                    prof_b["median"][v_b],
                    pen=pg.mkPen("#d62728", width=2.5),
                    name=f"B: {lb} (Median)",
                )
                plot_widget.plot(
                    bc[v_b],
                    prof_b["percentiles"][25][v_b],
                    pen=pg.mkPen("#d62728", width=1.0, style=Qt.PenStyle.DashLine),
                )
                plot_widget.plot(
                    bc[v_b],
                    prof_b["percentiles"][75][v_b],
                    pen=pg.mkPen("#d62728", width=1.0, style=Qt.PenStyle.DashLine),
                )

        plot_profile(self.plot_h_profile, p_h_a, p_h_b, "Heuristic h(n)")
        plot_profile(self.plot_g_profile, p_g_a, p_g_b, "Path Cost g(n)")
        plot_profile(self.plot_f_profile, p_f_a, p_f_b, "Evaluation f(n) = g + h")

        # Plot 4: Δh Histogram
        self.plot_dh_hist.clear()
        self.plot_dh_hist.setLabel("bottom", "Δh = h_B(s) - h_A(s)")
        self.plot_dh_hist.setLabel("left", "Number of Common States")

        delta_h = common_res["delta_h"]
        if len(delta_h) > 0:
            min_dh = delta_h.min()
            max_dh = delta_h.max()
            if min_dh == max_dh:
                bins = np.array([min_dh - 1.0, min_dh + 1.0])
            else:
                bins = np.linspace(min_dh, max_dh, 60)

            hist_y, hist_x = np.histogram(delta_h, bins=bins)
            bg_dh = pg.BarGraphItem(
                x0=hist_x[:-1],
                x1=hist_x[1:],
                height=hist_y,
                brush=pg.mkBrush("#2563eb"),
                pen=pg.mkPen("w"),
            )
            self.plot_dh_hist.addItem(bg_dh)

            line_zero_dh = pg.InfiniteLine(
                pos=0,
                angle=90,
                pen=pg.mkPen("#dc2626", width=2, style=Qt.PenStyle.DashLine),
                label="Δh = 0",
            )
            self.plot_dh_hist.addItem(line_zero_dh)

        # Plot 5: h_A × h_B Scatter Plot
        self.plot_scatter_h.clear()
        self.plot_scatter_h.setLabel("bottom", f"h_A: {la}")
        self.plot_scatter_h.setLabel("left", f"h_B: {lb}")

        sc_ha = common_res["scatter_ha"]
        sc_hb = common_res["scatter_hb"]

        if len(sc_ha) > 0:
            scatter_item = pg.ScatterPlotItem(
                x=sc_ha,
                y=sc_hb,
                size=3,
                pen=None,
                brush=pg.mkBrush(37, 99, 235, 120),
            )
            self.plot_scatter_h.addItem(scatter_item)

            max_val = max(sc_ha.max(), sc_hb.max(), 1.0)
            diag_line = pg.PlotCurveItem(
                [0, max_val],
                [0, max_val],
                pen=pg.mkPen(color="#dc2626", width=2, style=Qt.PenStyle.DashLine),
                name="y = x (Equal h)",
            )
            self.plot_scatter_h.addItem(diag_line)
