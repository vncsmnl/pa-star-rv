"""
PA-Star Runtime Runtime Visualizer
"""

import os
import sys
import traceback

import matplotlib
import numpy as np

matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import LogNorm, TwoSlopeNorm
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ─────────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────────

P = {
    "a": "#1f77b4",  # blue  — A
    "b": "#d62728",  # red   — B
    "warn": "#ff7f0e",
    "grid": "#e0e0e0",
}


# ─────────────────────────────────────────────
#  PARSING
# ─────────────────────────────────────────────


def process_log_file(filepath):
    f_costs, g_costs, h_costs, iterations = {}, {}, {}, []
    with open(filepath, "r") as fh:
        for _ in range(5):
            fh.readline()
        line = fh.readline()
        while line and line.strip() == "":
            line = fh.readline()
        if not line:
            raise ValueError("File contains no execution data.")

        parts = line.split("\t")
        dimensions = len(parts[3].strip().replace("(", "").replace(")", "").split())

        while line:
            s = line.strip()
            if not s or s.startswith("P"):
                break
            parts = line.split("\t")
            if len(parts) < 5:
                line = fh.readline()
                continue

            node = tuple(
                int(n)
                for n in parts[3].strip().replace("(", "").replace(")", "").split()
            )
            iteration_id = int(parts[1])
            iterations.append((iteration_id, node))

            vs = parts[4].strip()
            if "g(" in vs:
                vals = vs.split()
                g_val = vals[0].replace("g(", "").replace(")", "")
                h_val = vals[1].replace("h(", "").replace(")", "")
                f_val = vals[2].replace("f(", "").replace(")", "")
            else:
                clean = vs.replace("(", "").replace(")", "").split()
                g_val, h_val, f_val = clean[2], clean[5], clean[8]

            g_costs[node] = int(g_val)
            h_costs[node] = int(h_val)
            f_costs[node] = int(f_val)
            line = fh.readline()

    iterations.sort()
    return {
        "f": f_costs,
        "g": g_costs,
        "h": h_costs,
        "jumps": [],
        "num_jumps": 0,
        "iterations": iterations,
        "dimensions": dimensions,
        "num_expansions": {},
    }


def calculate_metrics(data):
    iters = data["iterations"]
    jumps = data["jumps"]

    def is_nb(a, b):
        return all(abs(a[i] - b[i]) <= 1 for i in range(len(a)))

    prev = None
    jc = 0
    for _, v in iters:
        data["num_expansions"][v] = data["num_expansions"].get(v, 0) + 1
        if prev is not None and not is_nb(prev, v):
            jc += 1
            jumps.append((prev, v))
        prev = v
    data["num_jumps"] = jc
    return data


# ─────────────────────────────────────────────
#  SHARED PLOT HELPERS
# ─────────────────────────────────────────────


def _style(ax):
    ax.set_facecolor("white")
    ax.tick_params(colors="black", labelsize=8)
    ax.xaxis.label.set_color("black")
    ax.yaxis.label.set_color("black")
    if hasattr(ax, "zaxis"):
        ax.zaxis.label.set_color("black")
    ax.title.set_color("black")
    for sp in ax.spines.values():
        sp.set_edgecolor("#aaaaaa")
    ax.grid(True, color=P["grid"], linewidth=0.5)


def _cbar(fig, im, ax, label=""):
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label(label, color="black", fontsize=8)
    cb.ax.yaxis.set_tick_params(color="black")
    plt.setp(cb.ax.yaxis.get_ticklabels(), color="black")


def _extract(data):
    iters = data["iterations"]
    x = np.array([n[0] for _, n in iters])
    y = np.array([n[1] for _, n in iters])
    z = np.array([n[2] for _, n in iters])
    t = np.array([ts for ts, _ in iters])
    h = np.array([data["h"].get(n, np.nan) for _, n in iters])
    g = np.array([data["g"].get(n, np.nan) for _, n in iters])
    mc = (x + y + z) / 3.0
    dev = np.sqrt((x - mc) ** 2 + (y - mc) ** 2 + (z - mc) ** 2)
    return x, y, z, t, h, g, dev


def _h2d(x, y, bins=80):
    return np.histogram2d(x, y, bins=bins)


