"""
Comparative Analytics and Metrics Summary Widget
"""

import numpy as np

try:
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QGridLayout,
        QHeaderView,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QGridLayout,
        QHeaderView,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )


class CanvasComparison(QWidget):
    """Dual File Comparison Metrics & Summary Table Canvas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        grid = QGridLayout()

        self.plot_min_h = pg.PlotWidget(
            title="Frontier Quality (min h — Lower is better)"
        )
        self.plot_avg_h = pg.PlotWidget(title="Frontier Informativeness (avg h)")
        self.plot_dev = pg.PlotWidget(title="Band Deviation (Overlaid Density)")
        self.plot_bars = pg.PlotWidget(title="Absolute Metrics Comparison")

        for p in (self.plot_min_h, self.plot_avg_h, self.plot_dev, self.plot_bars):
            p.setBackground("w")
            p.showGrid(x=True, y=True, alpha=0.3)
            p.getAxis("left").setPen("k")
            p.getAxis("bottom").setPen("k")

        grid.addWidget(self.plot_min_h, 0, 0)
        grid.addWidget(self.plot_avg_h, 0, 1)
        grid.addWidget(self.plot_dev, 1, 0)
        grid.addWidget(self.plot_bars, 1, 1)

        layout.addLayout(grid)

        # Summary Improvement Table
        self.lbl_table_title = QLabel("Improvement Summary Table (B vs A)")
        self.lbl_table_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.lbl_table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Metric", "File A", "File B", "Reduction (%)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setMaximumHeight(160)
        layout.addWidget(self.table)

    def set_data(self, da, db, la="A", lb="B"):
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key
        hA, hB = da["h"], db["h"]
        tA, tB = da["iterations"], db["iterations"]
        devA, devB = da["dev"], db["dev"]

        nA, nB = len(hA), len(hB)
        if nA == 0 or nB == 0:
            return

        # 1. Min h & Avg h Curves
        W_a, W_b = max(50, nA // 100), max(50, nB // 100)

        step_a = max(1, nA // 3000)
        step_b = max(1, nB // 3000)

        idx_a = np.arange(0, nA, step_a)
        idx_b = np.arange(0, nB, step_b)

        pad_a = np.pad(hA, W_a // 2, mode="edge")
        pad_b = np.pad(hB, W_b // 2, mode="edge")

        min_hA = [np.min(pad_a[i : i + W_a]) for i in idx_a]
        min_hB = [np.min(pad_b[i : i + W_b]) for i in idx_b]

        avg_hA = [np.mean(pad_a[i : i + W_a]) for i in idx_a]
        avg_hB = [np.mean(pad_b[i : i + W_b]) for i in idx_b]

        norm_a = idx_a / max(1, nA - 1)
        norm_b = idx_b / max(1, nB - 1)

        self.plot_min_h.clear()
        self.plot_min_h.setLabel("bottom", "Normalised progress")
        self.plot_min_h.setLabel("left", "min h(n)")
        self.plot_min_h.plot(
            norm_a, min_hA, pen=pg.mkPen("#1f77b4", width=2), name=f"A: {la}"
        )
        self.plot_min_h.plot(
            norm_b, min_hB, pen=pg.mkPen("#d62728", width=2), name=f"B: {lb}"
        )

        self.plot_avg_h.clear()
        self.plot_avg_h.setLabel("bottom", "Normalised progress")
        self.plot_avg_h.setLabel("left", "avg h(n)")
        self.plot_avg_h.plot(
            norm_a, avg_hA, pen=pg.mkPen("#1f77b4", width=2), name=f"A: {la}"
        )
        self.plot_avg_h.plot(
            norm_b, avg_hB, pen=pg.mkPen("#d62728", width=2), name=f"B: {lb}"
        )

        # 2. Band Deviation Histogram Overlaid
        self.plot_dev.clear()
        self.plot_dev.setLabel("bottom", "Deviation")
        self.plot_dev.setLabel("left", "Count")

        bins = np.linspace(
            0, max(devA.max() if len(devA) else 1, devB.max() if len(devB) else 1), 50
        )
        yA, _ = np.histogram(devA, bins=bins)
        yB, _ = np.histogram(devB, bins=bins)

        bgA = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=yA,
            pen=pg.mkPen(color=(31, 119, 180, 150)),
            brush=pg.mkBrush(31, 119, 180, 150),
        )
        bgB = pg.BarGraphItem(
            x0=bins[:-1],
            x1=bins[1:],
            height=yB,
            pen=pg.mkPen(color=(214, 39, 40, 150)),
            brush=pg.mkBrush(214, 39, 40, 150),
        )
        self.plot_dev.addItem(bgA)
        self.plot_dev.addItem(bgB)

        # 3. Absolute Bars Comparison
        self.plot_bars.clear()
        metrics_names = ["Nodes Explored", "Jumps", "Mean Dev"]
        val_a = [len(tA), da["num_jumps"], float(np.mean(devA))]
        val_b = [len(tB), db["num_jumps"], float(np.mean(devB))]

        x_pos = np.arange(len(metrics_names))
        w = 0.35

        bar_a = pg.BarGraphItem(
            x=x_pos - w / 2,
            height=val_a,
            width=w,
            brush=pg.mkBrush("#1f77b4"),
        )
        bar_b = pg.BarGraphItem(
            x=x_pos + w / 2,
            height=val_b,
            width=w,
            brush=pg.mkBrush("#d62728"),
        )
        self.plot_bars.addItem(bar_a)
        self.plot_bars.addItem(bar_b)

        # 4. Table Update
        def _pct(a, b):
            if a == 0:
                return "N/A"
            r = (a - b) / a * 100
            prefix = "−" if r >= 0 else "+"
            return f"{prefix}{abs(r):.1f} %"

        table_rows = [
            ("Nodes Explored", f"{len(tA):,}", f"{len(tB):,}", _pct(len(tA), len(tB))),
            (
                "Jumps",
                f"{da['num_jumps']:,}",
                f"{db['num_jumps']:,}",
                _pct(da["num_jumps"], db["num_jumps"]),
            ),
            (
                "Mean Deviation",
                f"{np.mean(devA):.1f}",
                f"{np.mean(devB):.1f}",
                _pct(np.mean(devA), np.mean(devB)),
            ),
        ]

        self.table.setRowCount(len(table_rows))
        for r, (m_name, v_a, v_b, pct) in enumerate(table_rows):
            self.table.setItem(r, 0, QTableWidgetItem(m_name))
            self.table.setItem(r, 1, QTableWidgetItem(v_a))
            self.table.setItem(r, 2, QTableWidgetItem(v_b))
            item_pct = QTableWidgetItem(pct)
            item_pct.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, item_pct)
