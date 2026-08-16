"""
Search Savings Comparison Canvas (File A vs File B)
Visualizes expansion savings over geometric alignment progress.
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
    MIN_BIN_SUPPORT,
    PROGRESS_BINS,
    compute_expansion_savings,
    compute_geometric_alignment_progress,
)


class CanvasSavings(QWidget):
    """
    Dual-file Search Savings Canvas.
    Visualizes cumulative and local expansion differences over normalized geometric progress.
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

        # ── 1. Top Summary Banner (Cards) ──
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; }"
        )
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(20)

        def make_card(title, initial_val="—", color="#1e293b"):
            card_layout = QVBoxLayout()
            card_layout.setSpacing(2)
            lbl_title = QLabel(title)
            lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_title.setStyleSheet("color: #64748b; text-transform: uppercase;")
            lbl_val = QLabel(initial_val)
            lbl_val.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {color};")
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_val)
            banner_layout.addLayout(card_layout)
            return lbl_val

        self.card_nodes_a = make_card("Baseline (A) Expansions", "—", "#1f77b4")
        self.card_nodes_b = make_card("Candidate (B) Expansions", "—", "#d62728")
        self.card_saved = make_card("Total Nodes Saved (A - B)", "—", "#2563eb")
        self.card_reduction = make_card("Total Reduction", "—", "#16a34a")
        banner_layout.addStretch()

        root_layout.addWidget(banner)

        # ── 2. Grid of Comparison Plots ──
        grid = QGridLayout()
        grid.setSpacing(6)

        self.plot_cum = pg.PlotWidget(title="Cumulative Expanded Nodes by Geometric Progress")
        self.plot_cum_diff = pg.PlotWidget(
            title="Cumulative Expansion Difference (A - B) by Geometric Progress"
        )
        self.plot_local_saved = pg.PlotWidget(
            title="Nodes Saved in Region (local A - local B) [Positive = B expanded fewer]"
        )
        self.plot_local_red = pg.PlotWidget(
            title=f"Local Expansion Reduction (%) [Min Support: {MIN_BIN_SUPPORT} nodes in A]"
        )
        self.plot_local_ratio = pg.PlotWidget(
            title="Local Expansion Ratio (B / A) [Ref = 1.0, <1.0 means B used fewer]"
        )

        self._all_plots = [
            self.plot_cum,
            self.plot_cum_diff,
            self.plot_local_saved,
            self.plot_local_red,
            self.plot_local_ratio,
        ]

        for p in self._all_plots:
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")
            p.addLegend(offset=(10, 10))

        grid.addWidget(self.plot_cum, 0, 0)
        grid.addWidget(self.plot_cum_diff, 0, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.plot_local_saved)
        bottom_row.addWidget(self.plot_local_red)
        bottom_row.addWidget(self.plot_local_ratio)
        grid.addLayout(bottom_row, 1, 0, 1, 2)

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
            savings = self._cache[cache_key]
        else:
            ref_coords = np.maximum(cA.max(axis=0), cB.max(axis=0))
            prog_a = compute_geometric_alignment_progress(cA, ref_coords)
            prog_b = compute_geometric_alignment_progress(cB, ref_coords)
            savings = compute_expansion_savings(
                prog_a, prog_b, n_bins=PROGRESS_BINS, min_support=MIN_BIN_SUPPORT
            )
            self._cache[cache_key] = savings

        nA = savings["expansions_a"]
        nB = savings["expansions_b"]
        saved = savings["total_nodes_saved"]
        red_pct = savings["total_reduction_pct"]

        self.card_nodes_a.setText(f"{nA:,} ({la})")
        self.card_nodes_b.setText(f"{nB:,} ({lb})")
        saved_prefix = "+" if saved >= 0 else "−"
        self.card_saved.setText(f"{saved_prefix}{abs(saved):,}")
        self.card_reduction.setText(f"{red_pct:+.2f} %")

        bin_centers = savings["bin_centers"]
        bin_edges = savings["bin_edges"]
        cum_a = savings["cum_a"]
        cum_b = savings["cum_b"]
        cum_diff = savings["cum_diff"]
        local_saved = savings["local_saved"]
        local_red = savings["local_reduction"]
        local_ratio = savings["local_ratio"]

        # Plot 1: Cumulative Expansions
        self.plot_cum.clear()
        self.plot_cum.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_cum.setLabel("left", "Cumulative Expanded Nodes")
        self.plot_cum.plot(bin_centers, cum_a, pen=pg.mkPen("#1f77b4", width=2.5), name=f"A: {la}")
        self.plot_cum.plot(bin_centers, cum_b, pen=pg.mkPen("#d62728", width=2.5), name=f"B: {lb}")

        # Plot 2: Cumulative Difference
        self.plot_cum_diff.clear()
        self.plot_cum_diff.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_cum_diff.setLabel("left", "Cumulative Expansions Saved (A - B)")
        self.plot_cum_diff.plot(
            bin_centers,
            cum_diff,
            pen=pg.mkPen("#16a34a", width=2.5),
            name="Saved by B (A - B)",
        )
        line_zero_cum = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen=pg.mkPen("#94a3b8", width=1.5, style=Qt.PenStyle.DashLine),
        )
        self.plot_cum_diff.addItem(line_zero_cum)

        # Plot 3: Nodes Saved in Region
        self.plot_local_saved.clear()
        self.plot_local_saved.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_local_saved.setLabel("left", "Nodes Saved in Region")

        pos_mask = local_saved >= 0
        neg_mask = ~pos_mask
        w = (bin_edges[1] - bin_edges[0]) * 0.9

        if np.any(pos_mask):
            bg_pos = pg.BarGraphItem(
                x=bin_centers[pos_mask],
                height=local_saved[pos_mask],
                width=w,
                brush=pg.mkBrush(22, 163, 74, 180),
                pen=pg.mkPen(22, 163, 74, 220),
            )
            self.plot_local_saved.addItem(bg_pos)

        if np.any(neg_mask):
            bg_neg = pg.BarGraphItem(
                x=bin_centers[neg_mask],
                height=local_saved[neg_mask],
                width=w,
                brush=pg.mkBrush(220, 38, 38, 180),
                pen=pg.mkPen(220, 38, 38, 220),
            )
            self.plot_local_saved.addItem(bg_neg)

        line_zero_local = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen=pg.mkPen("#64748b", width=1.5, style=Qt.PenStyle.DashLine),
        )
        self.plot_local_saved.addItem(line_zero_local)

        # Plot 4: Local Reduction (%)
        self.plot_local_red.clear()
        self.plot_local_red.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_local_red.setLabel("left", "Local Reduction (%)")

        valid_mask = ~np.isnan(local_red)
        if np.any(valid_mask):
            self.plot_local_red.plot(
                bin_centers[valid_mask],
                local_red[valid_mask],
                pen=pg.mkPen("#2563eb", width=2),
                symbol="o",
                symbolSize=4,
                symbolBrush="#2563eb",
                name="Local Reduction %",
            )
        line_zero_red = pg.InfiniteLine(
            pos=0,
            angle=0,
            pen=pg.mkPen("#94a3b8", width=1.5, style=Qt.PenStyle.DashLine),
        )
        self.plot_local_red.addItem(line_zero_red)

        # Plot 5: Local Expansion Ratio (B / A)
        self.plot_local_ratio.clear()
        self.plot_local_ratio.setLabel("bottom", "Geometric Alignment Progress")
        self.plot_local_ratio.setLabel("left", "Expansion Ratio (B / A)")

        valid_ratio_mask = ~np.isnan(local_ratio)
        if np.any(valid_ratio_mask):
            self.plot_local_ratio.plot(
                bin_centers[valid_ratio_mask],
                local_ratio[valid_ratio_mask],
                pen=pg.mkPen("#9333ea", width=2),
                symbol="t",
                symbolSize=4,
                symbolBrush="#9333ea",
                name="Ratio B / A",
            )
        line_one_ratio = pg.InfiniteLine(
            pos=1.0,
            angle=0,
            pen=pg.mkPen("#dc2626", width=1.5, style=Qt.PenStyle.DashLine),
            label="Ratio = 1.0 (Equal)",
        )
        self.plot_local_ratio.addItem(line_one_ratio)
