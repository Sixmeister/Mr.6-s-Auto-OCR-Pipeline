import sys

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from paper_capture_utils import load_script_module, tune_layout_tree


base_gui = load_script_module(__file__, "auto_ocr_pipeline_v0.5.py", "auto_ocr_pipeline_v0_5_base")


class PaperCaptureWindow(base_gui.MainWindow):
    """Screenshot-friendly wrapper that keeps the early v0.5 style."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mr.6's Auto OCR Pipeline v0.5 - Paper Capture")
        self.resize(1380, 980)
        self.setMinimumSize(1260, 900)
        self._apply_paper_capture_tuning()

    def _apply_paper_capture_tuning(self):
        tune_layout_tree(self.centralWidget().layout(), margins=(22, 18, 22, 18), spacing=14)
        self._separate_output_section()

        body_font = QFont("Microsoft YaHei", 11)
        title_font = QFont("Microsoft YaHei", 13)
        title_font.setBold(True)

        section_titles = {"\u8f93\u51fa", "\u8bc6\u522b\u7ed3\u679c", "\u65e5\u5fd7\u4e0e\u7ed3\u679c"}
        for label in self.findChildren(QLabel):
            if label.text().strip() in section_titles:
                label.setFont(title_font)
            else:
                label.setFont(body_font)

        for line_edit in self.findChildren(QLineEdit):
            line_edit.setFont(body_font)
            line_edit.setMinimumHeight(38)

        for button in self.findChildren(QPushButton):
            button.setFont(body_font)
            button.setMinimumHeight(40)

        for text_edit in self.findChildren(QTextEdit):
            text_edit.setFont(body_font)

        self.result_display.setMinimumHeight(420)

        # Keep the simple early-stage feel: no full stylesheet rewrite.
        self.setStyleSheet(
            """
            QGroupBox {
                font-weight: bold;
            }
            QLineEdit, QTextEdit {
                padding: 6px;
            }
            """
        )

    def _separate_output_section(self):
        main_layout = self.centralWidget().layout()
        removed = []
        while main_layout.count() > 4:
            removed.append(main_layout.takeAt(main_layout.count() - 1))

        for item in removed:
            widget = item.widget()
            if widget and widget not in {self.result_display, self.save_manual_btn}:
                widget.deleteLater()

        output_group = QGroupBox("识别结果")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 18, 12, 12)
        output_layout.setSpacing(12)
        output_layout.addWidget(self.result_display)
        output_layout.addWidget(self.save_manual_btn)

        main_layout.addWidget(output_group, 1)


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 11))
    window = PaperCaptureWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
