"""
Independent CLI Validation & Benchmark Script for PA-Star Heuristic Comparison.

Usage:
    pastar-validate <log_a_path> <log_b_path>
    python -m pastar_rv.cli <log_a_path> <log_b_path>
"""

import ctypes
import os
import sys
import time
from ctypes import wintypes

import numpy as np

# Force UTF-8 on Windows standard out
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pastar_rv.metrics import (
    FOOTPRINT_BINS,
    MIN_BIN_SUPPORT,
    PROGRESS_BINS,
    compute_all_pairwise_footprints,
    compute_band_comparison,
    compute_common_states_analysis,
    compute_expansion_savings,
    compute_geometric_alignment_progress,
    deduplicate_and_diagnose_states,
    get_pair_label,
    intersect_unique_states_packed,
    intersect_unique_states_structured,
)
from pastar_rv.parser import parse_log_file

# ─────────────────────────────────────────────
#  MEMORY MEASUREMENT (RSS via Windows API)
# ─────────────────────────────────────────────


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def get_process_memory_info():
    """Returns (current_rss_mb, peak_rss_mb)."""
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        fn.restype = wintypes.BOOL
        if fn(handle, ctypes.byref(counters), counters.cb):
            rss_mb = counters.WorkingSetSize / (1024.0 * 1024.0)
            peak_mb = counters.PeakWorkingSetSize / (1024.0 * 1024.0)
            return rss_mb, peak_mb
    except Exception:
        pass
    return 0.0, 0.0


# ─────────────────────────────────────────────
#  MAIN VALIDATION & BENCHMARK ROUTINE
# ─────────────────────────────────────────────


