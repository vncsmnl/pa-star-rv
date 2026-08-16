"""
Integration test for MainWindow and all canvases (offscreen mode).
"""

import os
import unittest

import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtWidgets import QApplication

from pastar_rv.app import TAB_DEFS, MainWindow
from pastar_rv.widgets import (
    Canvas3D,
    CanvasBand,
    CanvasDensity,
    CanvasDynamics,
    CanvasFootprint,
    CanvasHeuristicComparison,
    CanvasSavings,
    CanvasSummary,
)


class TestGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def _create_synthetic_data(self, n_nodes, max_coord=100, is_candidate=False):
        coords = np.random.randint(0, max_coord, size=(n_nodes, 3), dtype=np.int32)
        h = np.random.randint(
            10 if not is_candidate else 20,
            100 if not is_candidate else 120,
            size=n_nodes,
            dtype=np.int32,
        )
        g = np.random.randint(0, 50, size=n_nodes, dtype=np.int32)
        f = h + g
        dev = np.random.uniform(0, 10, size=n_nodes).astype(np.float32)
        num_jumps = max(1, n_nodes // 10)
        j_dists = np.random.randint(1, 20, size=num_jumps, dtype=np.int32)
        j_indices = np.random.choice(n_nodes, size=num_jumps, replace=False).astype(np.int32)

        return {
            "iterations": np.arange(n_nodes, dtype=np.int32),
            "coords": coords,
            "g": g,
            "h": h,
            "f": f,
            "dimensions": 3,
            "dev": dev,
            "num_jumps": num_jumps,
            "jump_distances": j_dists,
            "jump_indices": j_indices,
        }

    def test_canvases_synthetic_data(self):
        data_a = self._create_synthetic_data(1000, 100, False)
        data_b = self._create_synthetic_data(600, 100, True)

        # 1. Test CanvasSummary
        summary = CanvasSummary()
        summary.set_data(data_a, data_b, "Synth_A", "Synth_B")
        self.assertIn("1,000", summary.kpi_nodes_a.text())
        self.assertIn("600", summary.kpi_nodes_b.text())

        # 2. Test CanvasSavings
        savings = CanvasSavings()
        savings.set_data(data_a, data_b, "Synth_A", "Synth_B")
        self.assertIn("1,000", savings.card_nodes_a.text())
        self.assertIn("600", savings.card_nodes_b.text())

        # 3. Test CanvasFootprint
        footprint = CanvasFootprint()
        footprint.set_data(data_a, data_b, "Synth_A", "Synth_B")
        self.assertEqual(footprint.table_occ.rowCount(), 3)

        # 4. Test CanvasHeuristicComparison
        heuristic = CanvasHeuristicComparison()
        heuristic.set_data(data_a, data_b, "Synth_A", "Synth_B")

        # 5. Test CanvasBand
        band = CanvasBand()
        band.set_data_comparison(data_a, data_b, "Synth_A", "Synth_B")
        band.set_data(data_a, "Synth_A")

        # 6. Test CanvasDensity
        density = CanvasDensity()
        density.set_data(data_a, "Synth_A")

        # 7. Test CanvasDynamics
        dynamics = CanvasDynamics()
        dynamics.set_data(data_a, "Synth_A")

        # 8. Test Canvas3D
        canvas3d = Canvas3D()
        canvas3d.set_data(data_a, "Synth_A")

    def test_mainwindow_flow(self):
        win = MainWindow()
        data_a = self._create_synthetic_data(500, 100, False)
        data_b = self._create_synthetic_data(300, 100, True)

        # Simulate loading A
        win._on_parse_done("a", data_a, "test_a.txt", None)
        self.assertIsNotNone(win.data_a)
        self.assertEqual(win.lbl_a.text(), "A: test_a.txt")

        # Simulate loading B
        win._on_parse_done("b", data_b, "test_b.txt", None)
        self.assertIsNotNone(win.data_b)
        self.assertEqual(win.lbl_b.text(), "B: test_b.txt")

        # Verify all tabs can be switched and grabbed as pixmaps
        for idx in range(win.tabs.count()):
            win.tabs.setCurrentIndex(idx)
            win._update_active_tab()
            canvas = win._canvases[TAB_DEFS[idx][0]]
            pixmap = canvas.grab()
            self.assertFalse(pixmap.isNull())

        win.close()


if __name__ == "__main__":
    unittest.main()
