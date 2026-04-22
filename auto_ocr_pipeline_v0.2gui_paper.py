import os
import sys
import importlib.util
from pathlib import Path

# Avoid triggering the relaunch logic in the original early-stage script.
os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


def _load_base_gui_module():
    script_path = Path(__file__).with_name("auto_ocr_pipeline_v0.2gui.py")
    spec = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_2gui_base", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base_gui = _load_base_gui_module()


class PaperCaptureWindow(base_gui.MainWindow):
    """A screenshot-friendly wrapper for the v0.2 GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mr.6's Auto OCR Pipeline v0.2gui - Paper Capture")
        self.resize(1460, 980)
        self.setMinimumSize(1320, 900)
        self._apply_paper_capture_tuning()

    def _apply_paper_capture_tuning(self):
        self._tune_layout(self.centralWidget().layout())
        self._separate_output_sections()

        title_font = QFont("Microsoft YaHei", 13)
        title_font.setBold(True)
        body_font = QFont("Microsoft YaHei", 11)
        body_font.setStyleHint(QFont.SansSerif)

        section_titles = {"\u8bc6\u522b\u7ed3\u679c", "\u65e5\u5fd7\u8f93\u51fa"}
        for label in self.findChildren(QLabel):
            text = label.text().strip()
            if text in section_titles:
                label.setFont(title_font)
            else:
                label.setFont(body_font)

        for line_edit in self.findChildren(QLineEdit):
            line_edit.setFont(body_font)

        for button in self.findChildren(QPushButton):
            button.setFont(body_font)

        for text_edit in self.findChildren(QTextEdit):
            text_edit.setFont(body_font)

        self.result_display.setMinimumHeight(430)
        self.log_display.setMinimumHeight(210)
        self.log_display.setMaximumHeight(250)

        if hasattr(self, "mode_label"):
            mode_font = QFont("Microsoft YaHei", 12)
            mode_font.setBold(True)
            self.mode_label.setFont(mode_font)

    def _separate_output_sections(self):
        main_layout = self.centralWidget().layout()
        removed_items = []

        while main_layout.count() > 4:
            removed_items.append(main_layout.takeAt(main_layout.count() - 1))

        for item in removed_items:
            widget = item.widget()
            if widget and widget not in {self.result_display, self.log_display}:
                widget.deleteLater()

        result_group = QGroupBox("识别结果")
        result_layout = QVBoxLayout(result_group)
        result_layout.setContentsMargins(12, 18, 12, 12)
        result_layout.addWidget(self.result_display)

        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 18, 12, 12)
        log_layout.addWidget(self.log_display)

        main_layout.addWidget(result_group, 3)
        main_layout.addWidget(log_group, 2)

    def _tune_layout(self, layout):
        if layout is None:
            return

        if isinstance(layout, QLayout):
            layout.setContentsMargins(24, 20, 24, 20)
            layout.setSpacing(16)

        for index in range(layout.count()):
            item = layout.itemAt(index)
            child_layout = item.layout()
            if child_layout is not None:
                self._tune_layout(child_layout)


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 11))
    window = PaperCaptureWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
