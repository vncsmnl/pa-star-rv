"""
Integration test for MainWindow and all canvases (offscreen mode) using pytest.
"""

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


def test_canvases_synthetic_data(qapp, make_synthetic_data):
    data_a = make_synthetic_data(n_nodes=1000, max_coord=100, is_candidate=False)
    data_b = make_synthetic_data(n_nodes=600, max_coord=100, is_candidate=True)

    # 1. Test CanvasSummary
    summary = CanvasSummary()
    summary.set_data(data_a, data_b, "Synth_A", "Synth_B")
    assert "1,000" in summary.kpi_nodes_a.text()
    assert "600" in summary.kpi_nodes_b.text()

    # 2. Test CanvasSavings
    savings = CanvasSavings()
    savings.set_data(data_a, data_b, "Synth_A", "Synth_B")
    assert "1,000" in savings.card_nodes_a.text()
    assert "600" in savings.card_nodes_b.text()

    # 3. Test CanvasFootprint
    footprint = CanvasFootprint()
    footprint.set_data(data_a, data_b, "Synth_A", "Synth_B")
    assert footprint.table_occ.rowCount() == 3

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


def test_mainwindow_flow(qapp, make_synthetic_data):
    win = MainWindow()
    data_a = make_synthetic_data(n_nodes=500, max_coord=100, is_candidate=False)
    data_b = make_synthetic_data(n_nodes=300, max_coord=100, is_candidate=True)

    # Simulate loading A
    win._on_parse_done("a", data_a, "test_a.txt", None)
    assert win.data_a is not None
    assert win.lbl_a.text() == "A: test_a.txt"

    # Simulate loading B
    win._on_parse_done("b", data_b, "test_b.txt", None)
    assert win.data_b is not None
    assert win.lbl_b.text() == "B: test_b.txt"

    # Verify all tabs can be switched and grabbed as pixmaps
    for idx in range(win.tabs.count()):
        win.tabs.setCurrentIndex(idx)
        win._update_active_tab()
        canvas = win._canvases[TAB_DEFS[idx][0]]
        pixmap = canvas.grab()
        assert not pixmap.isNull()

    win.close()
