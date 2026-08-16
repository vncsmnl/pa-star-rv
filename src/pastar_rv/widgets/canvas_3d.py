"""
3D View and 2D Projections Widget using PyQtGraph & OpenGL
"""

import numpy as np

try:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget
except ImportError:
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QSplitter, QVBoxLayout, QWidget


class Canvas3D(QWidget):
    """Interactive OpenGL 3D Scatter + 2D Projection Plots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 3D Viewport (Left)
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setBackgroundColor("w")

        self.scatter_3d = None
        self.grid_item = None
        splitter.addWidget(self.gl_widget)

        # 2D Projections (Right)
        proj_container = QWidget()
        proj_layout = QVBoxLayout(proj_container)
        proj_layout.setContentsMargins(2, 2, 2, 2)

        self.plot_xy = pg.PlotWidget(title="XY (Top Projection: Seq A vs Seq B)")
        self.plot_xz = pg.PlotWidget(title="XZ (Front Projection: Seq A vs Seq C)")
        self.plot_yz = pg.PlotWidget(title="YZ (Side Projection: Seq B vs Seq C)")

        for p in (self.plot_xy, self.plot_xz, self.plot_yz):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")

        proj_layout.addWidget(self.plot_xy)
        proj_layout.addWidget(self.plot_xz)
        proj_layout.addWidget(self.plot_yz)

        splitter.addWidget(proj_container)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter)

    def set_data(self, data, label=""):
        data_key = id(data)
        if self._current_key == data_key:
            return
        self._current_key = data_key

        coords = data["coords"]
        iters = data["iterations"]

        if len(coords) == 0:
            return

        if data_key in self._cache:
            cached = self._cache[data_key]
            sub_coords = cached["sub_coords"]
            colors = cached["colors"]
            sizes = cached["sizes"]
            c_x, c_y, c_z = cached["center"]
            camera_dist = cached["camera_dist"]
            grid_size = cached["grid_size"]
            min_p = cached["min_p"]
            px_xy, py_xy = cached["projs"][0]
            px_xz, py_xz = cached["projs"][1]
            px_yz, py_yz = cached["projs"][2]
            brushes = cached["brushes"]
        else:
            # Downsample coordinates for smooth 60 FPS rendering
            MAX_POINTS = 150000
            step = max(1, len(coords) // MAX_POINTS)
            sub_coords = coords[::step].astype(np.float32)
            sub_iters = iters[::step]

            # Color gradient
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

            idx = np.minimum(
                (norm_t * (len(stops) - 1)).astype(int),
                len(stops) - 1,
            )

            colors = stops[idx]
            colors = np.column_stack(
                [
                    colors,
                    np.full(len(colors), 0.90, dtype=np.float32),
                ]
            ).astype(np.float32)

            sizes = np.full(len(sub_coords), 5.0, dtype=np.float32)
            sizes[norm_t >= 0.75] = 6.0
            sizes[norm_t >= 0.90] = 7.0
            sizes[norm_t >= 0.97] = 9.0

            # Calculate bounding box & auto-scale camera distance
            min_p = np.min(sub_coords, axis=0)
            max_p = np.max(sub_coords, axis=0)
            center = (min_p + max_p) / 2.0
            extent = float(np.max(max_p - min_p))

            c_x = float(center[0])
            c_y = float(center[1])
            c_z = float(center[2]) if len(center) > 2 else 0.0

            camera_dist = max(extent * 1.6, 20.0)
            grid_size = max(extent * 1.2, 10.0)

            # 2D Projections (XY, XZ, YZ)
            x = coords[:, 0]
            y = coords[:, 1]
            z = coords[:, 2] if coords.shape[1] > 2 else np.zeros_like(x)

            step_2d = max(1, len(coords) // 50000)
            sub_iters_2d = iters[::step_2d]

            norm_2d = (sub_iters_2d - sub_iters_2d.min()) / max(
                1,
                sub_iters_2d.max() - sub_iters_2d.min(),
            )

            idx_2d = np.minimum(
                (norm_2d * (len(stops) - 1)).astype(int),
                len(stops) - 1,
            )

            colors_2d = (stops[idx_2d] * 255).astype(np.uint8)
            brushes = [pg.mkBrush(int(r), int(g), int(b), 210) for r, g, b in colors_2d]

            px_xy, py_xy = x[::step_2d], y[::step_2d]
            px_xz, py_xz = x[::step_2d], z[::step_2d]
            px_yz, py_yz = y[::step_2d], z[::step_2d]

            cached = {
                "sub_coords": sub_coords,
                "colors": colors,
                "sizes": sizes,
                "center": (c_x, c_y, c_z),
                "camera_dist": camera_dist,
                "grid_size": grid_size,
                "min_p": min_p,
                "projs": [(px_xy, py_xy), (px_xz, py_xz), (px_yz, py_yz)],
                "brushes": brushes,
            }
            self._cache[data_key] = cached

        # 1. 3D OpenGL Scatter Plot
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
        self.grid_item.translate(c_x, c_y, float(min_p[2] if len(min_p) > 2 else 0))
        self.gl_widget.addItem(self.grid_item)

        # 2. Render 2D Projections
        for plt_widget, (px, py), xl, yl in [
            (self.plot_xy, (px_xy, py_xy), "Seq A (i)", "Seq B (j)"),
            (self.plot_xz, (px_xz, py_xz), "Seq A (i)", "Seq C (k)"),
            (self.plot_yz, (px_yz, py_yz), "Seq B (j)", "Seq C (k)"),
        ]:
            plt_widget.clear()
            plt_widget.setLabel("bottom", xl)
            plt_widget.setLabel("left", yl)
            item = pg.ScatterPlotItem(
                x=px,
                y=py,
                size=3,
                pen=None,
                brush=brushes,
            )
            plt_widget.addItem(item)
