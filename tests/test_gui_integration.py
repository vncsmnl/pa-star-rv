"""
Integration test for MainWindow and all canvases (offscreen mode) using pytest.
"""

from pastar_rv.app import TAB_DEFS, MainWindow
from pastar_rv.widgets import (
    CanvasBand,
    CanvasDensity,
    CanvasDynamics,
    CanvasFootprint,
    CanvasHeuristicComparison,
    CanvasSavings,
    CanvasStateSpace,
    CanvasSummary,
)


def test_canvases_synthetic_data_3d(qapp, make_synthetic_data):
    data_a = make_synthetic_data(n_nodes=1000, max_coord=100, is_candidate=False, dimensions=3)
    data_b = make_synthetic_data(n_nodes=600, max_coord=100, is_candidate=True, dimensions=3)

    # 1. Test CanvasSummary
    summary = CanvasSummary()
    summary.set_data(data_a, data_b, "Synth_A", "Synth_B")
    assert "1,000" in summary.kpi_nodes_a.text()
    assert "600" in summary.kpi_nodes_b.text()
    assert summary.table_fp.rowCount() == 3

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

    # 8. Test CanvasStateSpace (Canvas3D)
    canvas_ss = CanvasStateSpace()
    canvas_ss.set_data(data_a, "Synth_A")
    assert "Complete 3D" in canvas_ss.lbl_mode_badge.text()


def test_canvases_synthetic_data_6d(qapp, make_synthetic_data):
    data_a = make_synthetic_data(n_nodes=800, max_coord=100, is_candidate=False, dimensions=6)
    data_b = make_synthetic_data(n_nodes=500, max_coord=100, is_candidate=True, dimensions=6)

    # 1. CanvasSummary for 6D
    summary = CanvasSummary()
    summary.set_data(data_a, data_b, "Synth6_A", "Synth6_B")
    assert summary.table_fp.rowCount() == 15

    # 2. CanvasFootprint Pairwise Matrix for 6D
    footprint = CanvasFootprint()
    footprint.set_data(data_a, data_b, "Synth6_A", "Synth6_B")
    assert footprint.table_occ.rowCount() == 15
    assert footprint.combo_detail_pair.count() == 15

    # Test selecting a pair in detailed view
    footprint.combo_detail_pair.setCurrentIndex(5)
    assert "Seq" in footprint.lbl_detail_jaccard.text()

    # 3. CanvasStateSpace for 6D (3D projection warning + selectors)
    state_space = CanvasStateSpace()
    state_space.set_data(data_a, "Synth6_A")
    assert "3D Projection" in state_space.lbl_mode_badge.text()
    assert state_space.combo_3d_x.count() == 6
    assert state_space.combo_2d_x.count() == 6

    # Change selected 2D projection
    state_space.combo_2d_x.setCurrentIndex(0)
    state_space.combo_2d_y.setCurrentIndex(3)
    assert "Seq 1 (x) vs Seq 4 (y)" in state_space.plot_selected_2d.plotItem.titleLabel.text

    # 4. CanvasDensity for 6D
    density = CanvasDensity()
    density.set_data(data_a, "Synth6_A")
    assert density.combo_x.count() == 6
    density.combo_x.setCurrentIndex(1)
    density.combo_y.setCurrentIndex(4)


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


def test_info_badges_and_tooltips(qapp):
    from pastar_rv.widgets.info_helper import TOOLTIPS, InfoBadge, create_info_badge

    # Test TOOLTIPS contents
    assert len(TOOLTIPS) >= 25
    for text in TOOLTIPS.values():
        assert "ℹ" in text
        assert "div" in text

    # Test InfoBadge creation
    badge = create_info_badge("btn_open_a")
    assert isinstance(badge, InfoBadge)
    assert badge.text() == "ℹ"
    assert "Abrir Log A" in badge.toolTip()

    # Test MainWindow tab tooltips
    win = MainWindow()
    for idx in range(win.tabs.count()):
        tip = win.tabs.tabToolTip(idx)
        assert tip is not None and len(tip) > 0
        assert "ℹ" in tip

    win.close()


