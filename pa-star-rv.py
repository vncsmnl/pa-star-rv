"""
PA-Star Runtime Visualizer
Modern High-Performance Log Visualizer using PyQt6 & PyQtGraph OpenGL
"""

import os
import sys

try:
    import pyqtgraph as pg
    from PyQt6.QtCore import QObject, QThread, pyqtSignal
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    import pyqtgraph as pg
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
        QProgressBar,
        QPushButton,
        QRadioButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

from parser import parse_log_file
from widgets.canvas_3d import Canvas3D
from widgets.canvas_band import CanvasBand
from widgets.canvas_comparison import CanvasComparison
from widgets.canvas_density import CanvasDensity
from widgets.canvas_dynamics import CanvasDynamics
from widgets.canvas_footprint import CanvasFootprint

# ─────────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────────

P = {
    "a": "#1f77b4",  # blue — A
    "b": "#d62728",  # red — B
    "warn": "#ff7f0e",
}

TAB_DEFS = [
    ("classic", "3D + Projections"),
    ("density", "Exploration Density"),
    ("dynamics", "Search Dynamics"),
    ("band", "Band Deviation"),
    ("footprint", "Search Footprint"),
    ("compare", "Comparison"),
]


# ─────────────────────────────────────────────
#  PARSER WORKER THREAD
# ─────────────────────────────────────────────


