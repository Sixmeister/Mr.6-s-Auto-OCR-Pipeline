import os
import sys
import warnings
from pathlib import Path

# Ensure warning suppression also applies in the child process.
if os.environ.get('PADDLE_SUPPRESS_WARNINGS') != '1':
    os.environ['PADDLE_SUPPRESS_WARNINGS'] = '1'
    import subprocess
    result = subprocess.run([sys.executable] + sys.argv, env=os.environ)
    raise SystemExit(result.returncode)

warnings.filterwarnings('ignore', category=UserWarning)

from paddleocr import PaddleOCR
from pyzbar import pyzbar
import cv2


def test_ocr_and_codes():
    """验证单张图片上的 OCR 与码识别能力。"""
    print('=== 开始测试 PaddleOCR ===')

    # 在当前环境中强制使用 CPU，避免最早原型脚本依赖 GPU/CUDNN。
    ocr = PaddleOCR(lang='ch', use_gpu=False)

    test_image_path = Path(__file__).resolve().parent / 'test_image.jpg'
    print(f'正在识别图片: {test_image_path}')

    try:
        result = ocr.ocr(str(test_image_path))

        print('--- OCR 识别结果 ---')
        extracted_texts = []
        if isinstance(result, list) and len(result) > 0 and result[0] is not None:
            for item in result[0]:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                text_info = item[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                    text = text_info[0]
                    score = text_info[1]
                    print(f"  - 文本: '{text}', 置信度: {score:.2f}")
                    extracted_texts.append(text)
                else:
                    print(f'  - 无法解析的结果项: {item}')
        else:
            print('  - 未检测到任何文本或结果为空。')

        print(f"提取到的文本: {' '.join(extracted_texts)}")

    except FileNotFoundError:
        print(f'错误: 找不到图片文件 {test_image_path}')
        return
    except Exception as e:
        print(f'OCR 识别过程中发生错误: {e}')
        import traceback
        traceback.print_exc()
        return

    print('\n=== 开始测试 码识别 ===')

    image = cv2.imread(str(test_image_path))
    if image is None:
        print(f'错误: OpenCV 无法读取图片 {test_image_path}')
        return

    print('正在扫描图片中的码...')
    decoded_objects = pyzbar.decode(image)

    print('--- 码识别结果 ---')
    if not decoded_objects:
        print('  - 未在图片中找到任何条形码或二维码。')
    else:
        for obj in decoded_objects:
            data = obj.data.decode('utf-8', errors='replace')
            code_type = obj.type
            print(f'  - 类型: {code_type}, 数据: {data}')


if __name__ == '__main__':
    test_ocr_and_codes()

warnings.filterwarnings('default')
print('\n--- 程序执行完毕 ---')
