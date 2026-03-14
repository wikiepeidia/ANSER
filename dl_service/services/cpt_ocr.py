# Helper module for Vietocr + CV
import os
import sys
import numpy as np
import cv2
from PIL import Image

sys.path.append(os.path.join(os.getcwd(), 'dl_service/models/vietocr'))
try:
    from vietocr.tool.predictor import Predictor
    from vietocr.tool.config import Cfg
    import torch
    _vietocr_config = Cfg.load_config_from_name('vgg_transformer')
    _vietocr_config['device'] = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    _vietocr_predictor = Predictor(_vietocr_config)
except Exception as e:
    _vietocr_predictor = None
    print(f"Warning: VietOCR not loaded - {e}")

from services.layout_service import get_text_lines

def run_vietocr_with_paddle_layout(image_pil, paddle_engine=None): # Ignore paddle argument now
    if not _vietocr_predictor:
        return None

    img_np = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

    lines = get_text_lines(img_np, conf_threshold=0.5)
    
    if not lines:
        return None
        
    full_text = []
    avg_conf = 0.0
    valid_boxes = len(lines)
    
    # Sort bounding boxes top to bottom
    def get_y_min(b):
         return b[1]
    lines.sort(key=get_y_min)
    
    # img_np shape is (H, W, 3) 
    # but PIL crop needs bounds, so let's crop with numpy
    for box in lines:
        try:
            # line bbox comes as [x0, y0, x1, y1, conf]
            x_min = max(0, int(box[0]))
            y_min = max(0, int(box[1]))
            x_max = min(img_np.shape[1], int(box[2]))
            y_max = min(img_np.shape[0], int(box[3]))
            if x_max - x_min < 2 or y_max - y_min < 2:
                continue
            crop_img = img_np[y_min:y_max, x_min:x_max]
            crop_pil = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            text = _vietocr_predictor.predict(crop_pil)
            if text:
                full_text.append(text)
                avg_conf += float(box[4]) # Use the layout detector's text confidence!
        except Exception as e:
            continue
            
    if not full_text:
        return None
    
    return {
        'text': '\n'.join(full_text),
        'backend': 'vietocr+cpt_localization_v2',
        'confidence': avg_conf / (valid_boxes or 1)
    }