def _rolling(arr, W, fn):
    out = []
    for i in range(len(arr)):
        lo, hi = max(0, i - W // 2), min(len(arr), i + W // 2)
        v = arr[lo:hi]
        v = v[~np.isnan(v)]
        out.append(fn(v) if len(v) else np.nan)
    return np.array(out)


# ─────────────────────────────────────────────
#  PLOT GENERATORS
# ─────────────────────────────────────────────


def plot_classic(data, label=""):
    x, y, z, t, *_ = _extract(data)
    fig = plt.figure(figsize=(14, 10), facecolor="white")
    if label:
        fig.suptitle(label, fontsize=11, fontweight="bold")

    ax3d = fig.add_subplot(2, 2, 1, projection="3d")
    ax3d.set_facecolor("white")
    sc = ax3d.scatter(x, y, z, c=t, cmap="plasma", s=10)
    ax3d.set_xlabel("Seq A (i)")
    ax3d.set_ylabel("Seq B (j)")
    ax3d.set_zlabel("Seq C (k)")
    ax3d.set_title("3D View")
    ax3d.tick_params(colors="black")

    def _proj(pos, xd, yd, xl, yl, sl):
        ax = fig.add_subplot(pos)
        ax.scatter(xd, yd, c=t, cmap="plasma", s=10, alpha=0.7)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.text(
            -0.15,
            0.5,
            sl,
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            va="center",
            ha="center",
            rotation=90,
        )
        d = np.abs(xd - yd) / np.sqrt(2)
        ax.text(
            0.02,
            0.98,
            f"Band width: {np.max(d) - np.min(d):.1f}",
            transform=ax.transAxes,
            fontsize=9,
            va="top",
            bbox={"boxstyle": "round", "facecolor": "#eeeeee", "alpha": 0.8},
        )
        _style(ax)

    _proj(222, x, y, "Seq A (i)", "Seq B (j)", "XY (Top)")
    _proj(223, x, z, "Seq A (i)", "Seq C (k)", "XZ (Front)")
    _proj(224, y, z, "Seq B (j)", "Seq C (k)", "YZ (Side)")

    ca = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    cb = fig.colorbar(sc, cax=ca)
    cb.set_label("Iteration")
    plt.tight_layout(rect=[0, 0, 0.90, 0.96])
    return fig


def plot_density(data, label=""):
    x, y, z, *_ = _extract(data)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor="white")
    title = "Exploration Density  —  brighter = more nodes visited"
    fig.suptitle(
        f"[{label}]  {title}" if label else title, fontsize=12, fontweight="bold"
    )

    for ax, (xd, yd, xl, yl, tt) in zip(
        axes,
        [
            (x, y, "Seq A (i)", "Seq B (j)", "XY (Top)"),
            (x, z, "Seq A (i)", "Seq C (k)", "XZ (Front)"),
            (y, z, "Seq B (j)", "Seq C (k)", "YZ (Side)"),
        ],
    ):
        H, xe, ye = _h2d(xd, yd)
        Hm = np.ma.masked_where(H == 0, H)
        im = ax.pcolormesh(
            xe, ye, Hm.T, cmap="plasma", norm=LogNorm(vmin=1, vmax=max(H.max(), 1))
        )
        lim = max(xe[-1], ye[-1])
        ax.plot([0, lim], [0, lim], color=P["b"], lw=1.2, linestyle="--", alpha=0.7)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(tt)
        _style(ax)
        _cbar(fig, im, ax, "Node visits (log)")

    plt.tight_layout()
    return fig


