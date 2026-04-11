import os
import shutil
import subprocess
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path


if os.environ.get("PADDLE_SUPPRESS_WARNINGS") != "1":
    os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"
    result = subprocess.run([sys.executable] + sys.argv, env=os.environ)
    raise SystemExit(result.returncode)

warnings.filterwarnings("ignore", category=UserWarning)

import cv2
import pandas as pd
import re
from paddleocr import PaddleOCR
from pyzbar import pyzbar
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ImageHandler(FileSystemEventHandler):
    """监听新增图片，并自动完成 OCR 与码识别。"""

    def __init__(self, ocr_engine, processed_dir, error_dir):
        super().__init__()
        self.ocr = ocr_engine
        self.processed_path = Path(processed_dir)
        self.error_path = Path(error_dir)
        self.processed_path.mkdir(parents=True, exist_ok=True)
        self.error_path.mkdir(parents=True, exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            return

        print(f"[{datetime.now()}] 检测到新图片: {file_path.name}")
        success = self.process_image(file_path)

        if success:
            dest_file = self.processed_path / file_path.name
            print(f"  -> 识别成功，移动到: {dest_file}")
        else:
            dest_file = self.error_path / file_path.name
            print(f"  -> 识别失败或效果差，移动到异常文件夹: {dest_file}")

        try:
            shutil.move(str(file_path), str(dest_file))
        except Exception as move_error:
            print(f"  -> 移动文件时发生错误: {move_error}")

    def process_image(self, image_path):
        try:
            print("    正在进行 OCR 识别...")
            ocr_result = self.ocr.ocr(str(image_path))

            all_ocr_texts = []
            all_ocr_scores = []
            if isinstance(ocr_result, list) and len(ocr_result) > 0 and ocr_result[0] is not None:
                for item in ocr_result[0]:
                    if not isinstance(item, (list, tuple)) or len(item) < 2:
                        continue
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        all_ocr_texts.append(text_info[0])
                        all_ocr_scores.append(text_info[1])

            print("    正在进行码识别...")
            image_cv = cv2.imread(str(image_path))
            if image_cv is None:
                print(f"    -> 无法读取图片文件: {image_path}")
                return False

            decoded_objects = pyzbar.decode(image_cv)

            print("    正在提取并格式化数据...")
            extracted_ocr_data = self.extract_data_from_ocr(all_ocr_texts)
            extracted_codes_data = self.get_codes_data(decoded_objects)
            self.format_and_print_results(
                all_ocr_texts,
                extracted_ocr_data,
                extracted_codes_data,
                image_path.name,
            )

            ocr_success = len(all_ocr_texts) > 0
            code_success = len(decoded_objects) > 0
            min_confidence_threshold = 0.5
            has_low_confidence = any(score < min_confidence_threshold for score in all_ocr_scores)

            if ocr_success or code_success:
                if has_low_confidence:
                    print("    -> 识别完成，但检测到低置信度结果。")
                return True

            print("    -> 未识别到任何文字或码，视为异常。")
            return False
        except Exception as error:
            print(f"    -> 处理图片 {image_path.name} 时发生错误: {error}")
            return False

    def extract_data_from_ocr(self, ocr_texts):
        """从 OCR 结果中提取简单字段。"""
        extracted_data = {
            "物料编码": "",
            "批次号": "",
            "数量": "",
            "备注": "",
        }

        for text in ocr_texts:
            if "LOT.NO." in text.upper():
                match = re.search(r"Lot\.No\.\s*(.+)", text, re.IGNORECASE)
                if match:
                    extracted_data["批次号"] = match.group(1).strip()
            elif "QTY" in text.upper():
                match = re.search(r"QTY\.?\s*(\d+)", text, re.IGNORECASE)
                if match:
                    extracted_data["数量"] = match.group(1).strip()
            elif not extracted_data["物料编码"] and re.match(r"^[A-Z0-9]{8,}$", text):
                extracted_data["物料编码"] = text
            elif "pcs" in text.lower() or "rohs" in text.lower():
                if extracted_data["备注"]:
                    extracted_data["备注"] += f"; {text}"
                else:
                    extracted_data["备注"] = text

        return extracted_data

    def get_codes_data(self, decoded_objects):
        """从识别到的条码/二维码对象中提取信息。"""
        codes_info = []
        for obj in decoded_objects:
            try:
                data = obj.data.decode("utf-8")
            except UnicodeDecodeError:
                data = obj.data.decode("utf-8", errors="replace")
            codes_info.append({
                "类型": obj.type,
                "数据": data,
            })
        return codes_info

    def format_and_print_results(self, raw_ocr_texts, ocr_data, codes_data, filename):
        """格式化输出识别结果。"""
        print(f"\n--- 开始处理文件: {filename} ---")

        print("--- OCR 原始文本 ---")
        if raw_ocr_texts:
            for text in raw_ocr_texts:
                print(f"  - {text}")
        else:
            print("未识别到任何原始文本。")

        ocr_df = pd.DataFrame([ocr_data])
        print("--- OCR 提取数据 ---")
        print(ocr_df.to_string(index=False))

        if codes_data:
            codes_df = pd.DataFrame(codes_data)
            print("\n--- 码识别数据 ---")
            print(codes_df.to_string(index=False))
        else:
            print("\n--- 码识别数据 ---")
            print("未识别到任何码。")

        print(f"--- {filename} 处理完毕 ---\n")


def main():
    print("=== 启动物料图片自动识别流水线 ===")

    watch_directory = r"E:\Mr.6_Auto_OCR_PipelineWithCodeX\watch_directory"
    processed_directory = r"E:\Mr.6_Auto_OCR_PipelineWithCodeX\processed_directory"
    error_directory = r"E:\Mr.6_Auto_OCR_PipelineWithCodeX\error_directory"

    Path(watch_directory).mkdir(parents=True, exist_ok=True)
    Path(processed_directory).mkdir(parents=True, exist_ok=True)
    Path(error_directory).mkdir(parents=True, exist_ok=True)

    print("正在加载 OCR 模型...")
    ocr = PaddleOCR(lang="ch", use_gpu=False)
    print("OCR 模型加载完成。")

    event_handler = ImageHandler(ocr, processed_directory, error_directory)

    observer = Observer()
    observer.schedule(event_handler, watch_directory, recursive=False)
    observer.start()

    print(f"开始监控文件夹: {watch_directory}")
    print("请将图片放入该文件夹以触发自动识别。按 Ctrl+C 停止程序。")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n接收到停止信号，正在关闭...")

    observer.join()
    print("流水线已停止。")


if __name__ == "__main__":
    main()
    warnings.filterwarnings("default")
    print("\n--- 程序结束 ---")
