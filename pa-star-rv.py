import matplotlib.pyplot as plt
import numpy as np
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def process_log_file(filepath):
    """Parses the log file and returns the necessary execution data."""
    try:
        with open(filepath, "r") as file:
            num_expansions = {}
            f_costs = {}
            g_costs = {}
            h_costs = {}
            jumps = []
            iterations = []
            avg_h_neighbors = {}

            # Skip headers
            # 1: PA-Star Execution Log, 2: Threads, 3: Hash, 4: Shift, 5: Empty
            for _ in range(5):
                file.readline()

            # Read first data line
            line = file.readline()

            # Skip empty lines until data is found
            while line and line.strip() == "":
                line = file.readline()

            if not line:
                messagebox.showerror("Error", "File contains no execution data.")
                return None

            parts = line.split("\t")

            # Determine vertex dimensions based on the first coordinate found
            dimensions = len(parts[3].strip().replace("(", "").replace(")", "").split())

            # Scan vertices
            while line:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("P"):
                    break

                parts = line.split("\t")
                coord_str = parts[3].strip()

                # Parse node coordinates
                node = coord_str.replace("(", "").replace(")", "").split()
                node = tuple(int(n) for n in node)

                iteration_id = int(parts[1])
                iterations.append((iteration_id, node))

                # Parse f, g, and h costs
                values_str = parts[4].strip()

                if "g(" in values_str:
                    # Format: g(90) h(82) f(172)
                    vals = values_str.split()
                    g_val = vals[0].replace("g(", "").replace(")", "")
                    h_val = vals[1].replace("h(", "").replace(")", "")
                    f_val = vals[2].replace("f(", "").replace(")", "")
                else:
                    # Format: g - 90 (h - 82 f - 172)
                    clean_str = values_str.replace("(", "").replace(")", "")
                    vals = clean_str.split()
                    # Index mapping based on split: "g", "-", "90", "h", "-", "82"...
                    g_val = vals[2]
                    h_val = vals[5]
                    f_val = vals[8]

                g_costs[node] = int(g_val)
                h_costs[node] = int(h_val)
                f_costs[node] = int(f_val)

                line = file.readline()

            iterations.sort()

            return {
                'num_expansions': num_expansions,
                'f': f_costs,
                'g': g_costs,
                'h': h_costs,
                'jumps': jumps,
                'num_jumps': 0,
                'iterations': iterations,
                'avg_h_neighbors': avg_h_neighbors,
                'dimensions': dimensions
            }

    except FileNotFoundError:
        messagebox.showerror("Error", "File not found.")
        return None
    except Exception as e:
        messagebox.showerror("Error", f"Failed to process file:\n{e}")
        return None


def get_neighbors(vertex, neighbor_list, index):
    """Recursively generates neighbors for a vertex."""
    if index <= 0:
        neighbor_list.append(vertex)
        new_vertex = list(vertex)
        new_vertex[index] += 1
        neighbor_list.append(tuple(new_vertex))

        if new_vertex[index] > 1:
            new_vertex[index] -= 2
            neighbor_list.append(tuple(new_vertex))
        return neighbor_list

    neighbor_list.append(vertex)
    neighbor_list = get_neighbors(vertex, neighbor_list.copy(), index - 1)

    new_vertex = list(vertex)
    new_vertex[index] += 1
    neighbor_list = get_neighbors(tuple(new_vertex), neighbor_list.copy(), index - 1)

    if new_vertex[index] > 1:
        new_vertex[index] -= 2
        neighbor_list = get_neighbors(tuple(new_vertex), neighbor_list.copy(), index - 1)

    return neighbor_list


def calculate_metrics(data):
    """Calculates additional metrics (jumps, neighbors) from processed data."""
    num_expansions = data['num_expansions']
    h_costs = data['h']
    iterations = data['iterations']
    jumps = data['jumps']
    avg_h_neighbors = data['avg_h_neighbors']
    dimensions = data['dimensions']

    index = dimensions - 1
    previous_node = None
    jump_count = 0

    for _, vertex in iterations:
        if vertex in num_expansions:
            num_expansions[vertex] += 1
        else:
            num_expansions[vertex] = 1

        neighbors = get_neighbors(vertex, [], index)
        neighbors = list(dict.fromkeys(neighbors))  # Remove duplicates
        if vertex in neighbors:
            neighbors.remove(vertex)

        if previous_node is not None:
            if previous_node not in neighbors:
                jump_count += 1
                jumps.append((previous_node, vertex))

        num_neighbors = 0
        total_h = 0
        for neighbor in neighbors:
            if neighbor in h_costs:
                total_h += h_costs[neighbor]
                num_neighbors += 1

        if num_neighbors == 0:
            avg_h_neighbors[vertex] = -1
        else:
            avg_h_neighbors[vertex] = total_h / num_neighbors

        previous_node = vertex

    data['num_jumps'] = jump_count
    return data


