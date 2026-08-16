"""
Summary Comparison Dashboard Widget (CanvasSummary)
Clean executive summary with dedicated cards and structured tables for all key metrics.
"""

import numpy as np

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont
    from PyQt5.QtWidgets import (
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QScrollArea,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
    )

from pastar_rv.metrics import (
    FOOTPRINT_BINS,
    MIN_BIN_SUPPORT,
    PROGRESS_BINS,
    compute_band_comparison,
    compute_common_states_analysis,
    compute_expansion_savings,
    compute_footprint_data,
    compute_geometric_alignment_progress,
)


class CanvasSummary(QWidget):
    """
    First tab dual-file summary dashboard.
    Renders clean, structured metrics tables and KPI cards without mixing
    incompatible units on the same graphical axis.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_key = None
        self._cache = {}
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(12)

        # ── 1. Top KPI Row (Search Effort Cards) ──
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet(
            "QFrame { background: #f8f9fa; border: 1px solid #cbd5e1; border-radius: 8px; }"
        )
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 12, 16, 12)
        kpi_layout.setSpacing(24)

        def make_kpi(title, subtitle="—", color="#1e293b"):
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl_t = QLabel(title)
            lbl_t.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_t.setStyleSheet("color: #64748b; text-transform: uppercase;")
            lbl_v = QLabel("—")
            lbl_v.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            lbl_v.setStyleSheet(f"color: {color};")
            lbl_sub = QLabel(subtitle)
            lbl_sub.setFont(QFont("Segoe UI", 8))
            lbl_sub.setStyleSheet("color: #94a3b8;")
            col.addWidget(lbl_t)
            col.addWidget(lbl_v)
            col.addWidget(lbl_sub)
            kpi_layout.addLayout(col)
            return lbl_v, lbl_sub

        self.kpi_nodes_a, self.kpi_sub_a = make_kpi(
            "Baseline (A) Expansions", "Total log records", "#1f77b4"
        )
        self.kpi_nodes_b, self.kpi_sub_b = make_kpi(
            "Candidate (B) Expansions", "Total log records", "#d62728"
        )
        self.kpi_saved, self.kpi_sub_saved = make_kpi(
            "Total Expansions Saved", "N_A − N_B", "#2563eb"
        )
        self.kpi_red, self.kpi_sub_red = make_kpi(
            "Expansion Reduction", "% saved by Candidate", "#16a34a"
        )
        self.kpi_common, self.kpi_sub_common = make_kpi(
            "Common Unique States", "Geometric intersection", "#7c3aed"
        )
        kpi_layout.addStretch()

        main_layout.addWidget(kpi_frame)

        # ── 2. Two-Column Dashboard Grid ──
        grid = QGridLayout()
        grid.setSpacing(12)

        def make_group(title):
            gb = QGroupBox(title)
            gb.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            gb.setStyleSheet(
                "QGroupBox { font-weight: bold; border: 1px solid #cbd5e1; border-radius: 6px; "
                "margin-top: 8px; padding-top: 10px; background: white; } "
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #1e293b; }"
            )
            return gb

        # Group 1: Search Effort
        gb_effort = make_group("1. Search Effort & Expansion Displacement")
        layout_effort = QVBoxLayout(gb_effort)
        self.table_effort = QTableWidget()
        self.table_effort.setColumnCount(4)
        self.table_effort.setHorizontalHeaderLabels(
            ["Metric", "Dataset A", "Dataset B", "Difference / Reduction"]
        )
        self.table_effort.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_effort.setFont(QFont("Segoe UI", 9))
        self.table_effort.setFixedHeight(170)
        layout_effort.addWidget(self.table_effort)
        grid.addWidget(gb_effort, 0, 0)

        # Group 2: Unique States & Deduplication
        gb_states = make_group("2. Unique Expanded States & Deduplication")
        layout_states = QVBoxLayout(gb_states)
        self.table_states = QTableWidget()
        self.table_states.setColumnCount(3)
        self.table_states.setHorizontalHeaderLabels(
            ["Metric / Category", "Count / Value", "Notes & Consistency"]
        )
        self.table_states.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_states.setFont(QFont("Segoe UI", 9))
        self.table_states.setFixedHeight(170)
        layout_states.addWidget(self.table_states)
        grid.addWidget(gb_states, 0, 1)

        # Group 3: Heuristic Advantage
        gb_heur = make_group("3. Heuristic Comparison on Valid Common States (Δh = h_B − h_A)")
        layout_heur = QVBoxLayout(gb_heur)
        self.table_heur = QTableWidget()
        self.table_heur.setColumnCount(3)
        self.table_heur.setHorizontalHeaderLabels(["Statistic", "Value", "Interpretation"])
        self.table_heur.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_heur.setFont(QFont("Segoe UI", 9))
        self.table_heur.setFixedHeight(170)
        layout_heur.addWidget(self.table_heur)
        grid.addWidget(gb_heur, 1, 0)

        # Group 4: Path Cost & Log Diagnostics
        gb_diag = make_group("4. Path Cost & Log Consistency Diagnostics")
        layout_diag = QVBoxLayout(gb_diag)
        self.table_diag = QTableWidget()
        self.table_diag.setColumnCount(3)
        self.table_diag.setHorizontalHeaderLabels(["Diagnostic Check", "Result", "Evaluation"])
        self.table_diag.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_diag.setFont(QFont("Segoe UI", 9))
        self.table_diag.setFixedHeight(170)
        layout_diag.addWidget(self.table_diag)
        grid.addWidget(gb_diag, 1, 1)

        main_layout.addLayout(grid)

        # Group 5: Footprint Occupancy Full Width
        gb_footprint = make_group("5. 2D Search Footprint Occupancy & Jaccard Overlap")
        layout_fp = QVBoxLayout(gb_footprint)
        self.table_fp = QTableWidget()
        self.table_fp.setColumnCount(7)
        self.table_fp.setHorizontalHeaderLabels(
            [
                "2D Projection",
                "Occupied Cells A",
                "Occupied Cells B",
                "Shared Cells",
                "Only in A",
                "Only in B",
                "Jaccard Overlap",
            ]
        )
        self.table_fp.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_fp.setFont(QFont("Segoe UI", 9))
        self.table_fp.setFixedHeight(125)
        layout_fp.addWidget(self.table_fp)
        main_layout.addWidget(gb_footprint)

    def set_data(self, da, db, la="A", lb="B"):
        key = (id(da), id(db), la, lb)
        if self._current_key == key:
            return
        self._current_key = key

        cA = da.get("coords")
        cB = db.get("coords")
        if cA is None or cB is None or len(cA) == 0 or len(cB) == 0:
            return

        cache_key = (id(da), id(db))
        if cache_key in self._cache:
            savings, common_res, fp_xy, fp_xz, fp_yz, band_res = self._cache[cache_key]
        else:
            ref_coords = np.maximum(cA.max(axis=0), cB.max(axis=0))
            prog_a = compute_geometric_alignment_progress(cA, ref_coords)
            prog_b = compute_geometric_alignment_progress(cB, ref_coords)

            savings = compute_expansion_savings(
                prog_a, prog_b, n_bins=PROGRESS_BINS, min_support=MIN_BIN_SUPPORT
            )
            common_res = compute_common_states_analysis(
                cA,
                da["h"],
                da["g"],
                da["f"],
                cB,
                db["h"],
                db["g"],
                db["f"],
            )
            fp_xy = compute_footprint_data(cA, cB, proj_dims=(0, 1), n_bins=FOOTPRINT_BINS)
            fp_xz = compute_footprint_data(cA, cB, proj_dims=(0, 2), n_bins=FOOTPRINT_BINS)
            fp_yz = compute_footprint_data(cA, cB, proj_dims=(1, 2), n_bins=FOOTPRINT_BINS)
            band_res = compute_band_comparison(
                prog_a, da["dev"], prog_b, db["dev"], n_bins=PROGRESS_BINS
            )

            self._cache[cache_key] = (
                savings,
                common_res,
                fp_xy,
                fp_xz,
                fp_yz,
                band_res,
            )

        nA = savings["expansions_a"]
        nB = savings["expansions_b"]
        saved = savings["total_nodes_saved"]
        red_pct = savings["total_reduction_pct"]

        self.kpi_nodes_a.setText(f"{nA:,}")
        self.kpi_sub_a.setText(f"Dataset A ({la})")

        self.kpi_nodes_b.setText(f"{nB:,}")
        self.kpi_sub_b.setText(f"Dataset B ({lb})")

        prefix = "+" if saved >= 0 else "−"
        self.kpi_saved.setText(f"{prefix}{abs(saved):,}")
        self.kpi_sub_saved.setText("Nodes Saved by B")

        self.kpi_red.setText(f"{red_pct:+.2f} %")
        self.kpi_sub_red.setText("Overall Reduction")

        self.kpi_common.setText(f"{common_res['num_common_unique']:,}")
        self.kpi_sub_common.setText("Shared unique states")

        j_a = da.get("num_jumps", 0)
        j_b = db.get("num_jumps", 0)
        j_red = ((j_a - j_b) / max(j_a, 1)) * 100.0 if j_a > 0 else 0.0

        mean_disp_a = (
            float(np.mean(da["jump_distances"])) if len(da.get("jump_distances", [])) > 0 else 0.0
        )
        mean_disp_b = (
            float(np.mean(db["jump_distances"])) if len(db.get("jump_distances", [])) > 0 else 0.0
        )

        effort_rows = [
            (
                "Total Expansions (log records)",
                f"{nA:,}",
                f"{nB:,}",
                f"{saved:+,d} ({red_pct:.2f} %)",
            ),
            (
                "Expansion Displacements (jumps)",
                f"{j_a:,}",
                f"{j_b:,}",
                f"{j_a - j_b:+,d} ({j_red:.2f} %)",
            ),
            (
                "Mean Displacement Step (L1)",
                f"{mean_disp_a:.2f}",
                f"{mean_disp_b:.2f}",
                f"{mean_disp_b - mean_disp_a:+.2f}",
            ),
            (
                "Mean Band Deviation (from diagonal)",
                f"{band_res['mean_dev_a']:.2f}",
                f"{band_res['mean_dev_b']:.2f}",
                f"{band_res['mean_dev_b'] - band_res['mean_dev_a']:+.2f}",
            ),
            (
                "Median Band Deviation",
                f"{band_res['median_dev_a']:.2f}",
                f"{band_res['median_dev_b']:.2f}",
                f"{band_res['median_dev_b'] - band_res['median_dev_a']:+.2f}",
            ),
        ]
        self._populate_table(self.table_effort, effort_rows)

        states_rows = [
            (
                "Unique Expanded States A",
                f"{common_res['num_unique_a']:,}",
                "Distinct coordinates in A",
            ),
            (
                "Unique Expanded States B",
                f"{common_res['num_unique_b']:,}",
                "Distinct coordinates in B",
            ),
            (
                "Common Unique States",
                f"{common_res['num_common_unique']:,}",
                "Visited by both executions",
            ),
            ("Exclusive to A (Only A)", f"{common_res['num_only_a']:,}", "Avoided by Candidate B"),
            (
                "Exclusive to B (Only B)",
                f"{common_res['num_only_b']:,}",
                "Additional states explored by B",
            ),
            (
                "Inconsistent h States (A / B)",
                f"{common_res['inconsistent_h_a']} / {common_res['inconsistent_h_b']}",
                "Excluded from Δh if > 0",
            ),
        ]
        self._populate_table(self.table_states, states_rows)

        heur_rows = [
            (
                "Valid Common States for Δh",
                f"{common_res['num_valid_h_common']:,}",
                "Consistent h in both A and B",
            ),
            (
                "Mean Δh (h_B − h_A)",
                f"{common_res['mean_delta_h']:+.3f}",
                "Positive indicates higher h in B",
            ),
            ("Median Δh", f"{common_res['median_delta_h']:+.3f}", "50th percentile of difference"),
            (
                "Δh > 0 (Candidate B > Baseline A)",
                f"{common_res['pct_delta_h_pos']:.2f} %",
                "B has stronger heuristic value",
            ),
            (
                "Δh = 0 (Identical Heuristic)",
                f"{common_res['pct_delta_h_zero']:.2f} %",
                "Same heuristic informativeness",
            ),
            (
                "Δh < 0 (Candidate B < Baseline A)",
                f"{common_res['pct_delta_h_neg']:.2f} %",
                "A has higher heuristic value",
            ),
        ]
        self._populate_table(self.table_heur, heur_rows)

        f_a_match = common_res["f_diag_a"]["match_pct"]
        f_b_match = common_res["f_diag_b"]["match_pct"]
        diag_rows = [
            (
                "f == g + h Log Check (Dataset A)",
                f"{f_a_match:.1f} % match",
                "Verified on all raw entries",
            ),
            (
                "f == g + h Log Check (Dataset B)",
                f"{f_b_match:.1f} % match",
                "Verified on all raw entries",
            ),
            (
                "Valid Common States for g Check",
                f"{common_res['num_valid_g_common']:,}",
                "Consistent g in both executions",
            ),
            (
                "Common States with Equal g",
                f"{common_res['num_g_match']:,} ({common_res['pct_g_match']:.2f} %)",
                "Optimal path cost agreement",
            ),
            (
                "Common States with Different g",
                f"{common_res['num_g_mismatch']:,}",
                "Different path costs observed",
            ),
            (
                "Inconsistent g States (A / B)",
                f"{common_res['inconsistent_g_a']:,} / {common_res['inconsistent_g_b']:,}",
                "Reopened/multi-cost states in search",
            ),
        ]
        self._populate_table(self.table_diag, diag_rows)

        fp_rows = [
            (
                "XY (Top: Seq A vs Seq B)",
                f"{fp_xy['n_occupied_a']:,}",
                f"{fp_xy['n_occupied_b']:,}",
                f"{fp_xy['n_shared']:,}",
                f"{fp_xy['n_only_a']:,}",
                f"{fp_xy['n_only_b']:,}",
                f"{fp_xy['jaccard']:.4f}",
            ),
            (
                "XZ (Front: Seq A vs Seq C)",
                f"{fp_xz['n_occupied_a']:,}",
                f"{fp_xz['n_occupied_b']:,}",
                f"{fp_xz['n_shared']:,}",
                f"{fp_xz['n_only_a']:,}",
                f"{fp_xz['n_only_b']:,}",
                f"{fp_xz['jaccard']:.4f}",
            ),
            (
                "YZ (Side: Seq B vs Seq C)",
                f"{fp_yz['n_occupied_a']:,}",
                f"{fp_yz['n_occupied_b']:,}",
                f"{fp_yz['n_shared']:,}",
                f"{fp_yz['n_only_a']:,}",
                f"{fp_yz['n_only_b']:,}",
                f"{fp_yz['jaccard']:.4f}",
            ),
        ]
        self._populate_table(self.table_fp, fp_rows)

    def _populate_table(self, table_widget, rows):
        table_widget.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                if c_idx > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table_widget.setItem(r_idx, c_idx, item)
