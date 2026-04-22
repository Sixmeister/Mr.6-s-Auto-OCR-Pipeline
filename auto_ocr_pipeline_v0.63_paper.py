import sys

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox

from paper_capture_utils import load_script_module, tune_layout_tree


base_gui = load_script_module(__file__, "auto_ocr_pipeline_v0.63.py", "auto_ocr_pipeline_v0_63_base")


class PaperCaptureWindow(base_gui.MainWindow):
    """Screenshot-friendly wrapper for the detector-integrated v0.63 GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mr.6 Auto Ocr Pipeline v0.63 (label_det_m_45e) - Paper Capture")
        self.resize(1400, 980)
        self.setMinimumSize(1280, 900)
        self._apply_paper_capture_tuning()

    def _apply_paper_capture_tuning(self):
        tune_layout_tree(self.centralWidget().layout(), margins=(22, 18, 22, 18), spacing=12)

        body_font = QFont("Microsoft YaHei", 10)
        title_font = QFont("Microsoft YaHei", 11)
        title_font.setBold(True)

        top_labels = [
            getattr(self, "output_dir_label", None),
            getattr(self, "visual_output_dir_label", None),
            getattr(self, "txt_output_dir_label", None),
            getattr(self, "truth_csv_label", None),
            getattr(self, "test_record_csv_label", None),
        ]

        browse_buttons = [
            getattr(self, "browse_output_dir_btn", None),
            getattr(self, "browse_visual_output_dir_btn", None),
            getattr(self, "browse_txt_output_dir_btn", None),
            getattr(self, "browse_truth_csv_btn", None),
            getattr(self, "browse_test_record_csv_btn", None),
        ]

        for label in self.findChildren(QLabel):
            text = label.text().strip()
            if text in {
                "\u5168\u5c40\u8bbe\u7f6e",
                "\u8f93\u51fa",
                "\u5f53\u524d\u6a21\u5f0f: \u5355\u6b21\u8bc6\u522b",
                "\u5f53\u524d\u6a21\u5f0f: \u5b9e\u65f6\u76d1\u63a7",
            }:
                label.setFont(title_font)
            else:
                label.setFont(body_font)

        for label in top_labels:
            if label is not None:
                label.setFixedWidth(118)
                label.setFont(body_font)

        for line_edit in self.findChildren(QLineEdit):
            line_edit.setFont(body_font)
            line_edit.setMinimumHeight(38)

        for button in self.findChildren(QPushButton):
            button.setFont(body_font)
            button.setMinimumHeight(38)

        for button in browse_buttons:
            if button is not None:
                button.setFixedWidth(82)

        self.result_display.setFont(QFont("Consolas", 10))
        self.result_display.setMinimumHeight(420)

        self.setStyleSheet(self.styleSheet() + """
            QWidget {
                font-size: 10pt;
            }
            QGroupBox {
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QTextEdit {
                padding: 6px 8px;
            }
            QPushButton {
                padding: 6px 10px;
            }
        """)

    def apply_modern_theme(self):
        # v0.63 should stay visually closer to the earlier v0.5-era GUI.
        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI";
                font-size: 10pt;
                background: #f5f5f5;
                color: #202020;
            }
            QGroupBox {
                background: #f5f5f5;
                font-weight: bold;
                border: 1px solid #cfcfcf;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            QLineEdit, QTextEdit {
                background: white;
                border: 1px solid #bcbcbc;
                border-radius: 0px;
                padding: 6px 8px;
            }
            QPushButton {
                background: #f7f7f7;
                border: 1px solid #bcbcbc;
                border-radius: 2px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: #eeeeee;
            }
        """)

    def update_output_mode_label_style(self):
        self.output_mode_label.setStyleSheet(
            "font-weight: bold; color: green;" if self.manual_output
            else "font-weight: bold; color: orange;"
        )

    def update_mode_label_style(self):
        self.mode_label.setStyleSheet("font-weight: bold; color: blue;")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = PaperCaptureWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