def plot_dynamics(data, label=""):
    iters = data["iterations"]
    h_map = data["h"]
    jumps = data["jumps"]

    h_vals = np.array([h_map.get(n, np.nan) for _, n in iters], dtype=float)
    n = len(h_vals)
    xn = np.linspace(0, 1, n)
    W = max(50, n // 100)

    min_h = _rolling(h_vals, W, np.min)
    avg_h = _rolling(h_vals, W, np.mean)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), facecolor="white")
    title = "Search Dynamics"
    fig.suptitle(
        f"[{label}]  {title}" if label else title, fontsize=14, fontweight="bold"
    )

    ax = axes[0, 0]
    ax.plot(xn, min_h, color=P["b"], lw=1.4, label=f"min h  (W={W})")
    ax.set_xlabel("Normalised progress")
    ax.set_ylabel("min h(n)")
    ax.set_title("Minimum h(n) — proxy for OPEN frontier quality")
    ax.legend(facecolor="white")
    _style(ax)

    ax = axes[0, 1]
    ax.plot(xn, avg_h, color=P["a"], lw=1.4, label=f"avg h  (W={W})")
    ax.set_xlabel("Normalised progress")
    ax.set_ylabel("avg h(n)")
    ax.set_title("Average h(n) — frontier informativeness")
    ax.legend(facecolor="white")
    _style(ax)

    ax = axes[1, 0]
    if jumps:
        dists = [sum(abs(b[i] - a[i]) for i in range(len(a))) for a, b in jumps]
        ax.hist(dists, bins=40, color=P["a"], edgecolor="white", alpha=0.85)
        md = np.mean(dists)
        ax.axvline(md, color=P["b"], lw=1.6, linestyle="--", label=f"Mean: {md:.1f}")
        ax.set_xlabel("Jump distance (Manhattan)")
        ax.set_ylabel("Count")
        ax.set_title(f"Jump Distance Distribution  (n={len(jumps):,})  —  L1 metric")
        ax.legend(facecolor="white")
    else:
        ax.text(
            0.5,
            0.5,
            "No jumps recorded",
            transform=ax.transAxes,
            ha="center",
            va="center",
        )
        ax.set_title("Jump Distance Distribution")
    _style(ax)

    ax = axes[1, 1]
    if jumps:
        prev = None
        jxs = []
        for idx, (_, node) in enumerate(iters):
            if prev is not None and not all(
                abs(node[i] - prev[i]) <= 1 for i in range(len(node))
            ):
                jxs.append(idx / max(n - 1, 1))
            prev = node
        jxs = np.array(jxs)
        cum = np.arange(1, len(jxs) + 1)
        ax.plot(jxs, cum, color=P["warn"], lw=1.5)
        ax.fill_between(jxs, cum, alpha=0.12, color=P["warn"])
        ax.set_xlabel("Normalised progress")
        ax.set_ylabel("Cumulative jumps")
        ax.set_title("Cumulative Jumps  —  flat slope = focused search")
    else:
        ax.text(
            0.5,
            0.5,
            "No jumps recorded",
            transform=ax.transAxes,
            ha="center",
            va="center",
        )
        ax.set_title("Cumulative Jumps")
    _style(ax)

    plt.tight_layout()
    return fig


def plot_band(data, label=""):
    _, _, _, t, _, _, dev = _extract(data)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor="white")
    title = "Diagonal Band Deviation  —  distance from line i = j = k"
    fig.suptitle(
        f"[{label}]  {title}" if label else title, fontsize=12, fontweight="bold"
    )

    ax = axes[0]
    sc = ax.scatter(t, dev, s=3, c=dev, cmap="plasma", alpha=0.4)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Deviation from diagonal")
    ax.set_title("Deviation per Node")
    _style(ax)
    _cbar(fig, sc, ax, "Deviation")

    ax = axes[1]
    ax.hist(dev, bins=60, color=P["a"], edgecolor="white", alpha=0.85)
    ax.axvline(
        np.mean(dev),
        color=P["b"],
        lw=1.8,
        linestyle="--",
        label=f"Mean: {np.mean(dev):.1f}",
    )
    ax.axvline(
        np.median(dev),
        color=P["warn"],
        lw=1.8,
        linestyle=":",
        label=f"Median: {np.median(dev):.1f}",
    )
    ax.set_xlabel("Deviation")
    ax.set_ylabel("Count")
    ax.set_title("Deviation Distribution  —  narrow peak = tight search band")
    ax.legend(facecolor="white")
    _style(ax)

    plt.tight_layout()
    return fig


