# -*- coding: utf-8 -*-
"""
Training Script for Invoice Layout Detector
Prepares YOLO datasets and trains the layout model used by the PebbleOCR pipeline.
"""
import csv
import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from config import LAYOUT_WEIGHTS_PATH, LAYOUT_METRICS_PATH


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / 'data'
GENERATED_DIR = DATA_DIR / 'generated_invoices'
LAYOUT_CLASSES = ['header', 'table', 'totals']

# Default training configuration; override via environment variables if needed
LAYOUT_TRAINING_CONFIG = {
    'enabled': os.getenv('LAYOUT_STAGE_ENABLED', '1') != '0',
    'rebuild_dataset': os.getenv('LAYOUT_REBUILD', '1') != '0',
    'base_model': os.getenv('LAYOUT_BASE_MODEL', 'yolov8n.pt'),
    'epochs': int(os.getenv('LAYOUT_EPOCHS', '40')), #debug this shit down to 1 to save weights and giggles 
    'batch_size': int(os.getenv('LAYOUT_BATCH', '8')),
    'image_size': int(os.getenv('LAYOUT_IMGSZ', '640')),
    'device': os.getenv('LAYOUT_DEVICE', 'auto'),
}


def _remove_dir_safely(path: Path):
    """Remove directory tree even if files are read-only (Windows friendly)."""

    def _onerror(func, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
        except OSError:
            pass
        func(target)

    shutil.rmtree(path, onerror=_onerror)


def _resolve_device(requested: Optional[str]) -> str:
    """Map 'auto' to an actual device string based on torch availability."""

    desired = (requested or 'auto').strip().lower()
    if desired != 'auto':
        return desired

    try:
        import torch  # pylint: disable=import-outside-toplevel

        if torch.cuda.is_available():
            return '0'
    except Exception:
        pass

    print("[PIPELINE] No CUDA device detected, forcing layout training to CPU.")
    return 'cpu'


@dataclass
class LayoutDatasetInfo:
    root: Path
    yaml_path: Path
    samples_per_split: Dict[str, int]
    class_names: List[str]


class LayoutDatasetBuilder:
    """Prepare YOLO-style dataset for invoice layout detection."""

    def __init__(self, dataset_root: Optional[Path] = None, class_names: Optional[List[str]] = None):
        self.dataset_root = dataset_root or (DATA_DIR / 'layout_dataset')
        self.class_names = class_names or LAYOUT_CLASSES

    def prepare(self, metadata_map: Dict[str, Path], rebuild: bool = False) -> LayoutDatasetInfo:
        if rebuild and self.dataset_root.exists():
            print(f"[LAYOUT] Rebuilding dataset at {self.dataset_root} ...")
            _remove_dir_safely(self.dataset_root)

        stats: Dict[str, int] = {}
        images_dir = self.dataset_root / 'images'
        labels_dir = self.dataset_root / 'labels'

        for split, metadata_path in metadata_map.items():
            if metadata_path is None:
                continue
            metadata_path = Path(metadata_path)
            if not metadata_path.exists():
                print(f"[LAYOUT] Skip {split}: metadata file missing at {metadata_path}")
                continue
            stats[split] = self._process_split(split, metadata_path, images_dir, labels_dir)

        yaml_path = self._write_yaml()
        return LayoutDatasetInfo(
            root=self.dataset_root,
            yaml_path=yaml_path,
            samples_per_split=stats,
            class_names=self.class_names,
        )

    def _process_split(self, split: str, metadata_path: Path, images_dir: Path, labels_dir: Path) -> int:
        with metadata_path.open('r', encoding='utf-8') as handle:
            records = json.load(handle)

        split_images = images_dir / split
        split_labels = labels_dir / split
        split_images.mkdir(parents=True, exist_ok=True)
        split_labels.mkdir(parents=True, exist_ok=True)

        processed = 0
        for record in records:
            rel_path = Path(record['image_path'])
            src_image = (ROOT_DIR / rel_path).resolve()
            if not src_image.exists():
                print(f"[LAYOUT] Missing image for {rel_path}, skipping")
                continue

            with Image.open(src_image) as img:
                width, height = img.size

            dst_image = split_images / src_image.name
            shutil.copy2(src_image, dst_image)

            boxes = self._generate_layout_boxes(width, height, record.get('num_products') or len(record.get('products', [])))
            if not boxes:
                continue

            label_lines = self._to_yolo_lines(boxes, width, height)
            if not label_lines:
                continue

            label_path = split_labels / f"{src_image.stem}.txt"
            with label_path.open('w', encoding='utf-8') as label_file:
                label_file.write('\n'.join(label_lines))

            processed += 1

        print(f"[LAYOUT] Prepared {processed} samples for split '{split}'")
        return processed

    def _generate_layout_boxes(self, width: int, height: int, num_products: int) -> List[Dict[str, int]]:
        num_products = max(1, num_products or 1)
        header_height = int(height * 0.18)
        table_height = int(height * min(0.62, 0.28 + 0.02 * num_products))
        totals_height = int(height * 0.12)

        # Ensure the table occupies the remaining band between header and totals.
        available = height - header_height - totals_height
        if table_height > available:
            table_height = max(available - int(height * 0.05), int(height * 0.25))

        if table_height <= 0:
            return []

        boxes = [
            {
                'name': 'header',
                'x': int(width * 0.05),
                'y': int(height * 0.02),
                'w': int(width * 0.9),
                'h': max(header_height, int(height * 0.12)),
            },
            {
                'name': 'table',
                'x': int(width * 0.035),
                'y': int(header_height + height * 0.02),
                'w': int(width * 0.93),
                'h': table_height,
            },
            {
                'name': 'totals',
                'x': int(width * 0.55),
                'y': max(height - totals_height - int(height * 0.03), header_height + table_height + 5),
                'w': int(width * 0.4),
                'h': max(totals_height, int(height * 0.1)),
            },
        ]
        return boxes

    def _to_yolo_lines(self, boxes: List[Dict[str, int]], width: int, height: int) -> List[str]:
        lines: List[str] = []
        for box in boxes:
            if box['name'] not in self.class_names:
                continue
            cls_idx = self.class_names.index(box['name'])
            x_center = (box['x'] + box['w'] / 2) / width
            y_center = (box['y'] + box['h'] / 2) / height
            w_norm = box['w'] / width
            h_norm = box['h'] / height

            clip = lambda v: max(0.0, min(1.0, v))
            x_center = clip(x_center)
            y_center = clip(y_center)
            w_norm = clip(w_norm)
            h_norm = clip(h_norm)

            if w_norm <= 0 or h_norm <= 0:
                continue

            lines.append(f"{cls_idx} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

        return lines

    def _write_yaml(self) -> Path:
        yaml_path = self.dataset_root / 'layout_dataset.yaml'
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        content = [
            f"path: {self.dataset_root.resolve()}",
            "train: images/train",
            "val: images/val",
            "names:",
        ]
        for idx, name in enumerate(self.class_names):
            content.append(f"  {idx}: {name}")

        with yaml_path.open('w', encoding='utf-8') as handle:
            handle.write('\n'.join(content))

        return yaml_path


def _persist_training_metrics(save_dir: Path, epochs: int) -> Optional[Path]:
    """Capture YOLO training metrics (mAP, precision, recall) into JSON for runtime display."""

    results_csv = save_dir / 'results.csv'
    if not results_csv.exists():
        return None

    try:
        with results_csv.open('r', encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        print(f"[LAYOUT] Unable to parse {results_csv}: {exc}")
        return None

    if not rows:
        return None

    latest = rows[-1]
    metrics = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'epochs': epochs,
        'precision': float(latest.get('metrics/precision(B)', 0) or 0),
        'recall': float(latest.get('metrics/recall(B)', 0) or 0),
        'map50': float(latest.get('metrics/mAP50(B)', 0) or 0),
        'map5095': float(latest.get('metrics/mAP50-95(B)', 0) or 0)
    }

    target_path = Path(LAYOUT_METRICS_PATH)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target_path.open('w', encoding='utf-8') as handle:
            json.dump(metrics, handle, indent=2)
        print(f"[LAYOUT] Saved training metrics to {target_path}")
    except Exception as exc:
        print(f"[LAYOUT] Failed to persist training metrics: {exc}")
        return None

    return target_path


def train_layout_detector(
    dataset_info: LayoutDatasetInfo,
    base_model: str = 'yolov8n.pt',
    epochs: int = 50, #lower , this shit is heavy ,standard is 40
    batch_size: int = 8,
    image_size: int = 640,
    device: str = 'auto',
) -> Dict[str, Path | None]:
    """Train or fine-tune a YOLO detector that segments invoice regions."""

    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "Ultralytics is required for layout training. Install via 'pip install ultralytics'."
        ) from exc

    print("\n" + "=" * 60)
    print("Training Layout Detector (YOLO)")
    print("=" * 60)

    print(f"[LAYOUT] Using dataset at {dataset_info.root}")
    for split, count in dataset_info.samples_per_split.items():
        print(f"    - {split}: {count} samples")

    model = YOLO(base_model)
    model.train(
        data=str(dataset_info.yaml_path),
        epochs=epochs,
        imgsz=image_size,
        batch=batch_size,
        device=device,
        project=str(ROOT_DIR / 'saved_models'),
        name='layout_detector',
        exist_ok=True,
        verbose=True,
    )

    trainer = getattr(model, 'trainer', None)
    if trainer and getattr(trainer, 'save_dir', None):
        save_dir = Path(trainer.save_dir)
    else:
        save_dir = Path(ROOT_DIR / 'saved_models' / 'layout_detector')
    weights_path = save_dir / 'weights' / 'best.pt'
    export_path: Optional[Path] = None

    try:
        export_path = Path(ROOT_DIR / 'saved_models' / 'layout_detector.onnx')
        model.export(format='onnx', imgsz=image_size, path=export_path, simplify=True)
    except Exception as export_error:  # pragma: no cover - export optional
        print(f"[LAYOUT] Export failed: {export_error}")
        export_path = None

    print(f"[LAYOUT] Training artifacts stored in {save_dir}")
    if weights_path.exists():
        print(f"[LAYOUT] Best weights: {weights_path}")

    if export_path and export_path.exists():
        print(f"[LAYOUT] ONNX export available at {export_path}")

    metrics_path = _persist_training_metrics(save_dir, epochs)

    return {
        'weights': weights_path if weights_path.exists() else None,
        'export': export_path,
        'metrics': metrics_path
    }


def _sync_layout_weights(weights_path: Optional[Path]) -> Optional[Path]:
    """Copy freshly trained weights to the runtime path consumed by PebbleOCR."""

    target_path = Path(LAYOUT_WEIGHTS_PATH)
    if weights_path is None or not weights_path.exists():
        print("[SYNC] No layout weights were produced; skipping copy.")
        return None

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if weights_path.resolve() == target_path.resolve():
            print(f"[SYNC] Layout weights already live at {target_path}")
        else:
            shutil.copy2(weights_path, target_path)
            print(f"[SYNC] Copied YOLO weights to {target_path}")
    except Exception as exc:  # pragma: no cover - filesystem specific
        print(f"[SYNC] Failed to copy layout weights: {exc}")
        raise

    return target_path


def _verify_layout_service_ready():
    """Ensure services.layout_service can load the latest weights."""

    print("[VERIFY] Checking PebbleOCR layout service wiring...")
    try:
        from services.layout_service import initialize_layout_detector

        model = initialize_layout_detector()
        if model is None:
            raise RuntimeError("layout_service returned None model")
        print(f"[VERIFY] layout_service is now pointing at {LAYOUT_WEIGHTS_PATH}")
    except Exception as exc:
        print(f"[VERIFY] Layout service failed to initialize with new weights: {exc}")
        raise


def main():
    """Entry point for training + verifying the layout detector used at runtime."""

    print("\n" + "=" * 60)
    print("LAYOUT TRAINING FOR PEBBLEOCR")
    print("=" * 60)

    (ROOT_DIR / 'saved_models').mkdir(exist_ok=True)

    try:
        layout_cfg = LAYOUT_TRAINING_CONFIG
        run_layout = layout_cfg.get('enabled', True)

        trained_weights: Optional[Path] = None
        trained_metrics_path: Optional[Path] = None

        if run_layout:
            print("\n[PIPELINE] Preparing layout dataset...")
            builder = LayoutDatasetBuilder()
            metadata_map = {
                'train': GENERATED_DIR / 'train_metadata.json',
                'val': GENERATED_DIR / 'valid_metadata.json',
            }
            rebuild_flag = layout_cfg.get('rebuild_dataset', False) or not builder.dataset_root.exists()
            layout_info = builder.prepare(metadata_map, rebuild=rebuild_flag)

            if layout_info.samples_per_split:
                layout_device = _resolve_device(layout_cfg.get('device', 'auto'))
                artifacts = train_layout_detector(
                    layout_info,
                    base_model=layout_cfg.get('base_model', 'yolov8n.pt'),
                    epochs=layout_cfg.get('epochs', 40),
                    batch_size=layout_cfg.get('batch_size', 8),
                    image_size=layout_cfg.get('image_size', 640),
                    device=layout_device,
                )
                trained_weights = artifacts.get('weights') if artifacts else None
                trained_metrics_path = artifacts.get('metrics') if artifacts else None
            else:
                print("[PIPELINE] No layout samples prepared. Skipping detector training.")
        else:
            print("[PIPELINE] Layout stage disabled via configuration.")

        live_weights = _sync_layout_weights(trained_weights)
        if live_weights is None:
            print(f"[SYNC] Using existing weights at {LAYOUT_WEIGHTS_PATH}")

        if trained_metrics_path:
            print(f"[PIPELINE] Latest YOLO metrics saved to {trained_metrics_path}")

        _verify_layout_service_ready()

        print("\n" + "=" * 60)
        print("Layout pipeline finished.")
        print("=" * 60)

    except Exception as exc:
        print(f"\n[X] Error during training: {exc}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