def test_log_scale_checkboxes(qapp, make_synthetic_data):
    data_a = make_synthetic_data(n_nodes=600, max_coord=80, is_candidate=False, dimensions=3)
    data_b = make_synthetic_data(n_nodes=400, max_coord=80, is_candidate=True, dimensions=3)

    # 1. CanvasSavings
    savings = CanvasSavings()
    savings.set_data(data_a, data_b, "Synth_A", "Synth_B")
    savings.chk_log_cum.setChecked(True)
    assert savings.plot_cum.getAxis("left").logMode is True
    assert "Log₁₀" in savings.plot_cum.plotItem.axes["left"]["item"].labelText
    savings.chk_log_ratio.setChecked(True)
    assert savings.plot_local_ratio.getAxis("left").logMode is True
    assert "Log₁₀" in savings.plot_local_ratio.plotItem.axes["left"]["item"].labelText
    savings.chk_log_cum.setChecked(False)
    assert savings.plot_cum.getAxis("left").logMode is False
    savings.chk_log_ratio.setChecked(False)
    assert savings.plot_local_ratio.getAxis("left").logMode is False

    # 2. CanvasBand
    band = CanvasBand()
    band.set_data_comparison(data_a, data_b, "Synth_A", "Synth_B")
    band.chk_log_dist_abs.setChecked(True)
    assert "Log₁₀" in band.plot_dist_abs.plotItem.axes["left"]["item"].labelText
    band.chk_log_dist_density.setChecked(True)
    assert "Log₁₀" in band.plot_dist_density.plotItem.axes["left"]["item"].labelText
    band.chk_log_dist_abs.setChecked(False)
    band.chk_log_dist_density.setChecked(False)
    # Also test single mode
    band.set_data(data_a, "Synth_A")
    band.chk_log_dist_abs.setChecked(True)
    band.chk_log_dist_density.setChecked(True)

    # 3. CanvasDynamics
    dynamics = CanvasDynamics()
    dynamics.set_data(data_a, "Synth_A")
    dynamics.chk_log_jdist.setChecked(True)
    assert "Log₁₀" in dynamics.plot_jdist.plotItem.axes["left"]["item"].labelText
    dynamics.chk_log_cumj.setChecked(True)
    assert dynamics.plot_cumj.getAxis("left").logMode is True
    dynamics.chk_log_jdist.setChecked(False)
    dynamics.chk_log_cumj.setChecked(False)

    # 4. CanvasHeuristicComparison
    heuristic = CanvasHeuristicComparison()
    heuristic.set_data(data_a, data_b, "Synth_A", "Synth_B")
    heuristic.chk_log_dh.setChecked(True)
    assert "Log₁₀" in heuristic.plot_dh_hist.plotItem.axes["left"]["item"].labelText
    heuristic.chk_log_dh.setChecked(False)
    assert "Number of Common States" in heuristic.plot_dh_hist.plotItem.axes["left"]["item"].labelText

    # 5. CanvasDensity
    density = CanvasDensity()
    density.set_data(data_a, "Synth_A")
    assert density.chk_log_intensity.isChecked() is True
    assert "[Log₁₊]" in density.plot_main.plotItem.titleLabel.text
    density.chk_log_intensity.setChecked(False)
    assert "[Linear]" in density.plot_main.plotItem.titleLabel.text

    # 6. CanvasFootprint
    footprint = CanvasFootprint()
    footprint.set_data(data_a, data_b, "Synth_A", "Synth_B")
    assert footprint.chk_log_intensity.isChecked() is True
    assert "[Log₁₊ Count]" in footprint.plot_detail_a.plotItem.titleLabel.text
    footprint.chk_log_intensity.setChecked(False)
    assert "[Linear Count]" in footprint.plot_detail_a.plotItem.titleLabel.text