def generate_plot(data):
    """Generates the 3D visualization plot with 2D projections."""
    iterations = data['iterations']
    dimensions = data['dimensions']

    if dimensions > 3:
        messagebox.showinfo("Warning", f"File has {dimensions} dimensions. Only 3D graphs are supported.")
        return None

    x_vals = []
    y_vals = []
    z_vals = []
    times = []

    for timestamp, node in iterations:
        x_vals.append(node[0])
        y_vals.append(node[1])
        z_vals.append(node[2])
        times.append(timestamp)

    x_vals = np.array(x_vals)
    y_vals = np.array(y_vals)
    z_vals = np.array(z_vals)
    times = np.array(times)

    # Create figure with 2x2 grid: 3D plot + 3 projections
    fig = plt.figure(figsize=(14, 10))

    # Main 3D plot (top-left, larger)
    ax3d = fig.add_subplot(2, 2, 1, projection='3d')
    scatter3d = ax3d.scatter(x_vals, y_vals, z_vals, c=times, cmap='viridis', marker='o', s=10)
    ax3d.set_xlabel("Sequence A (i)")
    ax3d.set_ylabel("Sequence B (j)")
    ax3d.set_zlabel("Sequence C (k)")
    ax3d.set_title("3D View")

    # XY Projection (top-right)
    ax_xy = fig.add_subplot(2, 2, 2)
    scatter_xy = ax_xy.scatter(x_vals, y_vals, c=times, cmap='viridis', marker='o', s=10, alpha=0.7)
    ax_xy.set_xlabel("Sequence A (i)")
    ax_xy.set_ylabel("Sequence B (j)")
    ax_xy.set_title("XY Projection (Top View)")
    ax_xy.set_aspect('equal', adjustable='box')
    ax_xy.grid(True, linestyle='--', alpha=0.5)

    # Calculate and display band width for XY
    if len(x_vals) > 0:
        # Band width as perpendicular distance from diagonal
        diag_dist_xy = np.abs(x_vals - y_vals) / np.sqrt(2)
        band_width_xy = np.max(diag_dist_xy) - np.min(diag_dist_xy)
        ax_xy.text(0.02, 0.98, f"Band width: {band_width_xy:.1f}",
                   transform=ax_xy.transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # XZ Projection (bottom-left)
    ax_xz = fig.add_subplot(2, 2, 3)
    scatter_xz = ax_xz.scatter(x_vals, z_vals, c=times, cmap='viridis', marker='o', s=10, alpha=0.7)
    ax_xz.set_xlabel("Sequence A (i)")
    ax_xz.set_ylabel("Sequence C (k)")
    ax_xz.set_title("XZ Projection (Front View)")
    ax_xz.set_aspect('equal', adjustable='box')
    ax_xz.grid(True, linestyle='--', alpha=0.5)

    # Calculate and display band width for XZ
    if len(x_vals) > 0:
        diag_dist_xz = np.abs(x_vals - z_vals) / np.sqrt(2)
        band_width_xz = np.max(diag_dist_xz) - np.min(diag_dist_xz)
        ax_xz.text(0.02, 0.98, f"Band width: {band_width_xz:.1f}",
                   transform=ax_xz.transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # YZ Projection (bottom-right)
    ax_yz = fig.add_subplot(2, 2, 4)
    scatter_yz = ax_yz.scatter(y_vals, z_vals, c=times, cmap='viridis', marker='o', s=10, alpha=0.7)
    ax_yz.set_xlabel("Sequence B (j)")
    ax_yz.set_ylabel("Sequence C (k)")
    ax_yz.set_title("YZ Projection (Side View)")
    ax_yz.set_aspect('equal', adjustable='box')
    ax_yz.grid(True, linestyle='--', alpha=0.5)

    # Calculate and display band width for YZ
    if len(y_vals) > 0:
        diag_dist_yz = np.abs(y_vals - z_vals) / np.sqrt(2)
        band_width_yz = np.max(diag_dist_yz) - np.min(diag_dist_yz)
        ax_yz.text(0.02, 0.98, f"Band width: {band_width_yz:.1f}",
                   transform=ax_yz.transAxes, fontsize=9,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Add colorbar for the entire figure
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    colorbar = fig.colorbar(scatter3d, cax=cbar_ax)
    colorbar.set_label('Iteration')

    plt.tight_layout(rect=[0, 0, 0.90, 1])

    return fig


class PAStarGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PA-Star Runtime Visualizer")
        self.root.geometry("1200x900")

        self.data = None
        self.current_figure = None

        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.btn_open = tk.Button(button_frame, text="Open Log File",
                                  command=self.open_file,
                                  font=("Arial", 12),
                                  bg="#4CAF50", fg="white",
                                  padx=20, pady=10)
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.btn_save = tk.Button(button_frame, text="Save Image",
                                  command=self.save_image,
                                  font=("Arial", 12),
                                  bg="#2196F3", fg="white",
                                  padx=20, pady=10,
                                  state=tk.DISABLED)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.status_label = tk.Label(root, text="Waiting for file...", font=("Arial", 10))
        self.status_label.pack(pady=5)

        self.graph_frame = tk.Frame(root)
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def open_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Log File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )

        if not filepath:
            return

        self.status_label.config(text="Processing file...")
        self.root.update()

        raw_data = process_log_file(filepath)
        if raw_data is None:
            self.status_label.config(text="Error processing file")
            return

        processed_data = calculate_metrics(raw_data)
        self.data = processed_data

        fig = generate_plot(processed_data)
        if fig is None:
            self.status_label.config(text="Error generating graph")
            return

        self.current_figure = fig

        # Clear previous graph
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.btn_save.config(state=tk.NORMAL)

        num_iterations = len(processed_data['iterations'])
        num_jumps = processed_data['num_jumps']
        self.status_label.config(
            text=f"File processed! Iterations: {num_iterations} | Jumps: {num_jumps}"
        )

    def save_image(self):
        if self.current_figure is None:
            messagebox.showwarning("Warning", "No graph to save!")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Image As",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
                ("All Files", "*.*")
            ]
        )

        if not filepath:
            return

        try:
            self.current_figure.savefig(filepath, dpi=300, bbox_inches='tight')
            messagebox.showinfo("Success", f"Image saved at:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image:\n{e}")


def main():
    root = tk.Tk()
    app = PAStarGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
