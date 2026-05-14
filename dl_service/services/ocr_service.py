from io import BytesIO
import logging
import os
import json
from typing import Optional

# Fix PaddlePaddle PIR compiler crash on Windows CPU (oneDNN + PIR incompatibility)
os.environ.setdefault('FLAGS_enable_pir_api', '0')
os.environ.setdefault('FLAGS_enable_pir_in_executor', '0')

import numpy as np
from PIL import Image
import requests

logger = logging.getLogger(__name__)

# ── Brain (Qwen2-VL) Configuration ──────────────────────────────────────────
_brain_url = None
_brain_disabled = False

_paddle_engine = None
_paddle_disabled = False
_easyocr_reader = None
_easyocr_disabled = False

from services.cpt_ocr import run_vietocr_with_paddle_layout

def _vietocr_ocr(image: Image.Image) -> Optional[dict]:
    engine = _get_paddle_engine()
    if engine is None:
        return None
    try:
        print("[OCR] VietOCR: attempting with CV Layout (Paddle/CTPN)...", flush=True)
        res = run_vietocr_with_paddle_layout(image, engine)
        if res and res.get('text'):
             return res
    except Exception as exc:
        print(f"[OCR] VietOCR: ERROR ({exc}) — falling back", flush=True)
    return None


def _get_brain_url():
    """Load the Brain (AI Agent Service) base URL from secrets/ai_config.json."""
    global _brain_url, _brain_disabled
    if _brain_disabled:
        return None
    if _brain_url is not None:
        return _brain_url
    try:
        config_paths = [
            os.path.join(os.getcwd(), 'secrets', 'ai_config.json'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'secrets', 'ai_config.json'),
        ]
        for p in config_paths:
            if os.path.exists(p):
                with open(p, 'r') as f:
                    conf = json.load(f)
                    url = conf.get('HF_BASE_URL', '').rstrip('/')
                    if url:
                        _brain_url = url
                        logger.info("Brain OCR endpoint discovered: %s/ocr", _brain_url)
                        return _brain_url
        _brain_disabled = True
        logger.info("No ai_config.json found; Brain VLM OCR disabled")
        return None
    except Exception as exc:
        _brain_disabled = True
        logger.info("Failed to load Brain URL: %s", exc)
        return None


