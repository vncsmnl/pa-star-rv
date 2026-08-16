"""
Search Dynamics Widget using PyQtGraph
Visualizes local minimum and average h(n) of expanded nodes, and expansion displacement distributions.
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pastar_rv.widgets.info_helper import TOOLTIPS, create_info_badge


class CanvasDynamics(QWidget):
    """Search Dynamics & Expansion Displacement Canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.plot_min_h = pg.PlotWidget(title="Local Minimum h(n) of Expanded Nodes")
        self.plot_avg_h = pg.PlotWidget(title="Local Average h(n) of Expanded Nodes")
        self.plot_jdist = pg.PlotWidget(title="Expansion Displacement Distribution (Manhattan L1)")
        self.plot_cumj = pg.PlotWidget(
            title="Cumulative Expansion Displacements — Flatter slope = More focused expansion sequence"
        )

        self.plot_min_h.setToolTip(TOOLTIPS["plot_dyn_min_h"])
        self.plot_avg_h.setToolTip(TOOLTIPS["plot_dyn_avg_h"])
        self.plot_jdist.setToolTip(TOOLTIPS["plot_dyn_jdist"])
        self.plot_cumj.setToolTip(TOOLTIPS["plot_dyn_cumj"])

        for p in (self.plot_min_h, self.plot_avg_h, self.plot_jdist, self.plot_cumj):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")

        def wrap_dyn_plot(plot_widget, title_text, tooltip_key):
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

        w_min = wrap_dyn_plot(self.plot_min_h, "Local Minimum h(n)", "plot_dyn_min_h")
        w_avg = wrap_dyn_plot(self.plot_avg_h, "Local Average h(n)", "plot_dyn_avg_h")
        w_jdist = wrap_dyn_plot(
            self.plot_jdist, "Expansion Displacement Distribution (L1)", "plot_dyn_jdist"
        )
        w_cumj = wrap_dyn_plot(
            self.plot_cumj, "Cumulative Expansion Displacements", "plot_dyn_cumj"
        )

        layout.addWidget(w_min, 0, 0)
        layout.addWidget(w_avg, 0, 1)
        layout.addWidget(w_jdist, 1, 0)
        layout.addWidget(w_cumj, 1, 1)

    def set_data(self, data, label=""):
        data_key = id(data)
        if self._current_key == data_key:
            return
        self._current_key = data_key

        h_arr = data["h"]
        n = len(h_arr)
        if n == 0:
            return

        if data_key in self._cache:
            cached = self._cache[data_key]
            sub_xn = cached["sub_xn"]
            min_h = cached["min_h"]
            avg_h = cached["avg_h"]
            jdist_data = cached["jdist_data"]
            cumj_data = cached["cumj_data"]
        else:
            xn = np.linspace(0, 1, n, dtype=np.float32)
            W = max(50, n // 100)

            pad_width = W // 2
            padded_h = np.pad(h_arr, pad_width, mode="edge")
            step = max(1, n // 5000)
            idx_range = np.arange(0, n, step)

            min_h = [np.min(padded_h[i : i + W]) for i in idx_range]
            avg_h = [np.mean(padded_h[i : i + W]) for i in idx_range]
            sub_xn = xn[idx_range]

            j_dists = data.get("jump_distances", np.array([]))
            if len(j_dists) > 0:
                y, x = np.histogram(j_dists, bins=40)
                mean_val = float(np.mean(j_dists))
                jdist_data = (x[:-1], x[1:], y, mean_val)
            else:
                jdist_data = None

            j_indices = data.get("jump_indices", np.array([]))
            if len(j_indices) > 0:
                progress_jumps = j_indices / max(1, n - 1)
                cum_counts = np.arange(1, len(j_indices) + 1)
                step_j = max(1, len(j_indices) // 5000)
                cumj_data = (progress_jumps[::step_j], cum_counts[::step_j])
            else:
                cumj_data = None

            cached = {
                "sub_xn": sub_xn,
                "min_h": min_h,
                "avg_h": avg_h,
                "jdist_data": jdist_data,
                "cumj_data": cumj_data,
            }
            self._cache[data_key] = cached

        # 1. Min h plot
        self.plot_min_h.clear()
        self.plot_min_h.setLabel("bottom", "Normalized Expansion Index")
        self.plot_min_h.setLabel("left", "Local min h(n)")
        self.plot_min_h.plot(sub_xn, min_h, pen=pg.mkPen(color="#d62728", width=2), name="min h")

        # 2. Avg h plot
        self.plot_avg_h.clear()
        self.plot_avg_h.setLabel("bottom", "Normalized Expansion Index")
        self.plot_avg_h.setLabel("left", "Local avg h(n)")
        self.plot_avg_h.plot(sub_xn, avg_h, pen=pg.mkPen(color="#1f77b4", width=2), name="avg h")

        # 3. Jump distance histogram
        self.plot_jdist.clear()
        self.plot_jdist.setLabel("bottom", "Expansion Displacement (Manhattan Step)")
        self.plot_jdist.setLabel("left", "Count")

        if jdist_data is not None:
            x0, x1, y, mean_val = jdist_data
            bg = pg.BarGraphItem(
                x0=x0,
                x1=x1,
                height=y,
                pen=pg.mkPen("w"),
                brush=pg.mkBrush("#1f77b4"),
            )
            self.plot_jdist.addItem(bg)

            line = pg.InfiniteLine(
                pos=mean_val,
                angle=90,
                pen=pg.mkPen(color="#d62728", width=2, style=pg.QtCore.Qt.PenStyle.DashLine),
            )
            self.plot_jdist.addItem(line)

        # 4. Cumulative jumps plot
        self.plot_cumj.clear()
        self.plot_cumj.setLabel("bottom", "Normalized Expansion Index")
        self.plot_cumj.setLabel("left", "Cumulative Displacements")

        if cumj_data is not None:
            pj, cc = cumj_data
            self.plot_cumj.plot(
                pj,
                cc,
                pen=pg.mkPen(color="#ff7f0e", width=2),
            )