def main():
    if len(sys.argv) < 3:
        print("Usage: pastar-validate <log_a_path> <log_b_path>")
        sys.exit(1)

    fp_a = sys.argv[1]
    fp_b = sys.argv[2]

    if not os.path.exists(fp_a):
        print(f"Error: File A not found: {fp_a}")
        sys.exit(1)
    if not os.path.exists(fp_b):
        print(f"Error: File B not found: {fp_b}")
        sys.exit(1)

    print("=" * 78)
    print(" PA-STAR RUNTIME VISUALIZER — COMPARISON VALIDATION & BENCHMARK")
    print("=" * 78)
    name_a = os.path.basename(fp_a)
    name_b = os.path.basename(fp_b)
    print(f"Dataset A: {name_a}")
    print(f"Dataset B: {name_b}")
    print("-" * 78)

    rss_init, _ = get_process_memory_info()
    print(f"Initial Process RSS: {rss_init:.1f} MB")

    # 1. Parse Files
    t0 = time.perf_counter()
    print("\n[1/5] Parsing logs...")
    data_a = parse_log_file(fp_a)
    t_parse_a = time.perf_counter() - t0
    rss_a, peak_a = get_process_memory_info()
    print(
        f"  Parsed A: {len(data_a['iterations']):,} nodes (Dims: {data_a['dimensions']}) "
        f"in {t_parse_a:.2f}s (RSS: {rss_a:.1f} MB, Peak: {peak_a:.1f} MB)"
    )

    t1 = time.perf_counter()
    data_b = parse_log_file(fp_b)
    t_parse_b = time.perf_counter() - t1
    rss_b, peak_b = get_process_memory_info()
    print(
        f"  Parsed B: {len(data_b['iterations']):,} nodes (Dims: {data_b['dimensions']}) "
        f"in {t_parse_b:.2f}s (RSS: {rss_b:.1f} MB, Peak: {peak_b:.1f} MB)"
    )

    # 2. Geometric Alignment Progress & Savings
    print("\n[2/5] Computing geometric alignment progress and search savings...")
    t2 = time.perf_counter()
    ref_coords = np.maximum(
        data_a["coords"].max(axis=0),
        data_b["coords"].max(axis=0),
    )
    print(f"  Reference coordinates (inferred max): {ref_coords.tolist()}")
    prog_a = compute_geometric_alignment_progress(data_a["coords"], ref_coords)
    prog_b = compute_geometric_alignment_progress(data_b["coords"], ref_coords)

    savings = compute_expansion_savings(
        prog_a, prog_b, n_bins=PROGRESS_BINS, min_support=MIN_BIN_SUPPORT
    )
    t_savings = time.perf_counter() - t2
    print(f"  Computed savings in {t_savings:.4f}s")

    # 3. Deduplication & Intersection Strategy Benchmarking
    print("\n[3/5] Deduplicating states and benchmarking intersection strategies...")
    t3 = time.perf_counter()
    dedup_a = deduplicate_and_diagnose_states(data_a["coords"], data_a["h"], data_a["g"])
    dedup_b = deduplicate_and_diagnose_states(data_b["coords"], data_b["h"], data_b["g"])
    t_dedup = time.perf_counter() - t3
    print(
        f"  Deduplication: A={dedup_a['num_unique_states']:,} unique, "
        f"B={dedup_b['num_unique_states']:,} unique ({t_dedup:.4f}s)"
    )

    u_a = dedup_a["unique_coords"]
    u_b = dedup_b["unique_coords"]

    # Benchmark Strategy 1: Packed uint64 keys
    t_pack_start = time.perf_counter()
    res_pack = intersect_unique_states_packed(u_a, u_b)
    t_pack = time.perf_counter() - t_pack_start
    rss_pack, _ = get_process_memory_info()

    # Benchmark Strategy 2: Structured Array view + searchsorted
    t_struct_start = time.perf_counter()
    res_struct = intersect_unique_states_structured(u_a, u_b)
    t_struct = time.perf_counter() - t_struct_start
    rss_struct, _ = get_process_memory_info()

    print("  Intersection Strategy Benchmarks:")
    if res_pack is not None:
        print(
            f"    - Strategy 1 (Packed uint64):       {t_pack * 1000:.2f} ms | "
            f"Found {len(res_pack[0]):,} common states (RSS: {rss_pack:.1f} MB)"
        )
    else:
        print(
            f"    - Strategy 1 (Packed uint64):       N/A (dim={u_a.shape[1]}, range=[{u_a.min()}, {u_a.max()}])"
        )
    print(
        f"    - Strategy 2 (Structured view):      {t_struct * 1000:.2f} ms | "
        f"Found {len(res_struct[0]):,} common states (RSS: {rss_struct:.1f} MB)"
    )

    # 4. Full Common States & Heuristic Analysis
    print("\n[4/5] Computing common states analysis & diagnostics...")
    t4 = time.perf_counter()
    common_res = compute_common_states_analysis(
        data_a["coords"],
        data_a["h"],
        data_a["g"],
        data_a["f"],
        data_b["coords"],
        data_b["h"],
        data_b["g"],
        data_b["f"],
    )
    t_common = time.perf_counter() - t4
    print(f"  Computed common state analysis in {t_common:.4f}s")

    # 5. Pairwise Projections & Search Footprint
    print("\n[5/5] Computing pairwise 2D Footprint projections and Search Band metrics...")
    t5 = time.perf_counter()
    d_dims = max(data_a.get("dimensions", 3), data_b.get("dimensions", 3))
    all_fp = compute_all_pairwise_footprints(
        data_a["coords"], data_b["coords"], dimensions=d_dims, n_bins=FOOTPRINT_BINS
    )

    band_res = compute_band_comparison(
        prog_a, data_a["dev"], prog_b, data_b["dev"], n_bins=PROGRESS_BINS
    )
    t_fp_band = time.perf_counter() - t5
    print(
        f"  Computed {len(all_fp['pairs'])} pairwise projections & band deviation in {t_fp_band:.4f}s "
        f"(Mean Jaccard: {all_fp['mean_jaccard']:.4f})"
    )

    rss_final, peak_final = get_process_memory_info()

    # ─────────────────────────────────────────────
    #  PRINT COMPREHENSIVE REPORT
    # ─────────────────────────────────────────────
    print("\n" + "=" * 78)
    print(" COMPARISON ANALYSIS REPORT")
    print("=" * 78)

    # 1. Search Effort
    print("\n[SEARCH EFFORT]")
    print(f"  Expansion Count A:           {savings['expansions_a']:,}")
    print(f"  Expansion Count B:           {savings['expansions_b']:,}")
    print(f"  Total Nodes Saved (A - B):   {savings['total_nodes_saved']:,}")
    print(f"  Reduction (%):               {savings['total_reduction_pct']:.2f} %")

    # 2. Unique States & Inconsistencies
    print("\n[UNIQUE EXPANDED STATES & DEDUPLICATION]")
    print(f"  Unique States A:             {common_res['num_unique_a']:,}")
    print(f"  Unique States B:             {common_res['num_unique_b']:,}")
    print(f"  Common Unique States:        {common_res['num_common_unique']:,}")
    print(f"  Only in A:                   {common_res['num_only_a']:,}")
    print(f"  Only in B:                   {common_res['num_only_b']:,}")
    print(f"  Inconsistent h in A:         {common_res['inconsistent_h_a']}")
    print(f"  Inconsistent h in B:         {common_res['inconsistent_h_b']}")
    print(f"  Inconsistent g in A:         {common_res['inconsistent_g_a']:,}")
    print(f"  Inconsistent g in B:         {common_res['inconsistent_g_b']:,}")

    # 3. Heuristic Comparison on Common States
    print("\n[HEURISTIC DIFFERENCE ON VALID COMMON STATES (Δh = h_B - h_A)]")
    print(f"  Valid Common States for Δh:  {common_res['num_valid_h_common']:,}")
    if common_res["num_valid_h_common"] > 0:
        print(f"  Mean Δh:                     {common_res['mean_delta_h']:.3f}")
        print(f"  Median Δh:                   {common_res['median_delta_h']:.3f}")
        print(f"  Δh > 0 (h_B > h_A):          {common_res['pct_delta_h_pos']:.2f} %")
        print(f"  Δh = 0 (h_B == h_A):         {common_res['pct_delta_h_zero']:.2f} %")
        print(f"  Δh < 0 (h_B < h_A):          {common_res['pct_delta_h_neg']:.2f} %")
    else:
        print("  No valid common states for Δh calculation.")

    # 4. Path Cost & Log Consistency Diagnostics
    print("\n[DIAGNOSTICS]")
    print(f"  Valid Common States for g:   {common_res['num_valid_g_common']:,}")
    if common_res["num_valid_g_common"] > 0:
        print(
            f"  Common States with g_A == g_B: {common_res['num_g_match']:,} "
            f"({common_res['pct_g_match']:.2f} %)"
        )
        print(f"  Common States with g_A != g_B: {common_res['num_g_mismatch']:,}")
    else:
        print("  No common states with unambiguous g in both executions.")
    print(
        f"  Pre-dedup f == g + h (A):    {common_res['f_diag_a']['match_count']:,} / "
        f"{common_res['f_diag_a']['total_entries']:,} ({common_res['f_diag_a']['match_pct']:.2f} %)"
    )
    print(
        f"  Pre-dedup f == g + h (B):    {common_res['f_diag_b']['match_count']:,} / "
        f"{common_res['f_diag_b']['total_entries']:,} ({common_res['f_diag_b']['match_pct']:.2f} %)"
    )

    # 5. Pairwise Projections & Footprint Occupancy
    print(f"\n[SEARCH FOOTPRINT OCCUPANCY ({len(all_fp['pairs'])} PAIRWISE PROJECTIONS)]")
    print("  Projection Pair | Occupied A | Occupied B | Shared Cells | Only A | Only B | Jaccard")
    print("  ----------------+------------+------------+--------------+--------+--------+--------")
    for d0, d1 in all_fp["pairs"]:
        fp = all_fp["footprints"][(d0, d1)]
        pair_str = f"{get_pair_label(d0, d1, prefix='Seq '):15s}"
        print(
            f"  {pair_str} | {fp['n_occupied_a']:10,d} | {fp['n_occupied_b']:10,d} | "
            f"{fp['n_shared']:12,d} | {fp['n_only_a']:6,d} | {fp['n_only_b']:6,d} | {fp['jaccard']:.4f}"
        )
    print(f"  --> Mean Pairwise Jaccard Overlap: {all_fp['mean_jaccard']:.4f}")

    # 6. Search Band Deviation
    print("\n[SEARCH BAND DEVIATION]")
    print(f"  Mean Deviation A:            {band_res['mean_dev_a']:.2f}")
    print(f"  Mean Deviation B:            {band_res['mean_dev_b']:.2f}")
    print(f"  Median Deviation A:          {band_res['median_dev_a']:.2f}")
    print(f"  Median Deviation B:          {band_res['median_dev_b']:.2f}")

    # 7. Expansion Displacement
    print("\n[EXPANSION DISPLACEMENT (Manhattan Jump)]")
    mean_disp_a = (
        float(np.mean(data_a["jump_distances"])) if len(data_a["jump_distances"]) > 0 else 0.0
    )
    mean_disp_b = (
        float(np.mean(data_b["jump_distances"])) if len(data_b["jump_distances"]) > 0 else 0.0
    )
    disp_red = ((data_a["num_jumps"] - data_b["num_jumps"]) / max(data_a["num_jumps"], 1)) * 100.0
    print(f"  Displacements A:             {data_a['num_jumps']:,}")
    print(f"  Displacements B:             {data_b['num_jumps']:,}")
    print(f"  Displacement Reduction:      {disp_red:.2f} %")
    print(f"  Mean Displacement A:         {mean_disp_a:.2f}")
    print(f"  Mean Displacement B:         {mean_disp_b:.2f}")

    # 8. Memory & Performance Summary
    print("\n[RESOURCE & PERFORMANCE BENCHMARK]")
    total_time = t_parse_a + t_parse_b + t_savings + t_dedup + t_common + t_fp_band
    print(f"  Total Execution Time:        {total_time:.2f} s")
    print(f"  Process Peak RSS:            {peak_final:.1f} MB")
    print(f"  Process Final RSS:           {rss_final:.1f} MB")
    print("=" * 78)


if __name__ == "__main__":
    main()