def _brain_vlm_ocr(image: Image.Image) -> Optional[dict]:
    """
    Primary OCR: send image to the Brain's Qwen2-VL / VisionAgent endpoint.
    Returns extracted text or None if the Brain is unreachable.
    """
    global _brain_disabled
    url = _get_brain_url()
    if not url:
        print("[OCR] Brain VLM: SKIPPED (no config / previously disabled)", flush=True)
        return None
    print(f"[OCR] Brain VLM: attempting Qwen2-VL OCR via {url}/ocr ...", flush=True)
    try:
        buf = BytesIO()
        image.save(buf, format='PNG')
        buf.seek(0)

        resp = requests.post(
            f"{url}/ocr",
            files={'file': ('invoice.png', buf, 'image/png')},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[OCR] Brain VLM: server returned HTTP {resp.status_code}, falling back", flush=True)
            logger.info("Brain OCR returned status %d, falling back", resp.status_code)
            return None

        data = resp.json()
        if not data.get('success'):
            print(f"[OCR] Brain VLM: unsuccessful — {data.get('error')}", flush=True)
            logger.info("Brain OCR unsuccessful: %s", data.get('error'))
            return None

        text = (data.get('text') or '').strip()
        if not text:
            print("[OCR] Brain VLM: returned empty text, falling back", flush=True)
            return None
        # Guard against vision error strings leaking through as "text"
        if text.startswith('Error analyzing') or text.startswith('Vision module'):
            print(f"[OCR] Brain VLM: vision error in response — {text[:80]}", flush=True)
            return None

        print(f"[OCR] Brain VLM: SUCCESS — extracted {len(text)} chars (backend={data.get('backend','qwen2-vl')})", flush=True)
        return {
            'text': text,
            'backend': data.get('backend', 'qwen2-vl'),
            'confidence': float(data.get('confidence', 0.89)),
        }
    except requests.exceptions.ConnectionError:
        print("[OCR] Brain VLM: OFFLINE (ConnectionError) — falling back to PaddleOCR", flush=True)
        logger.info("Brain unreachable (offline); falling back to PaddleOCR")
        _brain_disabled = True  # Don't retry for the rest of this process
        return None
    except requests.exceptions.Timeout:
        print("[OCR] Brain VLM: TIMEOUT (30s) — falling back to PaddleOCR", flush=True)
        logger.info("Brain OCR timed out; falling back to PaddleOCR")
        return None
    except Exception as exc:
        print(f"[OCR] Brain VLM: ERROR ({exc}) — falling back", flush=True)
        logger.info("Brain OCR error: %s; falling back", exc)
        return None

_PADDLE_USE_GPU = os.getenv('PADDLE_OCR_USE_GPU', '').lower() in {'1', 'true', 'yes'}
_PADDLE_DEVICE = os.getenv('PADDLE_OCR_DEVICE')
_PADDLE_LANG = os.getenv('PADDLE_OCR_LANG', 'en')  # PaddleOCR 'en' model supports Latin + Vietnamese characters


def _get_paddle_engine():
    global _paddle_engine, _paddle_disabled
    if _paddle_disabled:
        return None
    if _paddle_engine is not None:
        return _paddle_engine
    try:
        from paddleocr import PaddleOCR
        resolved_device = _PADDLE_DEVICE or ('gpu:0' if _PADDLE_USE_GPU else 'cpu')
        try:
            # Try new API first (device argument)
            _paddle_engine = PaddleOCR(
                use_angle_cls=True,
                lang=_PADDLE_LANG,
                device=resolved_device,
                det_db_thresh=0.2,
                det_db_box_thresh=0.4,
                rec_batch_num=6
            )
            logger.info(
                "PaddleOCR initialized (lang=%s, device=%s, enhanced detection)",
                _PADDLE_LANG,
                resolved_device
            )
        except (TypeError, ValueError) as exc:
            # Fallback for older versions or different API signatures
            # It seems newer paddleocr might not accept use_gpu or device in some contexts, 
            # or raises ValueError for unknown args.
            # Let's try a minimal init if the above fails.
            logger.info("PaddleOCR init failed with device arg (%s), retrying minimal init", exc)
            try:
                 _paddle_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=_PADDLE_LANG,
                    det_db_thresh=0.2,
                    det_db_box_thresh=0.4,
                    rec_batch_num=6
                )
                 logger.info("PaddleOCR initialized (minimal args)")
            except Exception as e2:
                 logger.error("PaddleOCR minimal init failed: %s", e2)
                 raise e2
    except Exception as exc:  # pragma: no cover - environment specific
        _paddle_disabled = True
        logger.warning("PaddleOCR unavailable: %s", exc)
        return None
    return _paddle_engine


def _paddle_ocr(image: Image.Image) -> Optional[dict]:
    engine = _get_paddle_engine()
    if engine is None:
        return None
    try:
        # PaddleOCR v3.4+ removed cls kwarg from ocr()/predict()
        try:
            result = engine.ocr(np.array(image), cls=True)
        except TypeError:
            try:
                result = engine.ocr(np.array(image))
            except Exception:
                result = list(engine.predict(np.array(image)))
             
        if not result:
            logger.info("PaddleOCR returned no text; falling back")
            return None
        texts = []
        confidences = []

        # Handle new PaddleOCR output format (list of dicts)
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and 'rec_texts' in result[0]:
            data = result[0]
            rec_texts = data.get('rec_texts', [])
            rec_scores = data.get('rec_scores', [])
            for i, text in enumerate(rec_texts):
                text = (text or '').strip()
                if not text:
                    continue
                texts.append(text)
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                confidences.append(float(score))
        # Handle classic PaddleOCR output format (list of lists)
        elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            for line in result[0]:
                if not line or len(line) < 2: continue
                text_info = line[1]
                if not text_info or len(text_info) < 2: continue
                
                text = (text_info[0] or '').strip()
                score = float(text_info[1]) if text_info[1] is not None else 0.0
                if not text:
                    continue
                texts.append(text)
                confidences.append(score)
        
        if not texts:
            return None
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return {
            'text': "\n".join(texts),
            'backend': 'paddleocr',
            'confidence': avg_conf
        }
    except Exception as exc:
        logger.info("PaddleOCR failed, falling back: %s", exc)
        return None


