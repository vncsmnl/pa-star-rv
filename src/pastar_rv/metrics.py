"""
Pure NumPy Analysis and Metrics Module for PA-Star Runtime Visualizer.

Provides pure mathematical and statistical routines decoupled from PyQt/GUI:
- Geometric alignment progress calculation
- Binned statistics and percentile profiles
- Expansion savings and local reduction/ratio metrics with safe masked division
- 2D footprint occupancy, absolute difference, and relative density
- Pre-deduplication f(n) == g(n) + h(n) consistency check
- Coordinate deduplication and state consistency diagnostics for h(n) and g(n)
- Vectorized intersection of unique states between executions
- Search band deviation profiles
- Shared ComparisonCache with explicit invalidation
"""

import numpy as np

# ─────────────────────────────────────────────
#  CENTRAL CONFIGURATION CONSTANTS
# ─────────────────────────────────────────────

PROGRESS_BINS = 150
FOOTPRINT_BINS = 100
MAX_SCATTER_POINTS = 100_000
MIN_BIN_SUPPORT = 20


# ─────────────────────────────────────────────
#  GEOMETRIC ALIGNMENT PROGRESS
# ─────────────────────────────────────────────


def compute_geometric_alignment_progress(coords, reference_coords=None):
    """
    Computes normalized geometric alignment progress for D-dimensional coordinates:
        progress(s) = (1 / D) * sum_{d=0}^{D-1} (coords[:, d] / reference_coords[d])

    NOTE: This is a geometric projection of the state in alignment space, NOT
    execution time progress, A* depth, or position in the OPEN list.

    If reference_coords is None, reference_coords is inferred as coords.max(axis=0).
    For dimensions where reference_coords is 0, the divisor is treated as 1 so
    zero coordinates evaluate to 0 without division by zero errors.

    Parameters:
        coords: (N, D) integer or float array of coordinates.
        reference_coords: (D,) array of reference maximum coordinates.

    Returns:
        progress: (N,) float64 array in range [0.0, 1.0].
    """
    if coords is None or len(coords) == 0:
        return np.array([], dtype=np.float64)

    coords_arr = np.asarray(coords, dtype=np.float64)
    if coords_arr.ndim == 1:
        coords_arr = coords_arr.reshape(-1, 1)

    n_nodes, d_dims = coords_arr.shape
    if d_dims == 0:
        return np.zeros(n_nodes, dtype=np.float64)

    if reference_coords is None:
        ref = np.max(coords_arr, axis=0)
    else:
        ref = np.asarray(reference_coords, dtype=np.float64)

    safe_ref = np.where(ref > 0, ref, 1.0)
    norm_coords = coords_arr / safe_ref
    progress = np.mean(norm_coords, axis=1)
    return np.clip(progress, 0.0, 1.0)


# ─────────────────────────────────────────────
#  BINNED PERCENTILES & PROFILES
# ─────────────────────────────────────────────