class LogParseWorker(QObject):
    """Background thread worker for fast log parsing."""

    done = pyqtSignal(str, object)  # (side, parsed_data)
    error = pyqtSignal(str, str)  # (side, error_message)
    progress = pyqtSignal(int)  # 0..100 percentage
    status = pyqtSignal(str)

    def __init__(self, filepath, side):
        super().__init__()
        self.filepath = filepath
        self.side = side

    def run(self):
        name = os.path.basename(self.filepath)
        self.status.emit(f"Parsing {name}…")
        try:
            data = parse_log_file(
                self.filepath, progress_callback=lambda p: self.progress.emit(p)
            )
            self.done.emit(self.side, data)
        except (
            AttributeError,
            KeyError,
            IndexError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as e:
            self.error.emit(self.side, str(e))


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PA-Star Runtime Visualizer — PyQt6 High Performance")
        self.resize(1400, 950)

        self.data_a = None
        self.label_a = "A"
        self.data_b = None
        self.label_b = "B"
        self.showing = "a"  # which file single-file tabs display

        self._jobs = []
        self._canvases = {}

        self._build_ui()

    # ── UI ───────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(6)
        root_layout.setContentsMargins(10, 8, 10, 6)

        # Button bar
        btn_row = QHBoxLayout()

        def mkbtn(text, color, slot):
            b = QPushButton(text)
            b.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:white;border:none;"
                f"padding:7px 16px;border-radius:4px;}}"
                f"QPushButton:hover{{background:{color};opacity:0.85;}}"
            )
            b.clicked.connect(slot)
            return b

        btn_row.addWidget(mkbtn("📂 Open Log A", P["a"], self.open_a))
        btn_row.addWidget(mkbtn("📂 Open Log B", P["b"], self.open_b))
        btn_row.addSpacing(20)
        btn_row.addWidget(mkbtn("💾 Save Current Tab", "#555555", self.save_current))
        btn_row.addWidget(mkbtn("💾 Export All Tabs", "#333333", self.export_all))
        btn_row.addStretch()
        root_layout.addLayout(btn_row)

        # File labels
        lbl_row = QHBoxLayout()
        self.lbl_a = QLabel("A: —")
        self.lbl_a.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_a.setStyleSheet(f"color:{P['a']}")
        self.lbl_b = QLabel("B: —")
        self.lbl_b.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_b.setStyleSheet(f"color:{P['b']}")
        lbl_row.addWidget(self.lbl_a)
        lbl_row.addSpacing(30)
        lbl_row.addWidget(self.lbl_b)
        lbl_row.addStretch()
        root_layout.addLayout(lbl_row)

        # A/B Switcher
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
        self.rb_b.toggled.connect(self._on_switch)
        sw_row.addWidget(self.rb_a)
        sw_row.addWidget(self.rb_b)
        sw_row.addStretch()
        root_layout.addLayout(sw_row)

        # Status & Progress bar
        status_row = QHBoxLayout()
        self.status_lbl = QLabel("Open a log file to begin.")
        self.status_lbl.setFont(QFont("Segoe UI", 9))
        self.status_lbl.setStyleSheet("color:#444444")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(220)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)

        status_row.addWidget(self.status_lbl)
        status_row.addSpacing(15)
        status_row.addWidget(self.progress_bar)
        status_row.addStretch()
        root_layout.addLayout(status_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 10))
        root_layout.addWidget(self.tabs)

        # Instantiate fast PyQtGraph canvases
        self._canvases["classic"] = Canvas3D()
        self._canvases["density"] = CanvasDensity()
        self._canvases["dynamics"] = CanvasDynamics()
        self._canvases["band"] = CanvasBand()
        self._canvases["footprint"] = CanvasFootprint()
        self._canvases["compare"] = CanvasComparison()

        for key, label in TAB_DEFS:
            self.tabs.addTab(self._canvases[key], label)

        self.tabs.currentChanged.connect(lambda _: self._update_active_tab())

    # ── Helpers ──────────────────────────────

    def _status(self, msg):
        self.status_lbl.setText(msg)

    def _on_progress(self, pct, name):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(f"Loading {name}… {pct}%")

    def _status_ready(self):
        parts = []
        if self.data_a:
            parts.append(
                f"A: {self.label_a} ({len(self.data_a['iterations']):,} nodes / {self.data_a['num_jumps']:,} jumps)"
            )
        if self.data_b:
            parts.append(
                f"B: {self.label_b} ({len(self.data_b['iterations']):,} nodes / {self.data_b['num_jumps']:,} jumps)"
            )
        self._status("   ·   ".join(parts) if parts else "Ready.")

    def _single_data(self):
        if self.showing == "b" and self.data_b is not None:
            return self.data_b, self.label_b
        if self.data_a is not None:
            return self.data_a, self.label_a
        return self.data_b, self.label_b

    def _update_active_tab(self):
        idx = self.tabs.currentIndex()
        if idx < 0 or idx >= len(TAB_DEFS):
            return
        key = TAB_DEFS[idx][0]
        if key in ("classic", "density", "dynamics", "band"):
            d, l = self._single_data()
            if d is not None:
                self._canvases[key].set_data(d, l)
        elif key in ("footprint", "compare"):
            if self.data_a and self.data_b:
                self._canvases[key].set_data(
                    self.data_a, self.data_b, self.label_a, self.label_b
                )

    # ── File Loading & Rendering ──────────────

    def _cleanup_job(self, job):
        if job in self._jobs:
            self._jobs.remove(job)

    def _load(self, fp, side):
        name = os.path.basename(fp)
        self._status(f"Loading {name}… 0%")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        thread = QThread()
        worker = LogParseWorker(fp, side)
        worker.moveToThread(thread)

        job = (thread, worker)
        self._jobs.append(job)

        thread.started.connect(worker.run)
        worker.status.connect(self._status)
        worker.progress.connect(lambda p: self._on_progress(p, name))
        worker.done.connect(lambda s, d: self._on_parse_done(s, d, name, job))
        worker.error.connect(lambda s, msg: self._on_parse_error(s, msg, job))

        worker.done.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        thread.start()

    def _on_parse_done(self, side, data, name, job):
        self._cleanup_job(job)
        self.progress_bar.setVisible(False)
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

        self._update_active_tab()
        self._status_ready()

    def _on_parse_error(self, side, msg, job):
        self._cleanup_job(job)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Failed to load file:\n{msg}")
        self._status("Error loading file.")

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
        self._update_active_tab()

    # ── Export ────────────────────────────────

    def save_current(self):
        idx = self.tabs.currentIndex()
        key = TAB_DEFS[idx][0]
        canvas_widget = self._canvases[key]

        fp, _ = QFileDialog.getSaveFileName(
            self,
            "Save Current Tab",
            "",
            "PNG Image (*.png);;All Files (*)",
        )
        if not fp:
            return

        try:
            pixmap = canvas_widget.grab()
            pixmap.save(fp, "PNG")
            QMessageBox.information(self, "Saved", f"Saved tab image:\n{fp}")
        except (
            AttributeError,
            KeyError,
            IndexError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as e:
            QMessageBox.critical(self, "Error", f"Save failed:\n{e}")

    def export_all(self):
        has_any = (self.data_a is not None) or (self.data_b is not None)
        if not has_any:
            QMessageBox.warning(self, "Warning", "No log files loaded yet.")
            return

        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Export All Tabs"
        )
        if not folder:
            return

        parts = []
        if self.data_a:
            parts.append(os.path.splitext(self.label_a)[0])
        if self.data_b:
            parts.append(os.path.splitext(self.label_b)[0])
        prefix = "_vs_".join(parts) if parts else "pastar"

        saved_files = []
        failed = []
        d_single, l_single = self._single_data()
        for key, _ in TAB_DEFS:
            canvas_widget = self._canvases[key]
            if key in ("classic", "density", "dynamics", "band") and d_single is not None:
                canvas_widget.set_data(d_single, l_single)
            elif key in ("footprint", "compare") and self.data_a and self.data_b:
                canvas_widget.set_data(
                    self.data_a, self.data_b, self.label_a, self.label_b
                )

            filename = f"{prefix}__{key}.png"
            filepath = os.path.join(folder, filename)
            try:
                pixmap = canvas_widget.grab()
                pixmap.save(filepath, "PNG")
                saved_files.append(filename)
            except (
                AttributeError,
                KeyError,
                IndexError,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as e:
                failed.append(f"{key}: {e}")

        msg = f"Exported {len(saved_files)} image(s) to:\n{folder}"
        if saved_files:
            msg += "\n\n" + "\n".join(saved_files)
        if failed:
            msg += "\n\nFailed:\n" + "\n".join(failed)
        QMessageBox.information(self, "Export Complete", msg)

    def closeEvent(self, event):
        for thread, worker in self._jobs:
            if thread.isRunning():
                thread.quit()
                thread.wait(500)
        event.accept()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────


def main():
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec() if hasattr(app, "exec") else app.exec_())


if __name__ == "__main__":
    main()
