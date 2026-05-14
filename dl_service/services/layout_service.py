import numpy as np
import torch
import cv2
from PIL import Image
from torchvision import transforms
from dataclasses import dataclass
from typing import Dict, Tuple

from config import LAYOUT_INFER_DEVICE
from utils.logger import get_logger
import os

# Import the newly copied model
from models.cpt_vision_localization._model import CtpnModel

logger = get_logger(__name__)

CFG_IMG_H, CFG_IMG_W = 448, 224
N_ANCHOR = 5

_layout_model = None
_layout_device = None

@dataclass
class LayoutRegion:
    name: str
    bbox: Tuple[int, int, int, int]
    confidence: float

def get_layout_model():
    global _layout_model, _layout_device
    if _layout_model is not None:
        return _layout_model
    
    _layout_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = os.path.join(os.getcwd(), 'dl_service/saved_models/cpt_vision/task1_best.pth')
    if not os.path.exists(model_path):
        # Handle fallback path if run locally
        model_path = os.path.join(os.getcwd(), 'saved_models/cpt_vision/task1_best.pth')
    
    logger.info(f"[LAYOUT] Loading CTPN layout model from {model_path}")
    _layout_model = CtpnModel(N_ANCHOR).to(_layout_device)
    ckpt = torch.load(model_path, map_location=_layout_device, weights_only=False)
    _layout_model.load_state_dict(ckpt["model_state_dict"])
    _layout_model.eval()
    return _layout_model

def get_layout_training_metrics():
    return None

def crop_region(image: np.ndarray, bbox: Tuple[int, int, int, int], padding: int = 8) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    return image[y1:y2, x1:x2].copy()

def _iou(a, b):
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0

def _merge_horizontal(boxes, y_overlap=0.5, x_gap_ratio=2.0):
    if not boxes: return boxes
    boxes = sorted(boxes, key=lambda b: ((b[1] + b[3]) / 2, b[0]))
    merged = []
    used = [False] * len(boxes)
    for i in range(len(boxes)):
        if used[i]: continue
        cur = list(boxes[i])
        used[i] = True
        h = cur[3] - cur[1]
        for j in range(i + 1, len(boxes)):
            if used[j]: continue
            bj = boxes[j]
            hj = bj[3] - bj[1]
            overlap = min(cur[3], bj[3]) - max(cur[1], bj[1])
            if overlap < y_overlap * min(h, hj): continue
            gap = bj[0] - cur[2]
            if gap > x_gap_ratio * max(h, hj): continue
            cur[0] = min(cur[0], bj[0])
            cur[1] = min(cur[1], bj[1])
            cur[2] = max(cur[2], bj[2])
            cur[3] = max(cur[3], bj[3])
            cur[4] = max(cur[4], bj[4])
            used[j] = True
        merged.append(cur)
    return merged

