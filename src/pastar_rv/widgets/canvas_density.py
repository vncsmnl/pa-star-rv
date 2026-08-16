"""
Exploration Density Heatmaps Widget (CanvasDensity)
Visualizes 2D exploration density heatmaps for any arbitrary (Xi, Xj) projection in D-dimensional space.
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QVBoxLayout,
        QWidget,
    )


from pastar_rv.widgets.info_helper import TOOLTIPS, create_info_badge


class CanvasDensity(QWidget):
    """
    Adaptive Exploration Density Heatmap Canvas.
    Supports selecting any pairwise projection (x_i, x_j) across all D dimensions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._data = None
        self._label = ""
        self._dimensions = 3
        self._lut = None

        self._init_colormap()
        self._build_ui()

    def _init_colormap(self):
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
        self._lut = cmap.getLookupTable(0.0, 1.0, 256)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Control Bar ──
        ctrl_bar = QFrame()
        ctrl_bar.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #e2e8f0; border-radius: 6px; }"
        )
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(10, 6, 10, 6)
        ctrl_layout.setSpacing(10)

        lbl_ctrl = QLabel("Projection Density:")
        lbl_ctrl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_ctrl.setStyleSheet("color: #1e293b;")
        ctrl_layout.addWidget(lbl_ctrl)
        ctrl_layout.addWidget(create_info_badge("density_controls"))

        ctrl_layout.addWidget(QLabel("X:"))
        self.combo_x = QComboBox()
        self.combo_x.setFont(QFont("Segoe UI", 9))
        self.combo_x.setToolTip(TOOLTIPS["density_controls"])
        self.combo_x.currentIndexChanged.connect(self._on_dims_changed)
        ctrl_layout.addWidget(self.combo_x)

        ctrl_layout.addWidget(QLabel("Y:"))
        self.combo_y = QComboBox()
        self.combo_y.setFont(QFont("Segoe UI", 9))
        self.combo_y.setToolTip(TOOLTIPS["density_controls"])
        self.combo_y.currentIndexChanged.connect(self._on_dims_changed)
        ctrl_layout.addWidget(self.combo_y)

        self.lbl_info = QLabel("—")
        self.lbl_info.setFont(QFont("Segoe UI", 8))
        self.lbl_info.setStyleSheet("color: #64748b; font-style: italic;")
        ctrl_layout.addWidget(self.lbl_info)

        ctrl_layout.addStretch()
        layout.addWidget(ctrl_bar)

        # ── Plots Grid (1 Main Selected + 2 Secondary) ──
        plots_layout = QHBoxLayout()
        plots_layout.setSpacing(6)

        self.plot_main = pg.PlotWidget(title="Selected Projection Exploration Density")
        self.plot_sub1 = pg.PlotWidget(title="Seq 1 vs Seq 2 Density")
        self.plot_sub2 = pg.PlotWidget(title="Seq 1 vs Seq 3 Density")

        self.plot_main.setToolTip(TOOLTIPS["plot_density_main"])
        self.plot_sub1.setToolTip(TOOLTIPS["plot_density_main"])
        self.plot_sub2.setToolTip(TOOLTIPS["plot_density_main"])

        for p in (self.plot_main, self.plot_sub1, self.plot_sub2):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")

        def wrap_dense(plot_widget, title_text, tooltip_key):
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

        w_main = wrap_dense(self.plot_main, "Selected Projection Density", "plot_density_main")
        w_sub1 = wrap_dense(self.plot_sub1, "Seq 1 vs Seq 2 Density", "plot_density_main")
        w_sub2 = wrap_dense(self.plot_sub2, "Seq 1 vs Seq 3 Density", "plot_density_main")

        plots_layout.addWidget(w_main, stretch=3)
        plots_layout.addWidget(w_sub1, stretch=2)
        plots_layout.addWidget(w_sub2, stretch=2)

        layout.addLayout(plots_layout)

    def _populate_combos(self, d_dims):
        self.combo_x.blockSignals(True)
        self.combo_y.blockSignals(True)

        self.combo_x.clear()
        self.combo_y.clear()

        for d in range(d_dims):
            self.combo_x.addItem(f"Seq {d + 1}", d)
            self.combo_y.addItem(f"Seq {d + 1}", d)

        self.combo_x.setCurrentIndex(0)
        self.combo_y.setCurrentIndex(min(1, d_dims - 1))

        self.combo_x.blockSignals(False)
        self.combo_y.blockSignals(False)

    def set_data(self, data, label=""):
        if data is None:
            return

        self._data = data
        self._label = label
        data_key = id(data)

        coords = data.get("coords")
        if coords is None or len(coords) == 0:
            return

        d_dims = coords.shape[1] if coords.ndim > 1 else 1
        self._dimensions = d_dims

        if self._current_key != data_key:
            self._current_key = data_key
            self._populate_combos(d_dims)

        self.lbl_info.setText(
            f"Dataset: {label} ({len(coords):,} expanded nodes · {d_dims} Dimensions)"
        )
        self._render_plots()

    def _on_dims_changed(self):
        if self._data is not None:
            self._render_plots()

    def _render_plots(self):
        if self._data is None:
            return

        coords = self._data["coords"]
        n_points = len(coords)
        if n_points == 0:
            return

        d_dims = coords.shape[1]
        dx = self.combo_x.currentData()
        if dx is None:
            dx = 0
        dy = self.combo_y.currentData()
        if dy is None:
            dy = 1 if d_dims > 1 else 0

        BINS = 100

        # Helper to compute and render heatmap
        def _plot_density(plt_widget, d0, d1, title_text):
            x = coords[:, d0] if coords.shape[1] > d0 else np.zeros(n_points)
            y = coords[:, d1] if coords.shape[1] > d1 else np.zeros(n_points)

            H, xe, ye = np.histogram2d(x, y, bins=BINS)
            H_log = np.log1p(H)
            max_val = max(1.0, H_log.max())
            H_norm = H_log / max_val

            rect_x = xe[-1] - xe[0]
            rect_y = ye[-1] - ye[0]
            lim = max(xe[-1], ye[-1], 1.0)

            plt_widget.clear()
            plt_widget.setTitle(title_text)
            plt_widget.setLabel("bottom", f"Seq {d0 + 1}")
            plt_widget.setLabel("left", f"Seq {d1 + 1}")

            img = pg.ImageItem()
            img.setImage(H_norm)
            img.setLookupTable(self._lut)
            img.setRect(pg.QtCore.QRectF(xe[0], ye[0], rect_x, rect_y))
            plt_widget.addItem(img)

            diag = pg.PlotCurveItem(
                [0, lim],
                [0, lim],
                pen=pg.mkPen(color=(214, 39, 40), width=1.5, style=pg.QtCore.Qt.PenStyle.DashLine),
            )
            plt_widget.addItem(diag)

        # 1. Main Selected Density Plot
        _plot_density(
            self.plot_main,
            dx,
            dy,
            f"Selected Density: Seq {dx + 1} vs Seq {dy + 1} ({self._label})",
        )

        # 2. Subplots (Presets or Secondary Projections)
        pair1 = (0, 1)
        pair2 = (0, 2) if d_dims > 2 else (1, min(1, d_dims - 1))

        _plot_density(
            self.plot_sub1,
            pair1[0],
            pair1[1],
            f"Seq {pair1[0] + 1} vs Seq {pair1[1] + 1} Density",
        )
        _plot_density(
            self.plot_sub2,
            pair2[0],
            pair2[1],
            f"Seq {pair2[0] + 1} vs Seq {pair2[1] + 1} Density",
        )
