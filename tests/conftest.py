"""
Pytest configuration and shared fixtures for PA-Star Runtime Visualizer tests.
"""

import os

import numpy as np
import pytest

# Ensure Qt runs in offscreen mode for headless test execution
os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance for GUI testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def make_synthetic_data():
    """Factory fixture to create synthetic search datasets for tests."""

    def _factory(n_nodes=1000, max_coord=100, is_candidate=False, dimensions=3):
        coords = np.random.randint(0, max_coord, size=(n_nodes, dimensions), dtype=np.int32)
        h = np.random.randint(
            10 if not is_candidate else 20,
            100 if not is_candidate else 120,
            size=n_nodes,
            dtype=np.int32,
        )
        g = np.random.randint(0, 50, size=n_nodes, dtype=np.int32)
        f = h + g
        mean_coords = np.mean(coords, axis=1, keepdims=True)
        dev = np.sqrt(np.sum((coords - mean_coords) ** 2, axis=1, dtype=np.float64)).astype(np.float32)
        num_jumps = max(1, n_nodes // 10)
        j_dists = np.random.randint(1, 20, size=num_jumps, dtype=np.int32)
        j_indices = np.random.choice(n_nodes, size=num_jumps, replace=False).astype(np.int32)

        return {
            "iterations": np.arange(n_nodes, dtype=np.int32),
            "coords": coords,
            "g": g,
            "h": h,
            "f": f,
            "dimensions": dimensions,
            "dev": dev,
            "num_jumps": num_jumps,
            "jump_distances": j_dists,
            "jump_indices": j_indices,
        }

    return _factory