def _get_easyocr_reader():
    global _easyocr_reader, _easyocr_disabled
    if _easyocr_disabled:
        return None
    if _easyocr_reader is not None:
        return _easyocr_reader
    try:
        import easyocr

        _easyocr_reader = easyocr.Reader(['en', 'vi'], gpu=_PADDLE_USE_GPU)
        logger.info("EasyOCR initialized (gpu=%s)", 'on' if _PADDLE_USE_GPU else 'off')
    except Exception as exc:
        _easyocr_disabled = True
        logger.warning("EasyOCR unavailable: %s", exc)
        return None
    return _easyocr_reader


def _easyocr_ocr(image: Image.Image) -> Optional[dict]:
    reader = _get_easyocr_reader()
    if reader is None:
        return None
    try:
        results = reader.readtext(np.array(image.convert('RGB')))
        if not results:
            return None
        texts = []
        confidences = []
        for _, text, score in results:
            text = (text or '').strip()
            if not text:
                continue
            texts.append(text)
            confidences.append(float(score) if score is not None else 0.0)
        if not texts:
            return None
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return {
            'text': "\n".join(texts),
            'backend': 'easyocr',
            'confidence': avg_conf
        }
    except Exception as exc:
        logger.info("EasyOCR failed, falling back: %s", exc)
        return None


def _pytesseract_ocr(image: Image.Image) -> Optional[dict]:
    try:
        import pytesseract
    except Exception as exc:
        logger.debug("pytesseract import failed: %s", exc)
        return None
    try:
        text = pytesseract.image_to_string(image).strip()
        if not text:
            return None
        return {
            'text': text,
            'backend': 'pytesseract',
            'confidence': 0.0
        }
    except Exception as exc:
        logger.info("pytesseract failed: %s", exc)
        return None


def extract_text_from_image_bytes(image_bytes):
    """Extract text using Qwen2-VL (Brain) → PaddleOCR → EasyOCR → Tesseract fallback."""

    try:
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
    except Exception as exc:
        return {'success': False, 'text': '', 'error': f'Failed to open image: {exc}'}

    # Build cascade: prefer fast local engines first, remote/slow backends last.
    # EasyOCR is the most reliable local backend on Windows.
    # PaddleOCR 3.4 has oneDNN/PIR crash on Windows CPU — try but expect failure.
    # Brain VLM requires a remote server (30s timeout) — only try if configured.
    backends = [
        ('EasyOCR',                             _easyocr_ocr),
        ('PaddleOCR',                           _paddle_ocr),
        ('VietOCR + ComputerVision',            _vietocr_ocr),
        ('Brain VLM (Qwen2-VL)',                _brain_vlm_ocr),
        ('Tesseract',                           _pytesseract_ocr),
    ]
    print(f"[OCR] Fallback chain: {' → '.join(n for n, _ in backends)}", flush=True)
    for name, runner in backends:
        result = runner(image)
        if result and result.get('text'):
            print(f"[OCR] ✓ Text extracted by: {name} (backend={result.get('backend')}, len={len(result['text'])}, conf={result.get('confidence',0):.3f})", flush=True)
            logger.info(
                "OCR success via %s (len=%d, confidence=%.3f)",
                result.get('backend'),
                len(result.get('text', '')),
                float(result.get('confidence', 0.0))
            )
            return {
                'success': True,
                'text': result['text'],
                'error': '',
                'backend': result.get('backend'),
                'confidence': float(result.get('confidence', 0.0))
            }

    logger.error('All OCR backends failed')
    return {
        'success': False,
        'text': '',
        'error': (
            'No OCR backend available. Install `paddleocr` (preferred), or `easyocr` / '
            '`pytesseract` with the Tesseract engine.'
        )
    }
