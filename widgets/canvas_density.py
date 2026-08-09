"""
Exploration Density Heatmaps Widget using PyQtGraph
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtWidgets import QHBoxLayout, QWidget
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtWidgets import QHBoxLayout, QWidget


class CanvasDensity(QWidget):
    """Fast 2D Exploration Density Heatmap Canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.plot_xy = pg.PlotWidget(title="XY Exploration Density (Top)")
        self.plot_xz = pg.PlotWidget(title="XZ Exploration Density (Front)")
        self.plot_yz = pg.PlotWidget(title="YZ Exploration Density (Side)")

        for p in (self.plot_xy, self.plot_xz, self.plot_yz):
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

        coords = data["coords"]
        if len(coords) == 0:
            return

        if data_key in self._cache:
            plots_data, lut = self._cache[data_key]
        else:
            x = coords[:, 0]
            y = coords[:, 1]
            z = coords[:, 2] if coords.shape[1] > 2 else np.zeros_like(x)

            pos = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
            color = np.array(
                [
                    [13, 8, 135, 255],
                    [126, 3, 168, 255],
                    [204, 71, 120, 255],
                    [248, 149, 64, 255],
                    [240, 249, 33, 255],
                ],
                dtype=np.ubyte,
            )
            cmap = pg.ColorMap(pos, color)
            lut = cmap.getLookupTable(0.0, 1.0, 256)

            BINS = 100
            plots_data = []
            for px, py in [(x, y), (x, z), (y, z)]:
                H, xe, ye = np.histogram2d(px, py, bins=BINS)
                H_log = np.log1p(H)
                max_val = max(1.0, H_log.max())
                H_norm = H_log / max_val
                rect_x = xe[-1] - xe[0]
                rect_y = ye[-1] - ye[0]
                lim = max(xe[-1], ye[-1])
                plots_data.append((H_norm, xe[0], ye[0], rect_x, rect_y, lim))
            self._cache[data_key] = (plots_data, lut)

        for plt_widget, (H_norm, x0, y0, rect_x, rect_y, lim), xl, yl in [
            (self.plot_xy, plots_data[0], "Seq A (i)", "Seq B (j)"),
            (self.plot_xz, plots_data[1], "Seq A (i)", "Seq C (k)"),
            (self.plot_yz, plots_data[2], "Seq B (j)", "Seq C (k)"),
        ]:
            plt_widget.clear()
            plt_widget.setLabel("bottom", xl)
            plt_widget.setLabel("left", yl)

            img = pg.ImageItem()
            img.setImage(H_norm)
            img.setLookupTable(lut)
            img.setRect(pg.QtCore.QRectF(x0, y0, rect_x, rect_y))
            plt_widget.addItem(img)

            diag = pg.PlotCurveItem(
                [0, lim],
                [0, lim],
                pen=pg.mkPen(
                    color=(214, 39, 40), width=1.5, style=pg.QtCore.Qt.PenStyle.DashLine
                ),
            )
            plt_widget.addItem(diag)
