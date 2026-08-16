"""
Tests for metrics.py using pytest.
"""

import numpy as np
import pytest

from pastar_rv.metrics import (
    ComparisonCache,
    check_f_consistency,
    compute_all_pairwise_footprints,
    compute_binned_percentiles,
    compute_common_states_analysis,
    compute_expansion_savings,
    compute_footprint_data,
    compute_geometric_alignment_progress,
    deduplicate_and_diagnose_states,
    get_pair_label,
    get_projection_pairs,
)


def test_geometric_alignment_progress():
    # 1. 2D Coordinates
    c2 = np.array([[0, 0], [50, 50], [100, 100]], dtype=np.int32)
    p2 = compute_geometric_alignment_progress(c2)
    np.testing.assert_allclose(p2, [0.0, 0.5, 1.0])

    # 2. 3D Coordinates with explicit reference
    c3 = np.array([[10, 20, 30], [20, 40, 60]], dtype=np.int32)
    ref = np.array([20, 40, 60], dtype=np.int32)
    p3 = compute_geometric_alignment_progress(c3, reference_coords=ref)
    np.testing.assert_allclose(p3, [0.5, 1.0])

    # 3. 5D Coordinates
    c5 = np.ones((10, 5), dtype=np.int32) * 50
    ref5 = np.ones(5, dtype=np.int32) * 100
    p5 = compute_geometric_alignment_progress(c5, reference_coords=ref5)
    np.testing.assert_allclose(p5, np.full(10, 0.5))

    # 4. Zero reference dimension (no divide-by-zero error)
    c_zero = np.array([[0, 10], [0, 20]], dtype=np.int32)
    p_zero = compute_geometric_alignment_progress(c_zero)
    assert len(p_zero) == 2
    assert not np.isnan(p_zero).any()
    assert not np.isinf(p_zero).any()

    # 5. Empty coords
    p_empty = compute_geometric_alignment_progress(np.empty((0, 3)))
    assert len(p_empty) == 0


def test_binned_percentiles():
    # Linear distribution
    prog = np.linspace(0.0, 1.0, 1000)
    vals = np.linspace(10.0, 110.0, 1000)
    res = compute_binned_percentiles(prog, vals, n_bins=10, percentiles=(25, 50, 75, 90))

    assert len(res["bin_centers"]) == 10
    assert len(res["counts"]) == 10
    assert np.all(res["counts"] > 0)
    assert not np.isnan(res["median"]).any()

    # Empty bin handling
    prog_sparse = np.array([0.05, 0.95])
    vals_sparse = np.array([10.0, 20.0])
    res_sparse = compute_binned_percentiles(prog_sparse, vals_sparse, n_bins=10)
    assert np.isnan(res_sparse["median"][5])
    assert res_sparse["counts"][5] == 0


def test_expansion_savings():
    # Baseline A has 100 nodes, Candidate B has 60 nodes
    prog_a = np.linspace(0.0, 1.0, 100)
    prog_b = np.linspace(0.0, 1.0, 60)

    res = compute_expansion_savings(prog_a, prog_b, n_bins=10, min_support=5)
    assert res["expansions_a"] == 100
    assert res["expansions_b"] == 60
    assert res["total_nodes_saved"] == 40
    assert res["total_reduction_pct"] == pytest.approx(40.0)

    # Cumulative difference at end should equal total saved
    assert res["cum_diff"][-1] == 40

    # Local saved sum should equal total saved
    assert np.sum(res["local_saved"]) == 40

    # Test safe masked division with min_support
    prog_a_sparse = np.array([0.1, 0.1, 0.9])
    prog_b_sparse = np.array([0.1, 0.9])
    res_sparse = compute_expansion_savings(prog_a_sparse, prog_b_sparse, n_bins=5, min_support=5)
    # All bins have < 5 elements in A, so local_reduction and local_ratio must be NaN
    assert np.isnan(res_sparse["local_reduction"]).all()
    assert np.isnan(res_sparse["local_ratio"]).all()
    # But local_saved is still available and exact
    assert np.sum(res_sparse["local_saved"]) == 1


def test_footprint_data():
    coords_a = np.array([[0, 0], [10, 10], [20, 20]], dtype=np.int32)
    coords_b = np.array([[10, 10], [30, 30], [40, 40]], dtype=np.int32)

    res = compute_footprint_data(coords_a, coords_b, proj_dims=(0, 1), n_bins=10)

    assert "diff_abs" in res
    assert "diff_rel" in res
    assert "jaccard" in res
    assert res["n_occupied_a"] > 0
    assert res["n_occupied_b"] > 0
    assert res["n_shared"] > 0
    assert 0.0 <= res["jaccard"] <= 1.0


def test_f_consistency():
    g = np.array([10, 20, 30], dtype=np.int32)
    h = np.array([5, 10, 15], dtype=np.int32)
    f = np.array([15, 30, 45], dtype=np.int32)

    res = check_f_consistency(g, h, f)
    assert res["total_entries"] == 3
    assert res["match_count"] == 3
    assert res["mismatch_count"] == 0
    assert res["match_pct"] == 100.0

    # With 1 mismatch
    f_bad = np.array([15, 30, 999], dtype=np.int32)
    res_bad = check_f_consistency(g, h, f_bad)
    assert res_bad["match_count"] == 2
    assert res_bad["mismatch_count"] == 1