def plot_footprint(da, db, la="A", lb="B"):
    xA, yA, zA, *_ = _extract(da)
    xB, yB, zB, *_ = _extract(db)

    BINS = 80
    fig = plt.figure(figsize=(18, 12), facecolor="white")
    fig.suptitle(
        f"Search Footprint  ·  A = {la}  vs  B = {lb}\n"
        "Blue = A visited more  |  Red = B visited more  |  White = equal",
        fontsize=12,
        fontweight="bold",
    )
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.30)

    for row, (xda, yda, xdb, ydb, xl, yl, tt) in enumerate(
        [
            (xA, yA, xB, yB, "Seq A (i)", "Seq B (j)", "XY (Top)"),
            (xA, zA, xB, zB, "Seq A (i)", "Seq C (k)", "XZ (Front)"),
            (yA, zA, yB, zB, "Seq B (j)", "Seq C (k)", "YZ (Side)"),
        ]
    ):
        all_x = np.concatenate([xda, xdb])
        all_y = np.concatenate([yda, ydb])
        rng = [[all_x.min(), all_x.max()], [all_y.min(), all_y.max()]]
        HA, xe, ye = np.histogram2d(xda, yda, bins=BINS, range=rng)
        HB, _, _ = np.histogram2d(xdb, ydb, bins=BINS, range=rng)
        vmax = max(HA.max(), HB.max(), 1)
        dlim = max(xe[-1], ye[-1])

        def _dg(ax, dlim=dlim):
            ax.plot(
                [0, dlim], [0, dlim], color="gray", lw=0.8, linestyle="--", alpha=0.5
            )

        ax = fig.add_subplot(gs[row, 0])
        Hm = np.ma.masked_where(HA == 0, HA)
        im = ax.pcolormesh(xe, ye, Hm.T, cmap="plasma", norm=LogNorm(vmin=1, vmax=vmax))
        _dg(ax)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(
            f"{tt}  ·  A: {la}\n({len(xda):,} nodes)", color=P["a"], fontsize=9
        )
        _style(ax)
        _cbar(fig, im, ax, "visits (log)")

        ax = fig.add_subplot(gs[row, 1])
        Hm = np.ma.masked_where(HB == 0, HB)
        im = ax.pcolormesh(xe, ye, Hm.T, cmap="plasma", norm=LogNorm(vmin=1, vmax=vmax))
        _dg(ax)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(
            f"{tt}  ·  B: {lb}\n({len(xdb):,} nodes)", color=P["b"], fontsize=9
        )
        _style(ax)
        _cbar(fig, im, ax, "visits (log)")

        HAn = HA / max(HA.sum(), 1)
        HBn = HB / max(HB.sum(), 1)
        diff = HBn - HAn
        amax = max(np.abs(diff).max(), 1e-9)
        ax = fig.add_subplot(gs[row, 2])
        im = ax.pcolormesh(
            xe,
            ye,
            diff.T,
            cmap="RdBu_r",
            norm=TwoSlopeNorm(vmin=-amax, vcenter=0, vmax=amax),
        )
        _dg(ax)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(
            f"{tt}  ·  Difference (B−A)\nBlue=A more  |  Red=B more", fontsize=9
        )
        _style(ax)
        _cbar(fig, im, ax, "density diff")

    return fig