def detect_layout_regions(image: np.ndarray, conf_threshold: float = 0.70) -> Dict[str, LayoutRegion]:
    model = get_layout_model()
    
    # Convert cv2 numpy image to PIL for CTPN transform
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(rgb)
    orig_w, orig_h = image_pil.size
    
    transform = transforms.Compose([
        transforms.Resize((CFG_IMG_H, CFG_IMG_W)),
        transforms.ToTensor(),
    ])
    img_tensor = transform(image_pil).unsqueeze(0).to(_layout_device)

    with torch.no_grad():
        out_1, out_2, out_3 = model(img_tensor)
        
    scores = torch.softmax(out_1, dim=-1)[..., 1]
    anchors = [5 * (2 ** (i / 2)) for i in range(N_ANCHOR)]
    
    boxes = []
    stride = 16
    grid_h, grid_w = scores.size(1), scores.size(2)
    for h_idx in range(grid_h):
        for w_idx in range(grid_w):
            for a_idx, ah in enumerate(anchors):
                score = scores[0, h_idx, w_idx, a_idx].item()
                if score < conf_threshold: continue
                cx_anc, cy_anc = w_idx * stride + stride / 2, h_idx * stride + stride / 2
                v_c = out_2[0, h_idx, w_idx, a_idx, 0].item()
                v_h = out_2[0, h_idx, w_idx, a_idx, 1].item()
                cy = v_c * ah + cy_anc
                h = min(np.exp(v_h) * ah, CFG_IMG_H)
                o = out_3[0, h_idx, w_idx, a_idx].item()
                cx = cx_anc + o * stride
                x0, y0, x1, y1 = cx - stride / 2, cy - h / 2, cx + stride / 2, cy + h / 2
                x0, x1 = x0 / CFG_IMG_W * orig_w, x1 / CFG_IMG_W * orig_w
                y0, y1 = y0 / CFG_IMG_H * orig_h, y1 / CFG_IMG_H * orig_h
                boxes.append([x0, y0, x1, y1, score])
                
    if not boxes: return {}
    
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    keep = []
    suppressed = set()
    for i, bi in enumerate(boxes):
        if i in suppressed: continue
        keep.append(bi)
        for j in range(i + 1, len(boxes)):
            if j in suppressed: continue
            if _iou(bi, boxes[j]) > 0.3: suppressed.add(j)
            
    merged = _merge_horizontal(keep)
    
    # Rather than returning a list of text lines, we will compute the macro bounding box 
    # of ALL text lines combined to act as the "table" crop so the rest of the OCR pipeline succeeds.
    if merged:
        min_x = int(min([b[0] for b in merged]))
        min_y = int(min([b[1] for b in merged]))
        max_x = int(max([b[2] for b in merged]))
        max_y = int(max([b[3] for b in merged]))
        
        # Give a little padding around the entire text block wrapper
        padding = 10
        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(orig_w, max_x + padding)
        max_y = min(orig_h, max_y + padding)
        avg_conf = sum([b[4] for b in merged]) / len(merged)
        
        return {
            'table': LayoutRegion(
                name='table',
                bbox=(min_x, min_y, max_x, max_y),
                confidence=avg_conf
            )
        }
    return {}


def initialize_layout_detector():
    """Initializes the CTPN layout detector for layout_service."""
    return get_layout_model()

def get_text_lines(image: np.ndarray, conf_threshold: float = 0.5):
    """Returns horizontal bounding boxes of text lines using CTPN."""
    model = get_layout_model()
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(rgb)
    orig_w, orig_h = image_pil.size
    
    transform = transforms.Compose([
        transforms.Resize((CFG_IMG_H, CFG_IMG_W)),
        transforms.ToTensor(),
    ])
    img_tensor = transform(image_pil).unsqueeze(0).to(_layout_device)

    with torch.no_grad():
        out_1, out_2, out_3 = model(img_tensor)
        
    scores = torch.softmax(out_1, dim=-1)[..., 1]
    anchors = [5 * (2 ** (i / 2)) for i in range(N_ANCHOR)]
    
    boxes = []
    stride = 16
    grid_h, grid_w = scores.size(1), scores.size(2)
    for h_idx in range(grid_h):
        for w_idx in range(grid_w):
            for a_idx, ah in enumerate(anchors):
                score = scores[0, h_idx, w_idx, a_idx].item()
                if score < conf_threshold: continue
                cx_anc, cy_anc = w_idx * stride + stride / 2, h_idx * stride + stride / 2
                v_c = out_2[0, h_idx, w_idx, a_idx, 0].item()
                v_h = out_2[0, h_idx, w_idx, a_idx, 1].item()
                cy = v_c * ah + cy_anc
                h = min(np.exp(v_h) * ah, CFG_IMG_H)
                o = out_3[0, h_idx, w_idx, a_idx].item()
                cx = cx_anc + o * stride
                x0, y0, x1, y1 = cx - stride / 2, cy - h / 2, cx + stride / 2, cy + h / 2
                x0, x1 = x0 / CFG_IMG_W * orig_w, x1 / CFG_IMG_W * orig_w
                y0, y1 = y0 / CFG_IMG_H * orig_h, y1 / CFG_IMG_H * orig_h
                boxes.append([x0, y0, x1, y1, score])
                
    if not boxes: return []
    
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    keep = []
    suppressed = set()
    for i, bi in enumerate(boxes):
        if i in suppressed: continue
        keep.append(bi)
        for j in range(i + 1, len(boxes)):
            if j in suppressed: continue
            if _iou(bi, boxes[j]) > 0.3: suppressed.add(j)
            
    merged = _merge_horizontal(keep)
    return merged