def compute_binned_percentiles(
    progress,
    values,
    n_bins=PROGRESS_BINS,
    percentiles=(25, 50, 75, 90),
    bin_range=(0.0, 1.0),
):
    """
    Computes percentiles and summary statistics of `values` across bins of `progress`.
    Uses a Python loop over the small fixed number of bins with vectorized NumPy
    slicing/sorting, avoiding huge temporary 2D matrices and high memory usage.

    Parameters:
        progress: (N,) float array of geometric alignment progress values.
        values: (N,) numeric array of values to profile (e.g., h, g, f, or dev).
        n_bins: int, number of bins across bin_range.
        percentiles: tuple of floats/ints, percentiles to compute.
        bin_range: tuple (min_val, max_val).

    Returns:
        dict with:
            - 'bin_edges': (n_bins + 1,) float64
            - 'bin_centers': (n_bins,) float64
            - 'counts': (n_bins,) int64
            - 'percentiles': dict {p: (n_bins,) float64 with np.nan for empty bins}
            - 'median': (n_bins,) float64 with np.nan for empty bins
            - 'mean': (n_bins,) float64 with np.nan for empty bins
    """
    bin_edges = np.linspace(bin_range[0], bin_range[1], n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    counts = np.zeros(n_bins, dtype=np.int64)
    means = np.full(n_bins, np.nan, dtype=np.float64)
    medians = np.full(n_bins, np.nan, dtype=np.float64)
    pct_dict = {p: np.full(n_bins, np.nan, dtype=np.float64) for p in percentiles}

    if progress is None or values is None or len(progress) == 0 or len(values) == 0:
        return {
            "bin_edges": bin_edges,
            "bin_centers": bin_centers,
            "counts": counts,
            "percentiles": pct_dict,
            "median": medians,
            "mean": means,
        }

    p_arr = np.asarray(progress, dtype=np.float64)
    v_arr = np.asarray(values, dtype=np.float64)

    # Bin indices: 0 is out of bounds left, n_bins+1 is right, 1..n_bins are valid
    bin_indices = np.digitize(p_arr, bin_edges)

    for b in range(1, n_bins + 1):
        idx = b - 1
        # Include right edge in last bin
        mask = (bin_indices == b) | (p_arr == bin_edges[-1]) if b == n_bins else (bin_indices == b)

        bin_vals = v_arr[mask]
        n_in_bin = len(bin_vals)
        counts[idx] = n_in_bin

        if n_in_bin > 0:
            means[idx] = np.mean(bin_vals)
            medians[idx] = np.median(bin_vals)
            for p in percentiles:
                pct_dict[p][idx] = np.percentile(bin_vals, p)

    return {
        "bin_edges": bin_edges,
        "bin_centers": bin_centers,
        "counts": counts,
        "percentiles": pct_dict,
        "median": medians,
        "mean": means,
    }


# ─────────────────────────────────────────────
#  EXPANSION SAVINGS & SEARCH DIFFERENCE
# ─────────────────────────────────────────────


def compute_expansion_savings(
    progress_a,
    progress_b,
    n_bins=PROGRESS_BINS,
    min_support=MIN_BIN_SUPPORT,
    bin_range=(0.0, 1.0),
):
    """
    Computes cumulative and local expansion differences between A and B over
    geometric alignment progress.

    NOTE: Cumulative Expansion Difference by Geometric Progress does NOT represent
    cumulative savings over execution time. It represents the cumulative expansion
    difference up to a given geometric region in alignment space.

    Convention:
        saved > 0  => B expanded fewer nodes than A
        saved == 0 => equal number of expansions
        saved < 0  => B expanded more nodes than A

    Safe division with np.divide is used so that unmasked / low-support bins
    evaluate to np.nan without divide-by-zero warnings.
    """
    bin_edges = np.linspace(bin_range[0], bin_range[1], n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    p_a = (
        np.asarray(progress_a, dtype=np.float64)
        if progress_a is not None
        else np.array([], dtype=np.float64)
    )
    p_b = (
        np.asarray(progress_b, dtype=np.float64)
        if progress_b is not None
        else np.array([], dtype=np.float64)
    )

    nA = len(p_a)
    nB = len(p_b)

    local_a, _ = np.histogram(p_a, bins=bin_edges)
    local_b, _ = np.histogram(p_b, bins=bin_edges)

    cum_a = np.cumsum(local_a)
    cum_b = np.cumsum(local_b)

    # Cumulative Expansion Difference by Geometric Progress
    cum_diff = cum_a - cum_b
    local_saved = local_a - local_b

    # Safe division for local reduction and ratio based on min_support in baseline A
    valid_mask = local_a >= min_support

    local_reduction = np.full(n_bins, np.nan, dtype=np.float64)
    np.divide(
        (local_a - local_b).astype(np.float64),
        local_a.astype(np.float64),
        out=local_reduction,
        where=valid_mask,
    )
    local_reduction = local_reduction * 100.0  # percentage

    local_ratio = np.full(n_bins, np.nan, dtype=np.float64)
    np.divide(
        local_b.astype(np.float64),
        local_a.astype(np.float64),
        out=local_ratio,
        where=valid_mask,
    )

    total_saved = nA - nB
    reduction_pct = ((nA - nB) / nA * 100.0) if nA > 0 else 0.0

    return {
        "bin_edges": bin_edges,
        "bin_centers": bin_centers,
        "expansions_a": nA,
        "expansions_b": nB,
        "total_nodes_saved": total_saved,
        "total_reduction_pct": reduction_pct,
        "local_a": local_a,
        "local_b": local_b,
        "cum_a": cum_a,
        "cum_b": cum_b,
        "cum_diff": cum_diff,
        "local_saved": local_saved,
        "local_reduction": local_reduction,
        "local_ratio": local_ratio,
        "valid_support_mask": valid_mask,
    }


# ─────────────────────────────────────────────
#  SEARCH FOOTPRINT (2D PROJECTIONS & OCCUPANCY)
# ─────────────────────────────────────────────


def compute_footprint_data(coords_a, coords_b, proj_dims=(0, 1), n_bins=FOOTPRINT_BINS):
    """
    Computes 2D footprint occupancy, absolute expansion difference, and relative
    exploration density for a given projection pair of dimensions (e.g., XY, XZ, YZ).

    NOTE: 2D footprint is a projection of D-dimensional space. Multiple distinct
    states may project into the same 2D histogram bin.
    """
    cA = (
        np.asarray(coords_a, dtype=np.int32)
        if coords_a is not None
        else np.empty((0, 2), dtype=np.int32)
    )
    cB = (
        np.asarray(coords_b, dtype=np.int32)
        if coords_b is not None
        else np.empty((0, 2), dtype=np.int32)
    )

    d0, d1 = proj_dims

    x_a = cA[:, d0] if len(cA) > 0 and cA.shape[1] > d0 else np.zeros(0, dtype=np.int32)
    y_a = cA[:, d1] if len(cA) > 0 and cA.shape[1] > d1 else np.zeros(0, dtype=np.int32)

    x_b = cB[:, d0] if len(cB) > 0 and cB.shape[1] > d0 else np.zeros(0, dtype=np.int32)
    y_b = cB[:, d1] if len(cB) > 0 and cB.shape[1] > d1 else np.zeros(0, dtype=np.int32)

    all_x = (
        np.concatenate([x_a, x_b]) if len(x_a) + len(x_b) > 0 else np.array([0, 1], dtype=np.int32)
    )
    all_y = (
        np.concatenate([y_a, y_b]) if len(y_a) + len(y_b) > 0 else np.array([0, 1], dtype=np.int32)
    )

    min_x, max_x = int(all_x.min()), int(all_x.max())
    min_y, max_y = int(all_y.min()), int(all_y.max())

    if min_x == max_x:
        max_x = min_x + 1
    if min_y == max_y:
        max_y = min_y + 1

    rng = [[min_x, max_x], [min_y, max_y]]

    HA, xe, ye = (
        np.histogram2d(x_a, y_a, bins=n_bins, range=rng)
        if len(x_a) > 0
        else (
            np.zeros((n_bins, n_bins)),
            np.linspace(min_x, max_x, n_bins + 1),
            np.linspace(min_y, max_y, n_bins + 1),
        )
    )
    HB, _, _ = (
        np.histogram2d(x_b, y_b, bins=n_bins, range=rng)
        if len(x_b) > 0
        else (np.zeros((n_bins, n_bins)), xe, ye)
    )

    # 1. Absolute Difference: HB - HA
    diff_abs = HB - HA

    # 2. Relative Density Difference: (HB / sum(HB)) - (HA / sum(HA))
    sum_a = HA.sum()
    sum_b = HB.sum()
    ha_norm = HA / max(sum_a, 1.0)
    hb_norm = HB / max(sum_b, 1.0)
    diff_rel = hb_norm - ha_norm

    # 3. Occupied Cell Metrics
    occupied_a = HA > 0
    occupied_b = HB > 0
    shared = occupied_a & occupied_b
    only_a = occupied_a & ~occupied_b
    only_b = occupied_b & ~occupied_a
    union = occupied_a | occupied_b

    n_occ_a = int(np.sum(occupied_a))
    n_occ_b = int(np.sum(occupied_b))
    n_shared = int(np.sum(shared))
    n_only_a = int(np.sum(only_a))
    n_only_b = int(np.sum(only_b))
    n_union = int(np.sum(union))

    jaccard = (n_shared / max(n_union, 1)) if n_union > 0 else 0.0

    return {
        "HA": HA,
        "HB": HB,
        "x_edges": xe,
        "y_edges": ye,
        "diff_abs": diff_abs,
        "diff_rel": diff_rel,
        "ha_norm": ha_norm,
        "hb_norm": hb_norm,
        "occupied_a": occupied_a,
        "occupied_b": occupied_b,
        "shared": shared,
        "only_a": only_a,
        "only_b": only_b,
        "n_occupied_a": n_occ_a,
        "n_occupied_b": n_occ_b,
        "n_shared": n_shared,
        "n_only_a": n_only_a,
        "n_only_b": n_only_b,
        "jaccard": jaccard,
        "extent": (xe[0], xe[-1], ye[0], ye[-1]),
    }


def get_projection_pairs(d_dims):
    """
    Returns list of all 2D projection dimension index pairs (d0, d1) for 0 <= d0 < d1 < d_dims.
    For D=3: [(0, 1), (0, 2), (1, 2)]
    For D=6: 15 pairs [(0, 1), (0, 2), ..., (4, 5)]
    """
    if d_dims < 2:
        return []
    return [(i, j) for i in range(d_dims) for j in range(i + 1, d_dims)]


def get_pair_label(d0, d1, prefix="Seq "):
    """
    Returns human-friendly label for a dimension pair, e.g. 'Seq 1 vs Seq 2' or 'S1 vs S2'.
    """
    return f"{prefix}{d0 + 1} vs {prefix}{d1 + 1}"


def compute_all_pairwise_footprints(coords_a, coords_b, dimensions=None, n_bins=FOOTPRINT_BINS):
    """
    Computes 2D footprint occupancy, absolute expansion difference, and relative
    exploration density for ALL (D choose 2) dimension pairs.

    Parameters:
        coords_a: (N_A, D) int32 array
        coords_b: (N_B, D) int32 array
        dimensions: int or None (inferred from coords shape if None, minimum 2)
        n_bins: int

    Returns:
        dict with:
            - 'dimensions': int
            - 'pairs': list of (d0, d1)
            - 'footprints': dict mapping (d0, d1) -> footprint dict from compute_footprint_data
            - 'mean_jaccard': float
    """
    cA = np.asarray(coords_a, dtype=np.int32) if coords_a is not None else np.empty((0, 2), dtype=np.int32)
    cB = np.asarray(coords_b, dtype=np.int32) if coords_b is not None else np.empty((0, 2), dtype=np.int32)

    if dimensions is None:
        dim_a = cA.shape[1] if cA.ndim > 1 and cA.shape[0] > 0 else 0
        dim_b = cB.shape[1] if cB.ndim > 1 and cB.shape[0] > 0 else 0
        d_dims = max(dim_a, dim_b, 2)
    else:
        d_dims = max(int(dimensions), 2)

    pairs = get_projection_pairs(d_dims)
    footprints = {}
    jaccards = []

    for d0, d1 in pairs:
        fp = compute_footprint_data(cA, cB, proj_dims=(d0, d1), n_bins=n_bins)
        footprints[(d0, d1)] = fp
        jaccards.append(fp["jaccard"])

    mean_jaccard = float(np.mean(jaccards)) if jaccards else 0.0

    return {
        "dimensions": d_dims,
        "pairs": pairs,
        "footprints": footprints,
        "mean_jaccard": mean_jaccard,
    }


# ─────────────────────────────────────────────
#  PRE-DEDUPLICATION CONSISTENCY CHECK
# ─────────────────────────────────────────────


def check_f_consistency(g, h, f):
    """
    Checks the relation f == g + h directly on the raw log entries prior to deduplication.
    Returns:
        dict with match count, mismatch count, total, and match percentage.
    """
    if g is None or h is None or f is None or len(f) == 0:
        return {
            "total_entries": 0,
            "match_count": 0,
            "mismatch_count": 0,
            "match_pct": 100.0,
        }

    g_arr = np.asarray(g, dtype=np.int64)
    h_arr = np.asarray(h, dtype=np.int64)
    f_arr = np.asarray(f, dtype=np.int64)

    expected = g_arr + h_arr
    matches = f_arr == expected
    match_cnt = int(np.sum(matches))
    total = len(f_arr)
    mismatch_cnt = total - match_cnt
    pct = (match_cnt / max(total, 1)) * 100.0

    return {
        "total_entries": total,
        "match_count": match_cnt,
        "mismatch_count": mismatch_cnt,
        "match_pct": pct,
    }


# ─────────────────────────────────────────────
#  DEDUPLICATION & STATE CONSISTENCY DIAGNOSTICS
# ─────────────────────────────────────────────


def deduplicate_and_diagnose_states(coords, h, g):
    """
    Deduplicates coordinates and verifies whether h(s) and g(s) are unambiguous
    (consistent) across all duplicate occurrences of the same coordinate within an execution.

    Parameters:
        coords: (N, D) int32 array of coordinates
        h: (N,) int32 array of heuristic values
        g: (N,) int32 array of path costs

    Returns:
        dict with:
            - 'unique_coords': (U, D) int32 array of distinct coordinates
            - 'unique_h': (U,) int32 array of h values (for consistent states)
            - 'unique_g': (U,) int32 array of g values (for consistent states)
            - 'h_is_consistent': (U,) bool array
            - 'g_is_consistent': (U,) bool array
            - 'num_total_entries': int
            - 'num_unique_states': int
            - 'inconsistent_h_count': int
            - 'inconsistent_g_count': int
    """
    if coords is None or len(coords) == 0:
        d = coords.shape[1] if (coords is not None and hasattr(coords, "shape") and coords.ndim > 1) else 0
        return {
            "unique_coords": np.empty((0, d), dtype=np.int32),
            "unique_h": np.empty(0, dtype=np.int32),
            "unique_g": np.empty(0, dtype=np.int32),
            "h_is_consistent": np.empty(0, dtype=bool),
            "g_is_consistent": np.empty(0, dtype=bool),
            "num_total_entries": 0,
            "num_unique_states": 0,
            "inconsistent_h_count": 0,
            "inconsistent_g_count": 0,
        }

    coords_arr = np.asarray(coords, dtype=np.int32)
    h_arr = np.asarray(h, dtype=np.int32)
    g_arr = np.asarray(g, dtype=np.int32)
    n_entries = len(coords_arr)

    # Lexicographical sort order of coordinates
    # np.lexsort takes keys in reverse order (last column first)
    sort_order = np.lexsort(coords_arr.T[::-1])
    s_coords = coords_arr[sort_order]
    s_h = h_arr[sort_order]
    s_g = g_arr[sort_order]

    # Coordinate boundary detection
    if n_entries > 1:
        diff_mask = np.any(s_coords[:-1] != s_coords[1:], axis=1)
        group_starts = np.concatenate(([0], np.where(diff_mask)[0] + 1))
        # Unique coordinate group ID for every sorted element
        group_ids = np.cumsum(np.concatenate(([0], diff_mask)))
    else:
        diff_mask = np.array([], dtype=bool)
        group_starts = np.array([0], dtype=np.int64)
        group_ids = np.array([0], dtype=np.int64)

    num_unique = len(group_starts)
    unique_coords = s_coords[group_starts]
    unique_h = s_h[group_starts]
    unique_g = s_g[group_starts]

    h_is_consistent = np.ones(num_unique, dtype=bool)
    g_is_consistent = np.ones(num_unique, dtype=bool)

    if n_entries > 1:
        # Detect any adjacent pair having the SAME coordinate (~diff_mask) but DIFFERENT h or g
        same_coord_mask = ~diff_mask
        within_group_h_diff = (s_h[:-1] != s_h[1:]) & same_coord_mask
        within_group_g_diff = (s_g[:-1] != s_g[1:]) & same_coord_mask

        if np.any(within_group_h_diff):
            inconsistent_h_ids = np.unique(group_ids[:-1][within_group_h_diff])
            h_is_consistent[inconsistent_h_ids] = False

        if np.any(within_group_g_diff):
            inconsistent_g_ids = np.unique(group_ids[:-1][within_group_g_diff])
            g_is_consistent[inconsistent_g_ids] = False

    return {
        "unique_coords": unique_coords,
        "unique_h": unique_h,
        "unique_g": unique_g,
        "h_is_consistent": h_is_consistent,
        "g_is_consistent": g_is_consistent,
        "num_total_entries": n_entries,
        "num_unique_states": num_unique,
        "inconsistent_h_count": int(np.sum(~h_is_consistent)),
        "inconsistent_g_count": int(np.sum(~g_is_consistent)),
    }


# ─────────────────────────────────────────────
#  COMMON STATES INTERSECTION STRATEGIES
# ─────────────────────────────────────────────


def pack_coords_uint64(coords):
    """
    Packs 3D integer coordinates (up to 20 bits each: 0..1,048,575) into uint64 keys.
    Returns: (N,) uint64 array or None if dimensions > 3 or coordinate out of range.
    """
    c = np.asarray(coords, dtype=np.int64)
    if c.shape[1] != 3:
        return None
    if np.any(c < 0) or np.any(c >= (1 << 20)):
        return None
    return (c[:, 0] << 40) | (c[:, 1] << 20) | c[:, 2]


def intersect_unique_states_packed(u_coords_a, u_coords_b):
    """
    Intersects unique coordinates using packed 64-bit integer keys.
    Returns (idx_a, idx_b) of matching entries.
    """
    keys_a = pack_coords_uint64(u_coords_a)
    keys_b = pack_coords_uint64(u_coords_b)
    if keys_a is None or keys_b is None:
        return None

    # Both arrays are already sorted lexicographically from deduplicate_and_diagnose_states!
    idx_b_cand = np.searchsorted(keys_b, keys_a)
    idx_b_cand = np.clip(idx_b_cand, 0, len(keys_b) - 1)
    match_mask = keys_b[idx_b_cand] == keys_a

    idx_a = np.where(match_mask)[0]
    idx_b = idx_b_cand[match_mask]
    return idx_a, idx_b


def intersect_unique_states_structured(u_coords_a, u_coords_b):
    """
    Intersects unique coordinates using NumPy structured array view and np.searchsorted.
    Returns (idx_a, idx_b) of matching entries.
    """
    d = u_coords_a.shape[1]
    dtype = np.dtype([("f", u_coords_a.dtype, d)])
    view_a = np.ascontiguousarray(u_coords_a).view(dtype).ravel()
    view_b = np.ascontiguousarray(u_coords_b).view(dtype).ravel()

    idx_b_cand = np.searchsorted(view_b, view_a)
    idx_b_cand = np.clip(idx_b_cand, 0, len(view_b) - 1)
    match_mask = view_b[idx_b_cand] == view_a

    idx_a = np.where(match_mask)[0]
    idx_b = idx_b_cand[match_mask]
    return idx_a, idx_b


def intersect_unique_states_lexsort(u_coords_a, u_coords_b):
    """
    Intersects unique coordinates using multi-column searchsorted.
    Returns (idx_a, idx_b) of matching entries.
    """
    return intersect_unique_states_structured(u_coords_a, u_coords_b)


def intersect_unique_states(u_coords_a, u_coords_b, strategy="auto"):
    """
    Intersects unique coordinates of A and B using the most appropriate strategy.
    Strategies: 'packed', 'structured', 'lexsort', or 'auto'.
    """
    if len(u_coords_a) == 0 or len(u_coords_b) == 0:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)

    if strategy in ("packed", "auto"):
        res = intersect_unique_states_packed(u_coords_a, u_coords_b)
        if res is not None:
            return res

    return intersect_unique_states_structured(u_coords_a, u_coords_b)


# ─────────────────────────────────────────────
#  COMMON STATES ANALYSIS
# ─────────────────────────────────────────────


def compute_common_states_analysis(
    coords_a,
    h_a,
    g_a,
    f_a,
    coords_b,
    h_b,
    g_b,
    f_b,
    max_scatter_points=MAX_SCATTER_POINTS,
):
    """
    Complete analysis of common expanded states between A and B with diagnostics:
    - Pre-deduplication f(n) == g(n) + h(n) consistency check for A and B.
    - State deduplication with h and g consistency checks.
    - Vectorized coordinate intersection.
    - Strict exclusion of inconsistent h states in Δh = h_B(s) - h_A(s).
    - Path cost diagnostic: g_A == g_B vs g_A != g_B on unambiguous g states.
    - Safe downsampling strictly for visual scatter rendering.
    """
    # 1. Pre-deduplication f consistency
    f_diag_a = check_f_consistency(g_a, h_a, f_a)
    f_diag_b = check_f_consistency(g_b, h_b, f_b)

    # 2. State deduplication and consistency diagnostics
    dedup_a = deduplicate_and_diagnose_states(coords_a, h_a, g_a)
    dedup_b = deduplicate_and_diagnose_states(coords_b, h_b, g_b)

    u_coords_a = dedup_a["unique_coords"]
    u_coords_b = dedup_b["unique_coords"]

    # 3. Vectorized intersection of unique coordinates
    idx_a_common, idx_b_common = intersect_unique_states(u_coords_a, u_coords_b)

    n_unique_a = dedup_a["num_unique_states"]
    n_unique_b = dedup_b["num_unique_states"]
    n_common_unique = len(idx_a_common)
    n_only_a = n_unique_a - n_common_unique
    n_only_b = n_unique_b - n_common_unique

    # 4. Filter for valid (consistent) h states
    h_valid_a = dedup_a["h_is_consistent"][idx_a_common]
    h_valid_b = dedup_b["h_is_consistent"][idx_b_common]
    valid_h_mask = h_valid_a & h_valid_b

    idx_a_valid_h = idx_a_common[valid_h_mask]
    idx_b_valid_h = idx_b_common[valid_h_mask]
    n_valid_h_common = len(idx_a_valid_h)

    h_a_common_valid = dedup_a["unique_h"][idx_a_valid_h]
    h_b_common_valid = dedup_b["unique_h"][idx_b_valid_h]

    # Δh = h_B(s) - h_A(s) on valid common states
    delta_h = h_b_common_valid.astype(np.float64) - h_a_common_valid.astype(np.float64)

    if n_valid_h_common > 0:
        mean_delta_h = float(np.mean(delta_h))
        median_delta_h = float(np.median(delta_h))
        pct_pos = float(np.mean(delta_h > 0) * 100.0)
        pct_zero = float(np.mean(delta_h == 0) * 100.0)
        pct_neg = float(np.mean(delta_h < 0) * 100.0)
    else:
        mean_delta_h = np.nan
        median_delta_h = np.nan
        pct_pos = np.nan
        pct_zero = np.nan
        pct_neg = np.nan

    # 5. Filter for valid (consistent) g states and diagnostic check g_A == g_B
    g_valid_a = dedup_a["g_is_consistent"][idx_a_common]
    g_valid_b = dedup_b["g_is_consistent"][idx_b_common]
    valid_g_mask = g_valid_a & g_valid_b

    idx_a_valid_g = idx_a_common[valid_g_mask]
    idx_b_valid_g = idx_b_common[valid_g_mask]
    n_valid_g_common = len(idx_a_valid_g)

    if n_valid_g_common > 0:
        g_a_common_valid = dedup_a["unique_g"][idx_a_valid_g]
        g_b_common_valid = dedup_b["unique_g"][idx_b_valid_g]
        g_matches = g_a_common_valid == g_b_common_valid
        n_g_match = int(np.sum(g_matches))
        n_g_mismatch = n_valid_g_common - n_g_match
        pct_g_match = (n_g_match / n_valid_g_common) * 100.0
    else:
        n_g_match = 0
        n_g_mismatch = 0
        pct_g_match = np.nan

    # 6. Scatter render data downsampling (STRICTLY for display; stats use complete arrays)
    if n_valid_h_common > max_scatter_points:
        step = max(1, n_valid_h_common // max_scatter_points)
        scatter_ha = h_a_common_valid[::step]
        scatter_hb = h_b_common_valid[::step]
    else:
        scatter_ha = h_a_common_valid
        scatter_hb = h_b_common_valid

    return {
        "num_unique_a": n_unique_a,
        "num_unique_b": n_unique_b,
        "num_common_unique": n_common_unique,
        "num_only_a": n_only_a,
        "num_only_b": n_only_b,
        "inconsistent_h_a": dedup_a["inconsistent_h_count"],
        "inconsistent_h_b": dedup_b["inconsistent_h_count"],
        "inconsistent_g_a": dedup_a["inconsistent_g_count"],
        "inconsistent_g_b": dedup_b["inconsistent_g_count"],
        "num_valid_h_common": n_valid_h_common,
        "delta_h": delta_h,
        "mean_delta_h": mean_delta_h,
        "median_delta_h": median_delta_h,
        "pct_delta_h_pos": pct_pos,
        "pct_delta_h_zero": pct_zero,
        "pct_delta_h_neg": pct_neg,
        "num_valid_g_common": n_valid_g_common,
        "num_g_match": n_g_match,
        "num_g_mismatch": n_g_mismatch,
        "pct_g_match": pct_g_match,
        "f_diag_a": f_diag_a,
        "f_diag_b": f_diag_b,
        "scatter_ha": scatter_ha,
        "scatter_hb": scatter_hb,
    }


# ─────────────────────────────────────────────
#  SEARCH BAND COMPARISON
# ─────────────────────────────────────────────


def compute_band_comparison(progress_a, dev_a, progress_b, dev_b, n_bins=PROGRESS_BINS):
    """
    Computes comparative band deviation profiles over geometric alignment progress,
    and global deviation distributions (both absolute count and normalized density).
    """
    profile_a = compute_binned_percentiles(
        progress_a, dev_a, n_bins=n_bins, percentiles=(25, 50, 75, 90)
    )
    profile_b = compute_binned_percentiles(
        progress_b, dev_b, n_bins=n_bins, percentiles=(25, 50, 75, 90)
    )

    dev_arr_a = np.asarray(dev_a, dtype=np.float64) if dev_a is not None else np.array([])
    dev_arr_b = np.asarray(dev_b, dtype=np.float64) if dev_b is not None else np.array([])

    max_dev = max(
        dev_arr_a.max() if len(dev_arr_a) > 0 else 1.0,
        dev_arr_b.max() if len(dev_arr_b) > 0 else 1.0,
    )
    hist_bins = np.linspace(0.0, max_dev, 60)

    count_a, _ = (
        np.histogram(dev_arr_a, bins=hist_bins) if len(dev_arr_a) > 0 else (np.zeros(59), hist_bins)
    )
    count_b, _ = (
        np.histogram(dev_arr_b, bins=hist_bins) if len(dev_arr_b) > 0 else (np.zeros(59), hist_bins)
    )

    density_a = count_a / max(count_a.sum(), 1.0)
    density_b = count_b / max(count_b.sum(), 1.0)

    mean_dev_a = float(np.mean(dev_arr_a)) if len(dev_arr_a) > 0 else np.nan
    mean_dev_b = float(np.mean(dev_arr_b)) if len(dev_arr_b) > 0 else np.nan
    median_dev_a = float(np.median(dev_arr_a)) if len(dev_arr_a) > 0 else np.nan
    median_dev_b = float(np.median(dev_arr_b)) if len(dev_arr_b) > 0 else np.nan

    return {
        "profile_a": profile_a,
        "profile_b": profile_b,
        "hist_bins": hist_bins,
        "count_a": count_a,
        "count_b": count_b,
        "density_a": density_a,
        "density_b": density_b,
        "mean_dev_a": mean_dev_a,
        "mean_dev_b": mean_dev_b,
        "median_dev_a": median_dev_a,
        "median_dev_b": median_dev_b,
    }


# ─────────────────────────────────────────────
#  COMPARISON CACHE WITH EXPLICIT INVALIDATION
# ─────────────────────────────────────────────


class ComparisonCache:
    """
    Shared in-memory cache for full comparison metrics between dataset pairs.
    Explicitly cleared whenever a dataset is loaded or replaced to prevent
    holding onto stale arrays and references in memory.
    """

    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value

    def clear(self):
        self._store.clear()

    def __len__(self):
        return len(self._store)


# Global comparison cache instance
comparison_cache = ComparisonCache()
