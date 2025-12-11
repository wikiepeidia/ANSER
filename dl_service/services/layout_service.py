"""Layout detection service powered by the trained YOLO model."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from config import LAYOUT_WEIGHTS_PATH, LAYOUT_INFER_DEVICE, LAYOUT_METRICS_PATH
from utils.logger import get_logger

logger = get_logger(__name__)

try:  # Lazy optional dependency
    from ultralytics import YOLO  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    YOLO = None  # type: ignore


@dataclass
class LayoutRegion:
    name: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float


_layout_model = None
_layout_device: Optional[str] = None
_layout_metrics: Optional[Dict[str, float]] = None


def _resolve_device(requested: Optional[str]) -> str:
    desired = (requested or 'auto').strip().lower()
    if desired != 'auto':
        return desired

    try:  # pragma: no cover - torch may be unavailable in tests
        import torch  # type: ignore

        if torch.cuda.is_available():
            return '0'
    except Exception:
        pass

    logger.info("[LAYOUT] No CUDA device detected, defaulting to CPU")
    return 'cpu'


def initialize_layout_detector():
    """Warm up the YOLO model at application start."""
    model = get_layout_model()
    _load_training_metrics()
    logger.info("[LAYOUT] Detector ready with weights %s", LAYOUT_WEIGHTS_PATH)
    return model


def get_layout_model():
    """Load the YOLO model lazily the first time it is needed."""
    global _layout_model, _layout_device

    if _layout_model is not None:
        return _layout_model

    if YOLO is None:
        raise ImportError("Ultralytics is required for layout inference. Run 'pip install ultralytics'.")

    weights_path = Path(LAYOUT_WEIGHTS_PATH)
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Layout detector weights not found at {weights_path}. Run the training pipeline first."
        )

    _layout_device = _resolve_device(os.getenv('LAYOUT_INFER_DEVICE', LAYOUT_INFER_DEVICE))
    logger.info("[LAYOUT] Loading YOLO weights from %s on device %s", weights_path, _layout_device)
    _layout_model = YOLO(str(weights_path))
    return _layout_model


def _load_training_metrics():
    """Read the metrics JSON produced by the training script if it exists."""
    global _layout_metrics
    metrics_path = Path(LAYOUT_METRICS_PATH)
    if not metrics_path.exists():
        _layout_metrics = None
        return
    try:
        with metrics_path.open('r', encoding='utf-8') as handle:
            _layout_metrics = json.load(handle)
            logger.info(
                "[LAYOUT] Loaded training metrics: mAP50=%.3f mAP5095=%.3f",
                _layout_metrics.get('map50', 0.0),
                _layout_metrics.get('map5095', 0.0)
            )
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("[LAYOUT] Unable to parse training metrics JSON: %s", exc)
        _layout_metrics = None


def _clamp_bbox(bbox: np.ndarray, width: int, height: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox.tolist()
    x1 = max(0, min(width - 1, int(round(x1))))
    y1 = max(0, min(height - 1, int(round(y1))))
    x2 = max(0, min(width, int(round(x2))))
    y2 = max(0, min(height, int(round(y2))))
    if x2 <= x1:
        x2 = min(width, x1 + 1)
    if y2 <= y1:
        y2 = min(height, y1 + 1)
    return x1, y1, x2, y2


def detect_layout_regions(image: np.ndarray, conf_threshold: float = 0.25) -> Dict[str, LayoutRegion]:
    """Run the YOLO detector and return the highest-confidence region per class."""
    model = get_layout_model()
    device = _layout_device or _resolve_device(os.getenv('LAYOUT_INFER_DEVICE', LAYOUT_INFER_DEVICE))

    if image is None or image.size == 0:
        raise ValueError("Empty image passed to layout detector")

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model.predict(rgb, imgsz=640, conf=conf_threshold, device=device, verbose=False)
    if not results:
        return {}

    names = model.names if hasattr(model, 'names') else {}
    regions: Dict[str, LayoutRegion] = {}
    frame_h, frame_w = image.shape[:2]

    for result in results:
        boxes = getattr(result, 'boxes', None)
        if boxes is None or boxes.xyxy is None or len(boxes) == 0:
            continue
        xyxy = boxes.xyxy.cpu().numpy()
        classes = boxes.cls.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()

        for bbox, cls, conf in zip(xyxy, classes, confidences):
            label = names.get(int(cls), str(int(cls)))
            confidence = float(conf)
            if confidence < conf_threshold:
                continue
            clamped_bbox = _clamp_bbox(bbox, frame_w, frame_h)
            existing = regions.get(label)
            if existing is None or confidence > existing.confidence:
                regions[label] = LayoutRegion(label, clamped_bbox, confidence)

    return regions


def crop_region(image: np.ndarray, bbox: Tuple[int, int, int, int], padding: int = 8) -> np.ndarray:
    """Crop a region from the image with optional padding."""
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    return image[y1:y2, x1:x2].copy()


def get_layout_training_metrics() -> Optional[Dict[str, float]]:
    """Expose the latest metrics parsed from the YOLO training run."""
    if _layout_metrics is None:
        _load_training_metrics()
    return _layout_metrics