def plot_comparison(da, db, la="A", lb="B"):
    _, _, _, tA, hA, _, devA = _extract(da)
    _, _, _, tB, hB, _, devB = _extract(db)

    fig = plt.figure(figsize=(16, 13), facecolor="white")
    fig.suptitle(
        f"Comparison  ·  A = {la}  vs  B = {lb}", fontsize=14, fontweight="bold"
    )
    gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.50, wspace=0.38)

    W_a = max(50, len(hA) // 100)
    W_b = max(50, len(hB) // 100)
    min_hA = _rolling(hA, W_a, np.min)
    min_hB = _rolling(hB, W_b, np.min)
    avg_hA = _rolling(hA, W_a, np.mean)
    avg_hB = _rolling(hB, W_b, np.mean)

    ax = fig.add_subplot(gs[0, 0:2])
    ax.plot(
        np.linspace(0, 1, len(min_hA)), min_hA, color=P["a"], lw=1.5, label=f"A: {la}"
    )
    ax.plot(
        np.linspace(0, 1, len(min_hB)), min_hB, color=P["b"], lw=1.5, label=f"B: {lb}"
    )
    ax.set_xlabel("Normalised progress")
    ax.set_ylabel("min h(n)")
    ax.set_title("Frontier Quality  (min h)\nlower = closer to goal sooner")
    ax.legend(facecolor="white")
    _style(ax)

    ax = fig.add_subplot(gs[0, 2:4])
    ax.plot(
        np.linspace(0, 1, len(avg_hA)), avg_hA, color=P["a"], lw=1.5, label=f"A: {la}"
    )
    ax.plot(
        np.linspace(0, 1, len(avg_hB)), avg_hB, color=P["b"], lw=1.5, label=f"B: {lb}"
    )
    ax.set_xlabel("Normalised progress")
    ax.set_ylabel("avg h(n)")
    ax.set_title("Frontier Informativeness  (avg h)")
    ax.legend(facecolor="white")
    _style(ax)

    ax = fig.add_subplot(gs[1, 0:2])
    ax.hist(devA, bins=60, color=P["a"], alpha=0.55, density=True, label=f"A: {la}")
    ax.hist(devB, bins=60, color=P["b"], alpha=0.55, density=True, label=f"B: {lb}")
    ax.axvline(
        np.mean(devA),
        color=P["a"],
        lw=1.6,
        linestyle="--",
        label=f"mean A: {np.mean(devA):.1f}",
    )
    ax.axvline(
        np.mean(devB),
        color=P["b"],
        lw=1.6,
        linestyle="--",
        label=f"mean B: {np.mean(devB):.1f}",
    )
    ax.set_xlabel("Deviation")
    ax.set_ylabel("Density")
    ax.set_title("Band Deviation  (overlaid)")
    ax.legend(facecolor="white", fontsize=8)
    _style(ax)

    ax = fig.add_subplot(gs[1, 2:4])
    ja = da["jumps"]
    jb = db["jumps"]
    if ja and jb:
        dA = [sum(abs(b[i] - a[i]) for i in range(len(a))) for a, b in ja]
        dB = [sum(abs(b[i] - a[i]) for i in range(len(a))) for a, b in jb]
        ax.hist(dA, bins=40, color=P["a"], alpha=0.55, density=True, label=f"A: {la}")
        ax.hist(dB, bins=40, color=P["b"], alpha=0.55, density=True, label=f"B: {lb}")
        ax.axvline(
            np.mean(dA),
            color=P["a"],
            lw=1.6,
            linestyle="--",
            label=f"mean A: {np.mean(dA):.1f}",
        )
        ax.axvline(
            np.mean(dB),
            color=P["b"],
            lw=1.6,
            linestyle="--",
            label=f"mean B: {np.mean(dB):.1f}",
        )
    ax.set_xlabel("Jump distance (Manhattan)")
    ax.set_ylabel("Density")
    ax.set_title("Jump Distance  (overlaid)")
    ax.legend(facecolor="white", fontsize=8)
    _style(ax)

    # absolute bars
    ax_bar = fig.add_subplot(gs[2, 0:2])
    metrics = [
        ("Nodes\nexplored", len(tA), len(tB)),
        ("Jumps", da["num_jumps"], db["num_jumps"]),
        ("Mean\ndeviation", round(np.mean(devA), 1), round(np.mean(devB), 1)),
    ]
    names = [m[0] for m in metrics]
    va_arr = np.array([m[1] for m in metrics], dtype=float)
    vb_arr = np.array([m[2] for m in metrics], dtype=float)
    xp = np.arange(len(names))
    w = 0.35
    ba = ax_bar.bar(xp - w / 2, va_arr, w, color=P["a"], alpha=0.85, label=f"A: {la}")
    bb = ax_bar.bar(xp + w / 2, vb_arr, w, color=P["b"], alpha=0.85, label=f"B: {lb}")
    for bar, val in list(zip(ba, va_arr)) + list(zip(bb, vb_arr)):
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.01,
            f"{val:,.0f}" if val >= 10 else f"{val:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax_bar.set_xticks(xp)
    ax_bar.set_xticklabels(names, fontsize=9)
    ax_bar.set_ylabel("Absolute value")
    ax_bar.set_title("Absolute Metrics")
    ax_bar.legend(facecolor="white")
    _style(ax_bar)

    # improvement table
    ax_tbl = fig.add_subplot(gs[2, 2:4])
    ax_tbl.set_facecolor("white")
    for sp in ax_tbl.spines.values():
        sp.set_edgecolor("#aaaaaa")
    ax_tbl.set_xticks([])
    ax_tbl.set_yticks([])

    def _pct(a, b):
        if a == 0:
            return "N/A"
        r = (a - b) / a * 100
        return f"{'−' if r >= 0 else '+'}{abs(r):.1f} %"

    rows = [
        ("Metric", f"A: {la}", f"B: {lb}", "Reduction"),
        ("Nodes explored", f"{len(tA):,}", f"{len(tB):,}", _pct(len(tA), len(tB))),
        (
            "Jumps",
            f"{da['num_jumps']:,}",
            f"{db['num_jumps']:,}",
            _pct(da["num_jumps"], db["num_jumps"]),
        ),
        (
            "Mean deviation",
            f"{np.mean(devA):.1f}",
            f"{np.mean(devB):.1f}",
            _pct(np.mean(devA), np.mean(devB)),
        ),
    ]
    col_xs = [0.02, 0.27, 0.52, 0.76]
    row_ys = [0.88, 0.70, 0.52, 0.34]

    for ci, (cx, hdr) in enumerate(zip(col_xs, rows[0])):
        ax_tbl.text(
            cx,
            0.95,
            hdr,
            transform=ax_tbl.transAxes,
            color="#444444",
            fontsize=9,
            fontweight="bold",
            va="top",
        )

    for ri, row in enumerate(rows[1:]):
        metric, va, vb, pct_str = row
        y = row_ys[ri]
        ax_tbl.text(
            col_xs[0],
            y,
            metric,
            transform=ax_tbl.transAxes,
            color="black",
            fontsize=9,
            va="top",
        )
        ax_tbl.text(
            col_xs[1],
            y,
            va,
            transform=ax_tbl.transAxes,
            color=P["a"],
            fontsize=9,
            va="top",
        )
        ax_tbl.text(
            col_xs[2],
            y,
            vb,
            transform=ax_tbl.transAxes,
            color=P["b"],
            fontsize=9,
            va="top",
        )
        an = float(rows[ri + 1][1].replace(",", ""))
        bn = float(rows[ri + 1][2].replace(",", ""))
        ax_tbl.text(
            col_xs[3],
            y,
            pct_str,
            transform=ax_tbl.transAxes,
            fontsize=9,
            fontweight="bold",
            color=P["b"] if bn <= an else P["warn"],
            va="top",
        )

    ax_tbl.axhline(0.88, color="#aaaaaa", lw=0.8, transform=ax_tbl.transAxes)
    ax_tbl.set_title("Improvement Table  (B vs A)")
    return fig


# ─────────────────────────────────────────────
#  WORKER THREAD
# ─────────────────────────────────────────────


class RenderWorker(QObject):
    """Runs one plot generator in a background thread and emits the result."""

    done = pyqtSignal(str, object)  # (tab_key, figure)
    error = pyqtSignal(str, str)  # (tab_key, error_message)
    status = pyqtSignal(str)  # status bar text

    def __init__(self, tab_key, fn, *args, **kwargs):
        super().__init__()
        self.tab_key = tab_key
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.status.emit(f"Rendering {self.tab_key}…")
        try:
            fig = self.fn(*self.args, **self.kwargs)
            self.done.emit(self.tab_key, fig)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            self.error.emit(self.tab_key, traceback.format_exc())


# ─────────────────────────────────────────────
#  CANVAS WIDGET
# ─────────────────────────────────────────────


class PlotCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self._canvas = None
        self._fig = None

    def set_figure(self, fig):
        if self._canvas:
            self.layout_.removeWidget(self._canvas)
            self._canvas.deleteLater()
            plt.close(self._fig)
        self._fig = fig
        self._canvas = FigureCanvas(fig)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout_.addWidget(self._canvas)
        self._canvas.draw()

    def figure(self):
        return self._fig


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────

TAB_DEFS = [
    ("classic", "3D + Projections"),
    ("density", "Exploration Density"),
    ("dynamics", "Search Dynamics"),
    ("band", "Band Deviation"),
    ("footprint", "Search Footprint"),
    ("compare", "Comparison"),
]
SINGLE_TABS = ["classic", "density", "dynamics", "band"]
DUAL_TABS = ["footprint", "compare"]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PA-Star Runtime Visualizer")
        self.resize(1400, 950)

        self.data_a = None
        self.label_a = "A"
        self.data_b = None
        self.label_b = "B"
        self.showing = "a"  # which file single-file tabs display

        self._threads = []  # keep references so GC doesn't kill them
        self._canvases = {}  # key -> PlotCanvas

        self._build_ui()

    # ── UI ───────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(4)
        root_layout.setContentsMargins(10, 8, 10, 6)

        # button bar
        btn_row = QHBoxLayout()

        def mkbtn(text, color, slot):
            b = QPushButton(text)
            b.setFont(QFont("Arial", 10, QFont.Bold))
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:white;border:none;"
                f"padding:6px 14px;border-radius:4px;}}"
                f"QPushButton:hover{{background:{color};opacity:0.85;}}"
            )
            b.clicked.connect(slot)
            return b

        btn_row.addWidget(mkbtn("📂 Open A", P["a"], self.open_a))
        btn_row.addWidget(mkbtn("📂 Open B", P["b"], self.open_b))
        btn_row.addSpacing(20)
        btn_row.addWidget(mkbtn("💾 Save current tab", "#555555", self.save_current))
        btn_row.addWidget(mkbtn("💾 Export all tabs", "#333333", self.export_all))
        btn_row.addStretch()
        root_layout.addLayout(btn_row)

        # file labels
        lbl_row = QHBoxLayout()
        self.lbl_a = QLabel("A: —")
        self.lbl_a.setFont(QFont("Arial", 9, QFont.Bold))
        self.lbl_a.setStyleSheet(f"color:{P['a']}")
        self.lbl_b = QLabel("B: —")
        self.lbl_b.setFont(QFont("Arial", 9, QFont.Bold))
        self.lbl_b.setStyleSheet(f"color:{P['b']}")
        lbl_row.addWidget(self.lbl_a)
        lbl_row.addSpacing(30)
        lbl_row.addWidget(self.lbl_b)
        lbl_row.addStretch()
        root_layout.addLayout(lbl_row)

        # AB switcher
        sw_row = QHBoxLayout()
        sw_row.addWidget(QLabel("Viewing in single-file tabs:"))
        self.rb_a = QRadioButton("A")
        self.rb_a.setChecked(True)
        self.rb_b = QRadioButton("B")
        self.rb_a.setStyleSheet(f"color:{P['a']};font-weight:bold")
        self.rb_b.setStyleSheet(f"color:{P['b']};font-weight:bold")
        self._rb_group = QButtonGroup()
        self._rb_group.addButton(self.rb_a)
        self._rb_group.addButton(self.rb_b)
        self.rb_a.toggled.connect(self._on_switch)
        sw_row.addWidget(self.rb_a)
        sw_row.addWidget(self.rb_b)
        sw_row.addStretch()
        root_layout.addLayout(sw_row)

        # status
        self.status_lbl = QLabel("Open a log file to begin.")
        self.status_lbl.setFont(QFont("Arial", 9))
        self.status_lbl.setStyleSheet("color:#444444")
        root_layout.addWidget(self.status_lbl)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 10))
        root_layout.addWidget(self.tabs)

        for key, label in TAB_DEFS:
            canvas = PlotCanvas()
            self._canvases[key] = canvas
            self.tabs.addTab(canvas, label)

    # ── helpers ──────────────────────────────

    def _status(self, msg):
        self.status_lbl.setText(msg)
        QApplication.processEvents()

    def _status_ready(self):
        parts = []
        if self.data_a:
            parts.append(
                f"A: {self.label_a}  {len(self.data_a['iterations']):,} nodes / {self.data_a['num_jumps']:,} jumps"
            )
        if self.data_b:
            parts.append(
                f"B: {self.label_b}  {len(self.data_b['iterations']):,} nodes / {self.data_b['num_jumps']:,} jumps"
            )
        self._status("   ·   ".join(parts) if parts else "Ready.")

    def _single_data(self):
        if self.showing == "b" and self.data_b is not None:
            return self.data_b, self.label_b
        if self.data_a is not None:
            return self.data_a, self.label_a
        return self.data_b, self.label_b

    # ── rendering ────────────────────────────

    def _render(self, tab_key, fn, *args):
        """Spin up a QThread for one plot generator."""
        thread = QThread()
        worker = RenderWorker(tab_key, fn, *args)
        worker.moveToThread(thread)

        # wire signals
        thread.started.connect(worker.run)
        worker.status.connect(self._status)
        worker.done.connect(self._on_render_done)
        worker.error.connect(self._on_render_error)

        # cleanup when thread finishes
        worker.done.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._threads.append(thread)  # prevent GC
        thread.start()

    def _on_render_done(self, key, fig):
        self._canvases[key].set_figure(fig)
        # clean finished threads
        self._threads = [t for t in self._threads if t.isRunning()]
        if not self._threads:
            self._status_ready()

    def _on_render_error(self, key, msg):
        print(f"[render error — {key}]\n{msg}")
        self._status(f"Error rendering {key} (see console).")
        self._threads = [t for t in self._threads if t.isRunning()]

    def _launch_single(self, data, label):
        self._render("classic", plot_classic, data, label)
        self._render("density", plot_density, data, label)
        self._render("dynamics", plot_dynamics, data, label)
        self._render("band", plot_band, data, label)

    def _launch_dual(self):
        self._render(
            "footprint",
            plot_footprint,
            self.data_a,
            self.data_b,
            self.label_a,
            self.label_b,
        )
        self._render(
            "compare",
            plot_comparison,
            self.data_a,
            self.data_b,
            self.label_a,
            self.label_b,
        )

    # ── file loading ─────────────────────────

    def _load(self, fp, side):
        name = os.path.basename(fp)
        self._status(f"Parsing {name}…")
        QApplication.processEvents()
        try:
            raw = process_log_file(fp)
            data = calculate_metrics(raw)
        except (OSError, TypeError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")
            self._status("Error loading file.")
            return

        if side == "a":
            self.data_a = data
            self.label_a = name
            self.lbl_a.setText(f"A: {name}")
            self.rb_a.setChecked(True)
            self.showing = "a"
        else:
            self.data_b = data
            self.label_b = name
            self.lbl_b.setText(f"B: {name}")
            self.rb_b.setChecked(True)
            self.showing = "b"

        # launch renders
        d, l = self._single_data()
        self._launch_single(d, l)
        if self.data_a and self.data_b:
            self._launch_dual()

    def open_a(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Open Log — A", "", "Text Files (*.txt);;All Files (*)"
        )
        if fp:
            self._load(fp, "a")

    def open_b(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Open Log — B", "", "Text Files (*.txt);;All Files (*)"
        )
        if fp:
            self._load(fp, "b")

    def _on_switch(self, checked):
        if not checked:
            return
        self.showing = "a" if self.rb_a.isChecked() else "b"
        d, l = self._single_data()
        if d is not None:
            self._launch_single(d, l)

    # ── save / export ─────────────────────────

    def save_current(self):
        idx = self.tabs.currentIndex()
        key = TAB_DEFS[idx][0]
        fig = self._canvases[key].figure()
        if fig is None:
            QMessageBox.warning(self, "Warning", "No graph on the current tab.")
            return
        fp, _ = QFileDialog.getSaveFileName(
            self,
            "Save current tab",
            "",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg);;All Files (*)",
        )
        if not fp:
            return
        try:
            fig.savefig(fp, dpi=300, bbox_inches="tight", facecolor="white")
            QMessageBox.information(self, "Saved", f"Saved:\n{fp}")
        except (OSError, TypeError, ValueError) as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{e}")

    def export_all(self):
        has_any = any(self._canvases[k].figure() for k, _ in TAB_DEFS)
        if not has_any:
            QMessageBox.warning(self, "Warning", "No graphs loaded yet.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not folder:
            return

        parts = []
        if self.data_a:
            parts.append(os.path.splitext(self.label_a)[0])
        if self.data_b:
            parts.append(os.path.splitext(self.label_b)[0])
        prefix = "_vs_".join(parts) if parts else "pastar"

        saved = []
        failed = []
        for key, _ in TAB_DEFS:
            fig = self._canvases[key].figure()
            if fig is None:
                continue
            fp = os.path.join(folder, f"{prefix}__{key}.png")
            try:
                fig.savefig(fp, dpi=300, bbox_inches="tight", facecolor="white")
                saved.append(os.path.basename(fp))
            except (OSError, TypeError, ValueError) as e:
                failed.append(f"{key}: {e}")

        msg = f"Exported {len(saved)} image(s) to:\n{folder}"
        if saved:
            msg += "\n\n" + "\n".join(saved)
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed)
        QMessageBox.information(self, "Export complete", msg)

    def closeEvent(self, event):
        # stop any running threads cleanly
        for t in self._threads:
            if t.isRunning():
                t.quit()
                t.wait(500)
        event.accept()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