def test_deduplicate_and_diagnose_states():
    # 4 entries: (1,1,1) duplicated with same h/g, (2,2,2) duplicated with diff h, (3,3,3) duplicated with diff g
    coords = np.array(
        [
            [1, 1, 1],
            [1, 1, 1],
            [2, 2, 2],
            [2, 2, 2],
            [3, 3, 3],
            [3, 3, 3],
            [4, 4, 4],
        ],
        dtype=np.int32,
    )
    h = np.array([10, 10, 20, 25, 30, 30, 40], dtype=np.int32)  # (2,2,2) has diff h (20 vs 25)
    g = np.array([5, 5, 15, 15, 30, 35, 40], dtype=np.int32)  # (3,3,3) has diff g (30 vs 35)

    res = deduplicate_and_diagnose_states(coords, h, g)

    assert res["num_total_entries"] == 7
    assert res["num_unique_states"] == 4
    assert res["inconsistent_h_count"] == 1
    assert res["inconsistent_g_count"] == 1

    # State (1,1,1) -> consistent h and g
    assert res["h_is_consistent"][0]
    assert res["g_is_consistent"][0]

    # State (2,2,2) -> inconsistent h, consistent g
    assert not res["h_is_consistent"][1]
    assert res["g_is_consistent"][1]

    # State (3,3,3) -> consistent h, inconsistent g
    assert res["h_is_consistent"][2]
    assert not res["g_is_consistent"][2]

    # State (4,4,4) -> consistent h and g
    assert res["h_is_consistent"][3]
    assert res["g_is_consistent"][3]


def test_common_states_analysis():
    # Dataset A: 3 unique states (1,1,1), (2,2,2), (3,3,3)
    coords_a = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3]], dtype=np.int32)
    h_a = np.array([10, 20, 30], dtype=np.int32)
    g_a = np.array([5, 10, 15], dtype=np.int32)
    f_a = h_a + g_a

    # Dataset B: 3 unique states (2,2,2), (3,3,3), (4,4,4)
    coords_b = np.array([[2, 2, 2], [3, 3, 3], [4, 4, 4]], dtype=np.int32)
    h_b = np.array(
        [25, 30, 40], dtype=np.int32
    )  # for (2,2,2): dh = 25 - 20 = +5; for (3,3,3): dh = 30 - 30 = 0
    g_b = np.array(
        [10, 20, 40], dtype=np.int32
    )  # for (2,2,2): g equal; for (3,3,3): g diff (15 vs 20)
    f_b = h_b + g_b

    res = compute_common_states_analysis(
        coords_a,
        h_a,
        g_a,
        f_a,
        coords_b,
        h_b,
        g_b,
        f_b,
    )

    assert res["num_unique_a"] == 3
    assert res["num_unique_b"] == 3
    assert res["num_common_unique"] == 2
    assert res["num_only_a"] == 1
    assert res["num_only_b"] == 1

    assert res["num_valid_h_common"] == 2
    np.testing.assert_array_equal(res["delta_h"], [5.0, 0.0])
    assert res["pct_delta_h_pos"] == 50.0
    assert res["pct_delta_h_zero"] == 50.0
    assert res["pct_delta_h_neg"] == 0.0

    assert res["num_valid_g_common"] == 2
    assert res["num_g_match"] == 1
    assert res["num_g_mismatch"] == 1
    assert res["pct_g_match"] == 50.0


def test_comparison_cache():
    cache = ComparisonCache()
    assert len(cache) == 0

    cache.set("key1", {"test": 123})
    assert len(cache) == 1
    assert cache.get("key1")["test"] == 123

    cache.clear()
    assert len(cache) == 0
    assert cache.get("key1") is None


def test_projection_pairs_and_labels():
    pairs_3d = get_projection_pairs(3)
    assert pairs_3d == [(0, 1), (0, 2), (1, 2)]

    pairs_6d = get_projection_pairs(6)
    assert len(pairs_6d) == 15
    assert pairs_6d[0] == (0, 1)
    assert pairs_6d[-1] == (4, 5)

    assert get_pair_label(0, 1, prefix="Seq ") == "Seq 1 vs Seq 2"
    assert get_pair_label(3, 5, prefix="S") == "S4 vs S6"


def test_all_pairwise_footprints_6d():
    n = 200
    c6_a = np.random.randint(0, 100, size=(n, 6), dtype=np.int32)
    c6_b = np.random.randint(0, 100, size=(n, 6), dtype=np.int32)

    res = compute_all_pairwise_footprints(c6_a, c6_b, dimensions=6, n_bins=15)
    assert res["dimensions"] == 6
    assert len(res["pairs"]) == 15
    assert len(res["footprints"]) == 15
    assert 0.0 <= res["mean_jaccard"] <= 1.0

    for pair in res["pairs"]:
        fp = res["footprints"][pair]
        assert "diff_abs" in fp
        assert "diff_rel" in fp
        assert "jaccard" in fp
        assert fp["diff_abs"].shape == (15, 15)


def test_d_dimensional_common_states_6d():
    # 6D coordinates
    c6_a = np.array([[1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50, 60]], dtype=np.int32)
    h_a = np.array([50, 100], dtype=np.int32)
    g_a = np.array([10, 20], dtype=np.int32)
    f_a = h_a + g_a

    c6_b = np.array([[1, 2, 3, 4, 5, 6], [99, 99, 99, 99, 99, 99]], dtype=np.int32)
    h_b = np.array([60, 200], dtype=np.int32)
    g_b = np.array([10, 30], dtype=np.int32)
    f_b = h_b + g_b

    res = compute_common_states_analysis(c6_a, h_a, g_a, f_a, c6_b, h_b, g_b, f_b)
    assert res["num_unique_a"] == 2
    assert res["num_unique_b"] == 2
    assert res["num_common_unique"] == 1
    assert res["num_only_a"] == 1
    assert res["num_only_b"] == 1
    assert res["num_valid_h_common"] == 1
    assert res["delta_h"][0] == 10.0  # 60 - 50 = +10
