"""
High-Performance Vectorized Log Parser for PA-Star
Parses execution logs directly into contiguous C-compatible NumPy arrays.
"""

import os

import numpy as np


def parse_log_file(filepath, progress_callback=None):
    """
    Parses a PA-Star log file into a dictionary of NumPy arrays.

    Returns:
        dict with keys:
            - 'iterations': np.ndarray (N,) int32
            - 'coords': np.ndarray (N, D) int32
            - 'g': np.ndarray (N,) int32
            - 'h': np.ndarray (N,) int32
            - 'f': np.ndarray (N,) int32
            - 'dimensions': int
            - 'dev': np.ndarray (N,) float32
            - 'num_jumps': int
            - 'jump_distances': np.ndarray (J,) int32
            - 'jump_indices': np.ndarray (J,) int32
    """
    file_size = os.path.getsize(filepath)

    iterations = []
    coords_list = []
    g_list = []
    h_list = []
    f_list = []

    dimensions = 3

    with open(filepath, encoding="utf-8", errors="replace") as fh:
        # 1. Skip header lines until valid data is found
        line = fh.readline()
        parts = []
        while line:
            parts = line.split("\t")
            if len(parts) >= 5 and "(" in parts[3]:
                break
            line = fh.readline()

        if not line:
            raise ValueError("File contains no execution data.")

        # Determine node dimensions
        first_coords = parts[3].strip().replace("(", "").replace(")", "").split()
        dimensions = len(first_coords)

        # 2. Main parsing loop
        line_count = 0
        update_interval = 10000

        if progress_callback:
            progress_callback(1)

        while line:
            s = line.strip()
            if not s or s.startswith("P"):
                break

            parts = line.split("\t")
            if len(parts) >= 5 and "(" in parts[3]:
                try:
                    iter_id = int(parts[1])
                    coord = [
                        int(n) for n in parts[3].strip().replace("(", "").replace(")", "").split()
                    ]

                    vs = parts[4].strip()
                    if "g(" in vs:
                        vals = vs.split()
                        g_val = int(vals[0].replace("g(", "").replace(")", ""))
                        h_val = int(vals[1].replace("h(", "").replace(")", ""))
                        f_val = int(vals[2].replace("f(", "").replace(")", ""))
                    else:
                        clean = vs.replace("(", "").replace(")", "").split()
                        g_val = int(clean[2])
                        h_val = int(clean[5])
                        f_val = int(clean[8])

                    iterations.append(iter_id)
                    coords_list.append(coord)
                    g_list.append(g_val)
                    h_list.append(h_val)
                    f_list.append(f_val)
                except (IndexError, ValueError):
                    pass

            line_count += 1
            if progress_callback and line_count % update_interval == 0:
                pct = max(1, min(99, int(fh.tell() / max(file_size, 1) * 100)))
                progress_callback(pct)

            line = fh.readline()

    if progress_callback:
        progress_callback(100)

    if not iterations:
        raise ValueError("No valid data entries were parsed from the file.")

    # Convert to contiguous NumPy arrays
    iters_arr = np.array(iterations, dtype=np.int32)
    coords_arr = np.array(coords_list, dtype=np.int32)
    g_arr = np.array(g_list, dtype=np.int32)
    h_arr = np.array(h_list, dtype=np.int32)
    f_arr = np.array(f_list, dtype=np.int32)

    # Sort by iteration ID
    sort_idx = np.argsort(iters_arr)
    iters_arr = iters_arr[sort_idx]
    coords_arr = coords_arr[sort_idx]
    g_arr = g_arr[sort_idx]
    h_arr = h_arr[sort_idx]
    f_arr = f_arr[sort_idx]

    # Vectorized band deviation calculation: distance from diagonal (i = j = k = ...)
    mean_coords = np.mean(coords_arr, axis=1, keepdims=True)
    dev_arr = np.sqrt(np.sum((coords_arr - mean_coords) ** 2, axis=1, dtype=np.float64)).astype(
        np.float32
    )

    # Vectorized Manhattan displacement calculation
    if len(coords_arr) > 1:
        diffs = np.abs(np.diff(coords_arr, axis=0))
        jump_mask = np.max(diffs, axis=1) > 1
        num_jumps = int(np.sum(jump_mask))
        jump_distances = np.sum(diffs[jump_mask], axis=1, dtype=np.int32)
        jump_indices = np.where(jump_mask)[0]
    else:
        num_jumps = 0
        jump_distances = np.array([], dtype=np.int32)
        jump_indices = np.array([], dtype=np.int32)

    return {
        "iterations": iters_arr,
        "coords": coords_arr,
        "g": g_arr,
        "h": h_arr,
        "f": f_arr,
        "dimensions": dimensions,
        "dev": dev_arr,
        "num_jumps": num_jumps,
        "jump_distances": jump_distances,
        "jump_indices": jump_indices,
    }
