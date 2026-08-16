"""
Adaptive State Space Projections Widget (3D View + Arbitrary 2D Projections)
Supports full 3D for D=3, explicit projection warnings for D>3, and arbitrary (Xi, Xj) 2D projections.
"""

import numpy as np

try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QComboBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )


class CanvasStateSpace(QWidget):
    """
    Adaptive State Space Projections Canvas.
    - D = 3: Full 3D state space (x, y, z represents the complete state).
    - D > 3: Explicit 3D projection badge with warning and dimension selectors.
    - 2D Projections: Select any pairwise projection (x_i, x_j) among all (D choose 2) pairs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._data = None
        self._cache = {}
        self._dimensions = 3

        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(4)

        # ── 1. Top Adaptive Banner ──
        self.banner = QFrame()
        self.banner.setStyleSheet(
            "QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; }"
        )
        banner_layout = QHBoxLayout(self.banner)
        banner_layout.setContentsMargins(10, 6, 10, 6)
        banner_layout.setSpacing(10)

        self.lbl_mode_badge = QLabel("3D State Space")
        self.lbl_mode_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_mode_badge.setStyleSheet("color: #166534;")
        banner_layout.addWidget(self.lbl_mode_badge)

        self.lbl_banner_desc = QLabel("Complete 3D state space (Seq 1 × Seq 2 × Seq 3).")
        self.lbl_banner_desc.setFont(QFont("Segoe UI", 8))
        self.lbl_banner_desc.setStyleSheet("color: #374151;")
        banner_layout.addWidget(self.lbl_banner_desc)
        banner_layout.addStretch()

        root_layout.addWidget(self.banner)

        # ── 2. Splitter: 3D View (Left) and 2D Projections (Right) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: 3D Viewport ──
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # 3D Dimension Selector Row
        self.row_3d_ctrl = QHBoxLayout()
        self.row_3d_ctrl.setSpacing(6)
        lbl_3d = QLabel("3D Axes:")
        lbl_3d.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_3d.setStyleSheet("color: #475569;")
        self.row_3d_ctrl.addWidget(lbl_3d)

        self.combo_3d_x = QComboBox()
        self.combo_3d_y = QComboBox()
        self.combo_3d_z = QComboBox()
        for cb in (self.combo_3d_x, self.combo_3d_y, self.combo_3d_z):
            cb.setFont(QFont("Segoe UI", 8))
            cb.currentIndexChanged.connect(self._on_3d_dims_changed)

        self.row_3d_ctrl.addWidget(QLabel("X:"))
        self.row_3d_ctrl.addWidget(self.combo_3d_x)
        self.row_3d_ctrl.addWidget(QLabel("Y:"))
        self.row_3d_ctrl.addWidget(self.combo_3d_y)
        self.row_3d_ctrl.addWidget(QLabel("Z:"))
        self.row_3d_ctrl.addWidget(self.combo_3d_z)
        self.row_3d_ctrl.addStretch()
        left_layout.addLayout(self.row_3d_ctrl)

        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setBackgroundColor("w")
        self.scatter_3d = None
        self.grid_item = None
        left_layout.addWidget(self.gl_widget)
        splitter.addWidget(left_container)

        # ── Right: 2D Projections ──
        proj_container = QWidget()
        proj_layout = QVBoxLayout(proj_container)
        proj_layout.setContentsMargins(2, 2, 2, 2)
        proj_layout.setSpacing(4)

        # 2D Dimension Selectors Row
        row_2d_ctrl = QHBoxLayout()
        row_2d_ctrl.setSpacing(6)
        lbl_2d = QLabel("2D Projection:")
        lbl_2d.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_2d.setStyleSheet("color: #475569;")
        row_2d_ctrl.addWidget(lbl_2d)

        row_2d_ctrl.addWidget(QLabel("X:"))
        self.combo_2d_x = QComboBox()
        self.combo_2d_x.setFont(QFont("Segoe UI", 8))
        self.combo_2d_x.currentIndexChanged.connect(self._on_2d_dims_changed)
        row_2d_ctrl.addWidget(self.combo_2d_x)

        row_2d_ctrl.addWidget(QLabel("Y:"))
        self.combo_2d_y = QComboBox()
        self.combo_2d_y.setFont(QFont("Segoe UI", 8))
        self.combo_2d_y.currentIndexChanged.connect(self._on_2d_dims_changed)
        row_2d_ctrl.addWidget(self.combo_2d_y)
        row_2d_ctrl.addStretch()
        proj_layout.addLayout(row_2d_ctrl)

        # Main interactive 2D selected plot
        self.plot_selected_2d = pg.PlotWidget(title="Selected 2D Projection (Seq 1 vs Seq 2)")
        self.plot_selected_2d.setBackground("w")
        self.plot_selected_2d.showGrid(x=True, y=True, alpha=0.3)
        self.plot_selected_2d.getAxis("left").setPen("k")
        self.plot_selected_2d.getAxis("bottom").setPen("k")
        proj_layout.addWidget(self.plot_selected_2d, stretch=2)

        # Secondary 2D projection subplots (e.g. standard pairs)
        sub_row = QHBoxLayout()
        self.plot_sub1 = pg.PlotWidget(title="Projection S1 vs S3")
        self.plot_sub2 = pg.PlotWidget(title="Projection S2 vs S3")
        for p in (self.plot_sub1, self.plot_sub2):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")
            sub_row.addWidget(p)
        proj_layout.addLayout(sub_row, stretch=1)

        splitter.addWidget(proj_container)
        splitter.setSizes([750, 550])

        root_layout.addWidget(splitter)

    # ── Populate Selectors ────────────────────

    def _populate_dimension_combos(self, d_dims):
        self.combo_3d_x.blockSignals(True)
        self.combo_3d_y.blockSignals(True)
        self.combo_3d_z.blockSignals(True)
        self.combo_2d_x.blockSignals(True)
        self.combo_2d_y.blockSignals(True)

        for cb in (self.combo_3d_x, self.combo_3d_y, self.combo_3d_z, self.combo_2d_x, self.combo_2d_y):
            cb.clear()
            for d in range(d_dims):
                cb.addItem(f"Seq {d + 1}", d)

        # Set default selections
        self.combo_3d_x.setCurrentIndex(0)
        self.combo_3d_y.setCurrentIndex(min(1, d_dims - 1))
        self.combo_3d_z.setCurrentIndex(min(2, d_dims - 1))

        self.combo_2d_x.setCurrentIndex(0)
        self.combo_2d_y.setCurrentIndex(min(1, d_dims - 1))

        self.combo_3d_x.blockSignals(False)
        self.combo_3d_y.blockSignals(False)
        self.combo_3d_z.blockSignals(False)
        self.combo_2d_x.blockSignals(False)
        self.combo_2d_y.blockSignals(False)

    # ── Data Loading & Updates ────────────────

    def set_data(self, data, label=""):
        if data is None:
            return

        self._data = data
        data_key = id(data)

        coords = data.get("coords")
        if coords is None or len(coords) == 0:
            return

        d_dims = coords.shape[1] if coords.ndim > 1 else 1
        self._dimensions = d_dims

        # Update dimension combos if dimension count changed or new dataset
        if self._current_key != data_key:
            self._current_key = data_key
            self._populate_dimension_combos(d_dims)

        # Update Banner based on dimensionality
        self._update_banner(d_dims)

        # Render 3D and 2D
        self._render_3d()
        self._render_2d_projections()

    def _update_banner(self, d_dims):
        if d_dims == 3:
            self.banner.setStyleSheet(
                "QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; }"
            )
            self.lbl_mode_badge.setText("🎯 Complete 3D State Space")
            self.lbl_mode_badge.setStyleSheet("color: #166534;")
            self.lbl_banner_desc.setText(
                "D = 3: (x, y, z) represents the entire search state without projection loss."
            )
            self.lbl_banner_desc.setStyleSheet("color: #374151;")
        elif d_dims > 3:
            self.banner.setStyleSheet(
                "QFrame { background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; }"
            )
            self.lbl_mode_badge.setText(f"⚠️ 3D Projection (Partial {d_dims}D Space)")
            self.lbl_mode_badge.setStyleSheet("color: #b45309;")
            self.lbl_banner_desc.setText(
                f"3D projection — dimensions {self.combo_3d_x.currentText()}/"
                f"{self.combo_3d_y.currentText()}/{self.combo_3d_z.currentText()} only. "
                "Do not use this single 3D plot as evidence of global search space behavior."
            )
            self.lbl_banner_desc.setStyleSheet("color: #92400e; font-weight: 500;")
        else:
            self.banner.setStyleSheet(
                "QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; }"
            )
            self.lbl_mode_badge.setText("🎯 2D State Space")
            self.lbl_mode_badge.setStyleSheet("color: #166534;")
            self.lbl_banner_desc.setText("D = 2: (x, y) represents the entire search state.")
            self.lbl_banner_desc.setStyleSheet("color: #374151;")

    def _on_3d_dims_changed(self):
        if self._data is not None:
            self._update_banner(self._dimensions)
            self._render_3d()

    def _on_2d_dims_changed(self):
        if self._data is not None:
            self._render_2d_projections()

    # ── 3D OpenGL Rendering ───────────────────

    def _render_3d(self):
        if self._data is None:
            return

        coords = self._data["coords"]
        iters = self._data["iterations"]
        n_points = len(coords)
        if n_points == 0:
            return

        dx = self.combo_3d_x.currentData()
        if dx is None:
            dx = 0
        dy = self.combo_3d_y.currentData()
        if dy is None:
            dy = 1 if coords.shape[1] > 1 else 0
        dz = self.combo_3d_z.currentData()
        if dz is None:
            dz = 2 if coords.shape[1] > 2 else 0

        # Extract selected 3D axes
        col_x = coords[:, dx] if coords.shape[1] > dx else np.zeros(n_points, dtype=np.int32)
        col_y = coords[:, dy] if coords.shape[1] > dy else np.zeros(n_points, dtype=np.int32)
        col_z = coords[:, dz] if coords.shape[1] > dz else np.zeros(n_points, dtype=np.int32)

        pts_3d = np.column_stack([col_x, col_y, col_z])

        # Downsample for smooth 60 FPS rendering
        MAX_POINTS = 150000
        step = max(1, n_points // MAX_POINTS)
        sub_coords = pts_3d[::step].astype(np.float32)
        sub_iters = iters[::step]

        # Color gradient by iteration progress
        norm_t = (sub_iters - sub_iters.min()) / max(1, sub_iters.max() - sub_iters.min())
        stops = (
            np.array(
                [
                    [31, 119, 180],  # blue
                    [23, 190, 207],  # cyan
                    [76, 175, 80],  # green
                    [255, 214, 64],  # yellow
                    [255, 152, 0],  # orange
                    [220, 53, 69],  # red
                ],
                dtype=np.float32,
            )
            / 255.0
        )
        idx = np.minimum((norm_t * (len(stops) - 1)).astype(int), len(stops) - 1)
        colors = stops[idx]
        colors = np.column_stack([colors, np.full(len(colors), 0.90, dtype=np.float32)]).astype(
            np.float32
        )

        sizes = np.full(len(sub_coords), 5.0, dtype=np.float32)
        sizes[norm_t >= 0.75] = 6.0
        sizes[norm_t >= 0.90] = 7.0
        sizes[norm_t >= 0.97] = 9.0

        min_p = np.min(sub_coords, axis=0)
        max_p = np.max(sub_coords, axis=0)
        center = (min_p + max_p) / 2.0
        extent = float(np.max(max_p - min_p))

        c_x = float(center[0])
        c_y = float(center[1])
        c_z = float(center[2])

        camera_dist = max(extent * 1.6, 20.0)
        grid_size = max(extent * 1.2, 10.0)

        if self.scatter_3d in self.gl_widget.items:
            self.gl_widget.removeItem(self.scatter_3d)

        self.scatter_3d = gl.GLScatterPlotItem(
            pos=sub_coords,
            color=colors,
            size=sizes,
            pxMode=True,
            glOptions="translucent",
        )
        self.gl_widget.addItem(self.scatter_3d)

        self.gl_widget.setCameraPosition(
            pos=pg.Vector(c_x, c_y, c_z),
            distance=camera_dist,
            elevation=30,
            azimuth=45,
        )

        if self.grid_item in self.gl_widget.items:
            self.gl_widget.removeItem(self.grid_item)

        self.grid_item = gl.GLGridItem()
        self.grid_item.setSize(x=grid_size, y=grid_size, z=grid_size)
        self.grid_item.setSpacing(
            x=max(1, grid_size / 10),
            y=max(1, grid_size / 10),
            z=max(1, grid_size / 10),
        )
        self.grid_item.setColor((140, 140, 140, 255))
        self.grid_item.translate(c_x, c_y, float(min_p[2]))
        self.gl_widget.addItem(self.grid_item)

    # ── 2D Projections Rendering ──────────────

    def _render_2d_projections(self):
        if self._data is None:
            return

        coords = self._data["coords"]
        iters = self._data["iterations"]
        n_points = len(coords)
        if n_points == 0:
            return

        dx = self.combo_2d_x.currentData()
        if dx is None:
            dx = 0
        dy = self.combo_2d_y.currentData()
        if dy is None:
            dy = 1 if coords.shape[1] > 1 else 0

        step_2d = max(1, n_points // 50000)
        sub_iters_2d = iters[::step_2d]

        norm_2d = (sub_iters_2d - sub_iters_2d.min()) / max(
            1, sub_iters_2d.max() - sub_iters_2d.min()
        )
        stops = np.array(
            [
                [31, 119, 180],
                [23, 190, 207],
                [76, 175, 80],
                [255, 214, 64],
                [255, 152, 0],
                [220, 53, 69],
            ],
            dtype=np.float32,
        )
        idx_2d = np.minimum((norm_2d * (len(stops) - 1)).astype(int), len(stops) - 1)
        colors_2d = stops[idx_2d]
        brushes = [
            pg.mkBrush(int(r), int(g), int(b), 210)
            for r, g, b in colors_2d
        ]

        # 1. Main Selected 2D Plot
        px_main = coords[::step_2d, dx] if coords.shape[1] > dx else np.zeros(len(sub_iters_2d))
        py_main = coords[::step_2d, dy] if coords.shape[1] > dy else np.zeros(len(sub_iters_2d))

        self.plot_selected_2d.clear()
        title_main = f"Selected 2D Projection: Seq {dx + 1} (x) vs Seq {dy + 1} (y)"
        self.plot_selected_2d.setTitle(title_main)
        self.plot_selected_2d.setLabel("bottom", f"Seq {dx + 1} (x_{dx + 1})")
        self.plot_selected_2d.setLabel("left", f"Seq {dy + 1} (x_{dy + 1})")

        item_main = pg.ScatterPlotItem(
            x=px_main,
            y=py_main,
            size=3.5,
            pen=None,
            brush=brushes,
        )
        self.plot_selected_2d.addItem(item_main)

        # Diagonal alignment reference line
        max_coord = max(px_main.max() if len(px_main) > 0 else 1, py_main.max() if len(py_main) > 0 else 1)
        diag = pg.PlotCurveItem(
            [0, max_coord],
            [0, max_coord],
            pen=pg.mkPen(color=(220, 53, 69), width=1.5, style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        self.plot_selected_2d.addItem(diag)

        # 2. Subplots (Standard pairs S1-S3, S2-S3 if D >= 3, or other dimensions)
        d_dims = coords.shape[1]
        pair1 = (0, 2) if d_dims > 2 else (0, 1)
        pair2 = (1, 2) if d_dims > 2 else (0, min(1, d_dims - 1))

        for plt_w, (p_d0, p_d1) in [(self.plot_sub1, pair1), (self.plot_sub2, pair2)]:
            plt_w.clear()
            plt_w.setTitle(f"Seq {p_d0 + 1} vs Seq {p_d1 + 1}")
            plt_w.setLabel("bottom", f"Seq {p_d0 + 1}")
            plt_w.setLabel("left", f"Seq {p_d1 + 1}")

            sub_x = coords[::step_2d, p_d0] if coords.shape[1] > p_d0 else np.zeros(len(sub_iters_2d))
            sub_y = coords[::step_2d, p_d1] if coords.shape[1] > p_d1 else np.zeros(len(sub_iters_2d))

            sub_item = pg.ScatterPlotItem(
                x=sub_x,
                y=sub_y,
                size=2.5,
                pen=None,
                brush=brushes,
            )
            plt_w.addItem(sub_item)


# Alias for backward compatibility
Canvas3D = CanvasStateSpace
