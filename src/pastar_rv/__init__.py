"""
PA-Star Runtime Visualizer (`pastar_rv`).
High-Performance Runtime Visualizer and Analytics for PA-Star Multiple Sequence Alignment.
"""

from pastar_rv.metrics import (
    FOOTPRINT_BINS,
    MAX_SCATTER_POINTS,
    MIN_BIN_SUPPORT,
    PROGRESS_BINS,
    ComparisonCache,
    check_f_consistency,
    comparison_cache,
    compute_band_comparison,
    compute_binned_percentiles,
    compute_common_states_analysis,
    compute_expansion_savings,
    compute_footprint_data,
    compute_geometric_alignment_progress,
    deduplicate_and_diagnose_states,
    intersect_unique_states,
)
from pastar_rv.parser import parse_log_file

__version__ = "0.2.0"
__all__ = [
    "FOOTPRINT_BINS",
    "MAX_SCATTER_POINTS",
    "MIN_BIN_SUPPORT",
    "PROGRESS_BINS",
    "ComparisonCache",
    "check_f_consistency",
    "comparison_cache",
    "compute_band_comparison",
    "compute_binned_percentiles",
    "compute_common_states_analysis",
    "compute_expansion_savings",
    "compute_footprint_data",
    "compute_geometric_alignment_progress",
    "deduplicate_and_diagnose_states",
    "intersect_unique_states",
    "parse_log_file",
]
