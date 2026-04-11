import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

if os.environ.get("PADDLE_SUPPRESS_WARNINGS") != "1":
    os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"
    result = subprocess.run([sys.executable] + sys.argv, env=os.environ)
    raise SystemExit(result.returncode)

from paddleocr import PaddleOCR
from pyzbar import pyzbar
import cv2
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(r"E:\Mr.6_Auto_OCR_PipelineWithCodeX")
WATCH_DIR = BASE_DIR / "watch_directory"
PROCESSED_DIR = BASE_DIR / "processed_directory"
ERROR_DIR = BASE_DIR / "error_directory"
RESULT_DIR = BASE_DIR / "v0_2gui_results"
RECORDS_CSV = BASE_DIR / "v0_2gui_test_records.csv"

for folder in [WATCH_DIR, PROCESSED_DIR, ERROR_DIR, RESULT_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def create_ocr_engine():
    return PaddleOCR(lang="ch", use_gpu=False)


def run_ocr_and_codes(ocr, image_path):
    image_path = Path(image_path)
    start_time = time.perf_counter()
    result = {
        "success": False,
        "ocr_lines": [],
        "codes": [],
        "error": "",
        "image_path": str(image_path),
        "elapsed_seconds": 0.0,
        "ocr_valid": False,
        "code_valid": False,
    }

    try:
        ocr_result = ocr.ocr(str(image_path))
        ocr_lines = []
        if isinstance(ocr_result, list) and len(ocr_result) > 0 and ocr_result[0] is not None:
            for item in ocr_result[0]:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                text_info = item[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                    text = str(text_info[0]).strip()
                    if text:
                        ocr_lines.append(text)

        image_cv = cv2.imread(str(image_path))
        if image_cv is None:
            raise ValueError(f"无法读取图片文件: {image_path}")

        decoded_objects = pyzbar.decode(image_cv)
        codes = []
        for obj in decoded_objects:
            try:
                data = obj.data.decode("utf-8")
            except UnicodeDecodeError:
                data = obj.data.decode("utf-8", errors="replace")
            codes.append({"type": obj.type, "data": data})

        result["ocr_lines"] = ocr_lines
        result["codes"] = codes
        result["ocr_valid"] = bool(ocr_lines)
        result["code_valid"] = bool(codes)
        result["success"] = bool(ocr_lines or codes)
        return result
    except Exception as error:
        result["error"] = str(error)
        return result
    finally:
        result["elapsed_seconds"] = round(time.perf_counter() - start_time, 4)


def format_result_text(result):
    image_name = Path(result["image_path"]).name
    lines = [
        f"图片: {image_name}",
        f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"处理耗时: {result['elapsed_seconds']:.4f} s",
        f"OCR是否有效: {'是' if result['ocr_valid'] else '否'}",
        f"码识别是否成功: {'是' if result['code_valid'] else '否'}",
        "",
        "--- OCR 文本 ---",
    ]

    if result["ocr_lines"]:
        lines.extend([f"  - {line}" for line in result["ocr_lines"]])
    else:
        lines.append("  - 未识别到文本")

    lines.append("")
    lines.append("--- 码识别结果 ---")
    if result["codes"]:
        for code in result["codes"]:
            lines.append(f"  - [{code['type']}] {code['data']}")
    else:
        lines.append("  - 未识别到任何码")

    if result["error"]:
        lines.append("")
        lines.append(f"错误信息: {result['error']}")

    return "\n".join(lines)


def save_result_file(result, output_dir=RESULT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_name = Path(result["image_path"]).stem
    output_path = output_dir / f"{image_name}_识别结果.txt"
    output_path.write_text(format_result_text(result), encoding="utf-8")
    return output_path


def append_test_record(result, mode, record_path=RECORDS_CSV):
    record_path = Path(record_path)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "recorded_at",
        "mode",
        "image_name",
        "ocr_valid",
        "code_valid",
        "ocr_line_count",
        "code_count",
        "success",
        "elapsed_seconds",
        "error",
    ]
    write_header = not record_path.exists()
    with record_path.open("a", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": mode,
                "image_name": Path(result["image_path"]).name,
                "ocr_valid": "Yes" if result["ocr_valid"] else "No",
                "code_valid": "Yes" if result["code_valid"] else "No",
                "ocr_line_count": len(result["ocr_lines"]),
                "code_count": len(result["codes"]),
                "success": "Yes" if result["success"] else "No",
                "elapsed_seconds": f"{result['elapsed_seconds']:.4f}",
                "error": result["error"],
            }
        )
    return record_path


class SingleImageWorker(QThread):
    finished_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        self.log_signal.emit("正在加载 OCR 模型...")
        ocr = create_ocr_engine()
        self.log_signal.emit("正在执行 OCR 与码识别...")
        result = run_ocr_and_codes(ocr, self.image_path)
        self.finished_signal.emit(result)


class ImageHandler(FileSystemEventHandler):
    def __init__(self, ocr, processed_dir, error_dir, log_callback, result_callback):
        super().__init__()
        self.ocr = ocr
        self.processed_dir = Path(processed_dir)
        self.error_dir = Path(error_dir)
        self.log_callback = log_callback
        self.result_callback = result_callback

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() not in IMAGE_SUFFIXES:
            return

        self.log_callback(f"[{datetime.now()}] 检测到新图片: {file_path.name}")
        result = run_ocr_and_codes(self.ocr, file_path)
        self.result_callback(result)
        self.log_callback(f"  -> 处理耗时: {result['elapsed_seconds']:.4f} s")

        try:
            if result["success"]:
                destination = self.processed_dir / file_path.name
                file_path.replace(destination)
                self.log_callback(f"  -> 识别成功，已移动到: {destination}")
            else:
                destination = self.error_dir / file_path.name
                file_path.replace(destination)
                self.log_callback(f"  -> 识别失败，已移动到异常目录: {destination}")
        except Exception as error:
            self.log_callback(f"  -> 移动文件时发生错误: {error}")


class WatcherThread(QThread):
    log_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)

    def __init__(self, watch_dir, processed_dir, error_dir):
        super().__init__()
        self.watch_dir = str(watch_dir)
        self.processed_dir = str(processed_dir)
        self.error_dir = str(error_dir)
        self.observer = Observer()

    def run(self):
        ocr = create_ocr_engine()
        handler = ImageHandler(
            ocr,
            self.processed_dir,
            self.error_dir,
            self.log_signal.emit,
            self.result_signal.emit,
        )
        self.observer.schedule(handler, self.watch_dir, recursive=False)
        self.observer.start()
        self.log_signal.emit(f"开始监听文件夹: {self.watch_dir}")

        try:
            while not self.isInterruptionRequested():
                self.msleep(500)
        finally:
            self.observer.stop()
            self.observer.join()
            self.log_signal.emit("监听已停止。")

    def stop_watching(self):
        self.requestInterruption()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mr.6's Auto OCR Pipeline v0.2gui")
        self.setMinimumSize(860, 640)

        self.current_mode = "single"
        self.worker = None
        self.watcher_thread = None
        self.current_watch_dir = WATCH_DIR
        self.current_processed_dir = PROCESSED_DIR
        self.current_error_dir = ERROR_DIR

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        header_layout = QHBoxLayout()
        self.mode_label = QLabel("当前模式: 单次识别")
        self.toggle_mode_btn = QPushButton("切换为实时监听模式")
        self.toggle_mode_btn.clicked.connect(self.toggle_mode)
        header_layout.addWidget(self.mode_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_mode_btn)
        main_layout.addLayout(header_layout)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.select_btn = QPushButton("选择图片")
        self.select_btn.clicked.connect(self.select_image)
        path_layout.addWidget(QLabel("输入路径:"))
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.select_btn)
        main_layout.addLayout(path_layout)

        watch_layout = QHBoxLayout()
        self.watch_dir_edit = QLineEdit(str(self.current_watch_dir))
        self.watch_dir_edit.setReadOnly(True)
        self.watch_dir_btn = QPushButton("选择监听目录")
        self.watch_dir_btn.clicked.connect(self.select_watch_dir)
        watch_layout.addWidget(QLabel("监听目录:"))
        watch_layout.addWidget(self.watch_dir_edit)
        watch_layout.addWidget(self.watch_dir_btn)
        main_layout.addLayout(watch_layout)

        action_layout = QHBoxLayout()
        self.run_btn = QPushButton("开始识别")
        self.run_btn.clicked.connect(self.start_task)
        self.stop_btn = QPushButton("停止监听")
        self.stop_btn.clicked.connect(self.stop_watching)
        self.stop_btn.setEnabled(False)
        action_layout.addWidget(self.run_btn)
        action_layout.addWidget(self.stop_btn)
        main_layout.addLayout(action_layout)

        main_layout.addWidget(QLabel("识别结果"))
        self.result_display = QTextEdit()
        self.result_display.setReadOnly(True)
        main_layout.addWidget(self.result_display)

        main_layout.addWidget(QLabel("日志输出"))
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(180)
        main_layout.addWidget(self.log_display)

        self.update_mode_ui()

    def update_mode_ui(self):
        if self.current_mode == "single":
            self.mode_label.setText("当前模式: 单次识别")
            self.toggle_mode_btn.setText("切换为实时监听模式")
            self.select_btn.setEnabled(True)
            self.watch_dir_btn.setEnabled(False)
            self.run_btn.setText("开始识别")
            self.path_edit.setText("")
            self.path_edit.setPlaceholderText("请选择单张图片")
        else:
            self.mode_label.setText("当前模式: 实时监听")
            self.toggle_mode_btn.setText("切换为单次识别模式")
            self.select_btn.setEnabled(False)
            self.watch_dir_btn.setEnabled(True)
            self.run_btn.setText("开始监听")
            self.path_edit.setText(str(self.current_watch_dir))
            self.path_edit.setPlaceholderText("")
        self.watch_dir_edit.setText(str(self.current_watch_dir))

    def toggle_mode(self):
        if self.watcher_thread and self.watcher_thread.isRunning():
            QMessageBox.warning(self, "提示", "请先停止监听，再切换模式。")
            return

        self.current_mode = "watch" if self.current_mode == "single" else "single"
        self.update_mode_ui()
        self.log_message(f"模式已切换为: {'实时监听' if self.current_mode == 'watch' else '单次识别'}")

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            str(BASE_DIR),
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff)",
        )
        if file_path:
            self.path_edit.setText(file_path)
            self.log_message(f"已选择图片: {file_path}")

    def select_watch_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择监听目录",
            str(self.current_watch_dir),
        )
        if directory:
            self.current_watch_dir = Path(directory)
            self.current_watch_dir.mkdir(parents=True, exist_ok=True)
            self.current_processed_dir = self.current_watch_dir / "processed"
            self.current_error_dir = self.current_watch_dir / "error"
            self.current_processed_dir.mkdir(parents=True, exist_ok=True)
            self.current_error_dir.mkdir(parents=True, exist_ok=True)
            self.watch_dir_edit.setText(str(self.current_watch_dir))
            if self.current_mode == "watch":
                self.path_edit.setText(str(self.current_watch_dir))
            self.log_message(f"已选择监听目录: {self.current_watch_dir}")
            self.log_message(f"已处理目录: {self.current_processed_dir}")
            self.log_message(f"异常目录: {self.current_error_dir}")

    def start_task(self):
        if self.current_mode == "single":
            self.start_single_recognition()
        else:
            self.start_watching()

    def start_single_recognition(self):
        image_path = self.path_edit.text().strip()
        if not image_path:
            QMessageBox.warning(self, "提示", "请先选择一张图片。")
            return

        self.run_btn.setEnabled(False)
        self.worker = SingleImageWorker(image_path)
        self.worker.log_signal.connect(self.log_message)
        self.worker.finished_signal.connect(self.handle_single_result)
        self.worker.finished.connect(lambda: self.run_btn.setEnabled(True))
        self.worker.start()

    def handle_single_result(self, result):
        self.result_display.setPlainText(format_result_text(result))
        output_path = save_result_file(result, RESULT_DIR)
        record_path = append_test_record(result, mode="single")
        if result["success"]:
            self.log_message(f"识别完成，结果已保存至: {output_path}")
        else:
            self.log_message(f"识别失败，结果已保存至: {output_path}")
        self.log_message(f"测试记录已写入: {record_path}")

    def start_watching(self):
        if self.watcher_thread and self.watcher_thread.isRunning():
            QMessageBox.information(self, "提示", "监听已经在运行中。")
            return

        self.current_watch_dir.mkdir(parents=True, exist_ok=True)
        self.current_processed_dir.mkdir(parents=True, exist_ok=True)
        self.current_error_dir.mkdir(parents=True, exist_ok=True)

        self.watcher_thread = WatcherThread(
            self.current_watch_dir,
            self.current_processed_dir,
            self.current_error_dir,
        )
        self.watcher_thread.log_signal.connect(self.log_message)
        self.watcher_thread.result_signal.connect(self.handle_watch_result)
        self.watcher_thread.finished.connect(self.on_watch_finished)
        self.watcher_thread.start()

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_message(f"开始连续测试，请将图片放入: {self.current_watch_dir}")

    def stop_watching(self):
        if self.watcher_thread and self.watcher_thread.isRunning():
            self.watcher_thread.stop_watching()
            self.stop_btn.setEnabled(False)

    def on_watch_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def handle_watch_result(self, result):
        self.result_display.setPlainText(format_result_text(result))
        output_path = save_result_file(result, RESULT_DIR)
        record_path = append_test_record(result, mode="watch")
        self.log_message(f"识别结果已保存至: {output_path}")
        self.log_message(f"测试记录已写入: {record_path}")

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_display.append(f"[{timestamp}] {message}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
