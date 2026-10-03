from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMainWindow, QMessageBox,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QListWidget,
    QListWidgetItem, QProgressBar
)

from core.watermark import clean_pdf


APP_NAME = "PDF 水印清理"


class Worker(QThread):
    done = pyqtSignal(str, str, int, int)  # input, output, blocks, annots
    failed = pyqtSignal(str, str)
    progress = pyqtSignal(int, int)

    def __init__(self, files: list[str]):
        super().__init__()
        self.files = files

    def run(self):
        total = len(self.files)
        for i, path in enumerate(self.files, 1):
            try:
                result = clean_pdf(path)
                self.done.emit(path, str(result.output_path), result.removed_blocks, result.watermark_annotations_removed)
            except Exception as e:
                self.failed.emit(path, str(e))
            self.progress.emit(i, total)


class DropArea(QLabel):
    filesDropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(240)
        self.setText("把 PDF 拖到这里\n\n松手后自动处理")
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #2997ff;
                border-radius: 22px;
                background: #eef7ff;
                color: #34495e;
                font-size: 24px;
                font-weight: 600;
                padding: 24px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith('.pdf') for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(820, 650)
        self.worker = None
        self.last_outputs: list[str] = []

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)

        title = QLabel("PDF 水印一键清理")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(28)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        subtitle = QLabel("本地处理，不上传文件。适合 PDF 中标准 Watermark / Artifact 水印。")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color:#657786;font-size:14px;")
        layout.addWidget(subtitle)

        self.drop = DropArea()
        self.drop.filesDropped.connect(self.process_files)
        layout.addWidget(self.drop)

        row = QHBoxLayout()
        self.pick_btn = QPushButton("选择 PDF 并处理")
        self.pick_btn.setMinimumHeight(44)
        self.pick_btn.clicked.connect(self.pick_files)
        row.addWidget(self.pick_btn)

        self.finder_btn = QPushButton("在 Finder 中显示结果")
        self.finder_btn.setMinimumHeight(44)
        self.finder_btn.setEnabled(False)
        self.finder_btn.clicked.connect(self.reveal_last)
        row.addWidget(self.finder_btn)
        layout.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)

        note = QLabel("输出文件默认保存在原 PDF 同一文件夹，文件名追加 _clean。原文件不会被覆盖。")
        note.setStyleSheet("color:#6b7280;font-size:13px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.setCentralWidget(root)

    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 PDF", "", "PDF Files (*.pdf)")
        if files:
            self.process_files(files)

    def process_files(self, files: list[str]):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, APP_NAME, "正在处理上一批文件，请稍等。")
            return
        files = [f for f in files if f.lower().endswith('.pdf')]
        if not files:
            return
        self.list.clear()
        self.last_outputs.clear()
        self.progress.setVisible(True)
        self.progress.setRange(0, len(files))
        self.progress.setValue(0)
        self.pick_btn.setEnabled(False)
        self.drop.setText("处理中…")

        self.worker = Worker(files)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_done(self, inp: str, out: str, blocks: int, annots: int):
        name = Path(inp).name
        removed = blocks + annots
        if removed:
            text = f"✅ {name}\n已移除 {removed} 个水印对象 → {Path(out).name}"
        else:
            text = f"⚠️ {name}\n未检测到标准 Watermark 标记；已生成副本 → {Path(out).name}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, out)
        self.list.addItem(item)
        self.last_outputs.append(out)

    def on_failed(self, inp: str, err: str):
        self.list.addItem(QListWidgetItem(f"❌ {Path(inp).name}\n{err}"))

    def on_progress(self, done: int, total: int):
        self.progress.setValue(done)

    def on_finished(self):
        self.pick_btn.setEnabled(True)
        self.finder_btn.setEnabled(bool(self.last_outputs))
        self.drop.setText("把 PDF 拖到这里\n\n松手后自动处理")
        if self.last_outputs:
            self.statusBar().showMessage("处理完成", 5000)

    def reveal_last(self):
        if not self.last_outputs:
            return
        path = self.last_outputs[-1]
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", "/select,", path], check=False)
        else:
            subprocess.run(["xdg-open", str(Path(path).parent)], check=False)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    w = MainWindow()
    w.show()

    # Also support dropping PDFs onto the app icon in Finder / Dock.
    args = [a for a in sys.argv[1:] if a.lower().endswith('.pdf')]
    if args:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(250, lambda: w.process_files(args))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
