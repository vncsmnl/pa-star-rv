"""
Diagonal Band Deviation Widget using PyQtGraph
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtWidgets import QHBoxLayout, QWidget
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtWidgets import QHBoxLayout, QWidget


class CanvasBand(QWidget):
    """Diagonal Band Deviation Canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.plot_scatter = pg.PlotWidget(
            title="Deviation per Node — Distance from diagonal line (i = j = k)"
        )
        self.plot_hist = pg.PlotWidget(
            title="Deviation Distribution — Narrow peak = Tight search band"
        )

        for p in (self.plot_scatter, self.plot_hist):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")
            layout.addWidget(p)

    def set_data(self, data, label=""):
        data_key = id(data)
        if self._current_key == data_key:
            return
        self._current_key = data_key

        dev = data["dev"]
        iters = data["iterations"]

        if len(dev) == 0:
            return

        if data_key in self._cache:
            sub_t, sub_dev, x0, x1, y, mean_val, median_val = self._cache[data_key]
        else:
            step = max(1, len(dev) // 50000)
            sub_t = iters[::step]
            sub_dev = dev[::step]

            y, x = np.histogram(dev, bins=60)
            mean_val = float(np.mean(dev))
            median_val = float(np.median(dev))
            x0 = x[:-1]
            x1 = x[1:]
            self._cache[data_key] = (sub_t, sub_dev, x0, x1, y, mean_val, median_val)

        # 1. Scatter plot (Downsampled for 60 FPS)
        self.plot_scatter.clear()
        self.plot_scatter.setLabel("bottom", "Iteration")
        self.plot_scatter.setLabel("left", "Deviation")

        scatter = pg.ScatterPlotItem(
            x=sub_t,
            y=sub_dev,
            size=3,
            pen=None,
            brush=pg.mkBrush(31, 119, 180, 100),
        )
        self.plot_scatter.addItem(scatter)

        # 2. Histogram
        self.plot_hist.clear()
        self.plot_hist.setLabel("bottom", "Deviation")
        self.plot_hist.setLabel("left", "Count")

        bg = pg.BarGraphItem(
            x0=x0,
            x1=x1,
            height=y,
            pen=pg.mkPen("w"),
            brush=pg.mkBrush("#1f77b4"),
        )
        self.plot_hist.addItem(bg)

        # Mean and Median lines
        l_mean = pg.InfiniteLine(
            pos=mean_val,
            angle=90,
            pen=pg.mkPen(
                color="#d62728", width=2, style=pg.QtCore.Qt.PenStyle.DashLine
            ),
            label=f"Mean: {mean_val:.1f}",
        )
        l_med = pg.InfiniteLine(
            pos=median_val,
            angle=90,
            pen=pg.mkPen(color="#ff7f0e", width=2, style=pg.QtCore.Qt.PenStyle.DotLine),
            label=f"Median: {median_val:.1f}",
        )
        self.plot_hist.addItem(l_mean)
        self.plot_hist.addItem(l_med)
