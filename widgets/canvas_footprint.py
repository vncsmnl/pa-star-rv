"""
Search Footprint Comparison Widget (File A vs File B)
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtWidgets import QGridLayout, QWidget
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtWidgets import QGridLayout, QWidget


class CanvasFootprint(QWidget):
    """Dual File Footprint Comparison and Density Difference Maps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._build_ui()

    def _build_ui(self):
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self._plots = []

    def set_data(self, da, db, la="A", lb="B"):
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key
        # Clear existing layout
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._plots.clear()

        cA = da["coords"]
        cB = db["coords"]
        if len(cA) == 0 or len(cB) == 0:
            return

        xA, yA = cA[:, 0], cA[:, 1]
        zA = cA[:, 2] if cA.shape[1] > 2 else np.zeros_like(xA)

        xB, yB = cB[:, 0], cB[:, 1]
        zB = cB[:, 2] if cB.shape[1] > 2 else np.zeros_like(xB)

        BINS = 80
        pos_plasma = np.array([0.0, 0.5, 1.0])
        col_plasma = np.array(
            [[13, 8, 135, 255], [204, 71, 120, 255], [240, 249, 33, 255]],
            dtype=np.ubyte,
        )
        lut_plasma = pg.ColorMap(pos_plasma, col_plasma).getLookupTable(0.0, 1.0, 256)

        pos_rdbu = np.array([0.0, 0.5, 1.0])
        col_rdbu = np.array(
            [[31, 119, 180, 255], [255, 255, 255, 255], [214, 39, 40, 255]],
            dtype=np.ubyte,
        )
        lut_rdbu = pg.ColorMap(pos_rdbu, col_rdbu).getLookupTable(0.0, 1.0, 256)

        rows = [
            (xA, yA, xB, yB, "Seq A (i)", "Seq B (j)", "XY (Top)"),
            (xA, zA, xB, zB, "Seq A (i)", "Seq C (k)", "XZ (Front)"),
            (yA, zA, yB, zB, "Seq B (j)", "Seq C (k)", "YZ (Side)"),
        ]

        for r_idx, (xda, yda, xdb, ydb, xl, yl, tt) in enumerate(rows):
            all_x = np.concatenate([xda, xdb])
            all_y = np.concatenate([yda, ydb])
            rng = [[all_x.min(), all_x.max()], [all_y.min(), all_y.max()]]

            HA, xe, ye = np.histogram2d(xda, yda, bins=BINS, range=rng)
            HB, _, _ = np.histogram2d(xdb, ydb, bins=BINS, range=rng)

            vmax = max(HA.max(), HB.max(), 1)
            rect = pg.QtCore.QRectF(xe[0], ye[0], xe[-1] - xe[0], ye[-1] - ye[0])

            # Plot A
            p_a = pg.PlotWidget(title=f"{tt} · A: {la} ({len(xda):,} nodes)")
            p_a.setBackground("w")
            p_a.setLabel("bottom", xl)
            p_a.setLabel("left", yl)
            img_a = pg.ImageItem()
            img_a.setImage(np.log1p(HA) / np.log1p(vmax))
            img_a.setLookupTable(lut_plasma)
            img_a.setRect(rect)
            p_a.addItem(img_a)
            self.layout.addWidget(p_a, r_idx, 0)

            # Plot B
            p_b = pg.PlotWidget(title=f"{tt} · B: {lb} ({len(xdb):,} nodes)")
            p_b.setBackground("w")
            p_b.setLabel("bottom", xl)
            p_b.setLabel("left", yl)
            img_b = pg.ImageItem()
            img_b.setImage(np.log1p(HB) / np.log1p(vmax))
            img_b.setLookupTable(lut_plasma)
            img_b.setRect(rect)
            p_b.addItem(img_b)
            self.layout.addWidget(p_b, r_idx, 1)

            # Difference (B - A)
            HAn = HA / max(HA.sum(), 1)
            HBn = HB / max(HB.sum(), 1)
            diff = HBn - HAn
            amax = max(np.abs(diff).max(), 1e-9)

            p_diff = pg.PlotWidget(
                title=f"{tt} · Difference (Blue=A more | Red=B more)"
            )
            p_diff.setBackground("w")
            p_diff.setLabel("bottom", xl)
            p_diff.setLabel("left", yl)
            img_diff = pg.ImageItem()
            img_diff.setImage((diff / amax + 1.0) / 2.0)
            img_diff.setLookupTable(lut_rdbu)
            img_diff.setRect(rect)
            p_diff.addItem(img_diff)
            self.layout.addWidget(p_diff, r_idx, 2)
