import importlib.util
import os
import time
from pathlib import Path

import cv2

os.environ["PADDLE_SUPPRESS_WARNINGS"] = "1"


def _load_module():
    root = Path(__file__).resolve().parent
    module_path = root / "auto_ocr_pipeline_v0.5.py"
    spec = importlib.util.spec_from_file_location("auto_ocr_pipeline_v0_5", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _iter_truth(mod, csv_path):
    truth_map = mod.load_ground_truth_map(str(csv_path))
    for name in sorted(truth_map.keys()):
        yield name, truth_map[name]


def main():
    root = Path(__file__).resolve().parent
    mod = _load_module()

    image_dir = root / "multiple_labels_test_enhanced"
    truth_csv = image_dir / "truth.csv"
    out_csv = root / "v0_5_grouping_test_records_enhanced50.csv"

    truth_map = mod.load_ground_truth_map(str(truth_csv))
    ocr = mod.PaddleOCR(lang="ch", use_gpu=False)

    if out_csv.exists():
        out_csv.unlink()

    for image_name, _actual in _iter_truth(mod, truth_csv):
        image_path = image_dir / image_name
        start = time.perf_counter()
        try:
            image_cv = cv2.imread(str(image_path))
            if image_cv is None:
                raise ValueError(f"unable to read image: {image_path}")

            ocr_results = ocr.ocr(str(image_path))
            if not ocr_results:
                raise ValueError("OCR returned empty result")

            text_items = mod._extract_text_items_from_ocr_result(ocr_results)
            code_items = []
            for obj in mod.pyzbar.decode(image_cv):
                rect = obj.rect
                bbox = [rect.left, rect.top, rect.left + rect.width, rect.top + rect.height]
                code_items.append(
                    {
                        "type": "code",
                        "code_type": obj.type,
                        "data": obj.data.decode("utf-8"),
                        "bbox": bbox,
                    }
                )

            labels = mod._build_label_groups(text_items, code_items)
            elapsed = time.perf_counter() - start
            row = mod.build_grouping_test_record(image_name, len(labels), elapsed, truth_map, True)
            mod.append_grouping_test_record(str(out_csv), row)
        except Exception as e:
            elapsed = time.perf_counter() - start
            row = mod.build_grouping_test_record(image_name, 0, elapsed, truth_map, False, error=str(e))
            mod.append_grouping_test_record(str(out_csv), row)

    print(f"out_csv={out_csv}")


if __name__ == "__main__":
    main()
