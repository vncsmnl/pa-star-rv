import matplotlib.pyplot as plt
import sys
import os


def process_log_file(filepath):
    iterations = []
    f_values = []

    # Unused but parsed as per original logic
    g_values = []
    h_values = []

    try:
        with open(filepath, "r") as file:
            # Skip headers (first 5 lines)
            for _ in range(5):
                file.readline()

            line = file.readline()  # First data line

            # Process lines until file ends or Phase 2 starts
            while line:
                parts = line.split("\t")

                # Check if line is valid data or if 'Phase' (P) starts
                if len(parts) < 5 or (parts[0].strip() and parts[0][0] == "P"):
                    break

                # Extract iteration number
                try:
                    current_iter = int(parts[1])
                except (ValueError, IndexError):
                    line = file.readline()
                    continue

                # Extract costs (g, h, f)
                # Format expected: "g(90) h(6913) f(7003)"
                costs_str = parts[4].strip()
                tokens = costs_str.replace(")", "").replace("(", " ").split()

                try:
                    # Token mapping: ['g', '90', 'h', '6913', 'f', '7003']
                    g_val = int(tokens[1])
                    h_val = int(tokens[3])
                    f_val = int(tokens[5])

                    iterations.append(current_iter)
                    f_values.append(f_val)
                    g_values.append(g_val)
                    h_values.append(h_val)
                except (ValueError, IndexError):
                    pass

                line = file.readline()

        return iterations, f_values

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None, None
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None, None


def main():
    # Thread configurations
    thread_counts = ["1", "2", "4", "8"]
    subplot_indices = [221, 222, 223, 224]
    titles = ["1 Thread", "2 Threads", "4 Threads", "8 Threads"]

    # CLI Argument handling
    if len(sys.argv) < 2:
        print("Usage: python script.py <directory_path> [min_y] [max_y]")
        sys.exit(1)

    directory = sys.argv[1]

    y_min, y_max = None, None
    if len(sys.argv) == 4:
        try:
            y_min = int(sys.argv[2])
            y_max = int(sys.argv[3])
        except ValueError:
            print("Error: Min and Max limits must be integers.")
            sys.exit(1)

    plt.figure(figsize=(12, 10))

    for i, thread_count in enumerate(thread_counts):
        filename = f"log{thread_count}.txt"
        filepath = os.path.join(directory, filename)

        iterations, f_vals = process_log_file(filepath)

        if iterations is None:
            sys.exit(1)

        # Sorting based on iteration number to ensure correct plotting order
        # Zipping, sorting, and unzipping
        if iterations:
            sorted_pairs = sorted(zip(iterations, f_vals))
            iterations, f_vals = zip(*sorted_pairs)

        ax = plt.subplot(subplot_indices[i])

        if y_min is not None and y_max is not None:
            ax.set_ylim(y_min, y_max)

        ax.set_title(titles[i])
        ax.plot(iterations, f_vals, 'y-', label='f-value')
        ax.set_xlabel("Iteration")
        ax.set_ylabel("F Value")
        ax.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
