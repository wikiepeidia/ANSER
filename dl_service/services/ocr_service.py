from io import BytesIO
import logging
import os
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_paddle_engine = None
_paddle_disabled = False
_easyocr_reader = None
_easyocr_disabled = False

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
        except TypeError as type_exc:
            if 'device' not in str(type_exc).lower():
                raise
            logger.info("PaddleOCR build lacks `device` arg, retrying with legacy `use_gpu` flag")
            _paddle_engine = PaddleOCR(
                use_angle_cls=True,
                lang=_PADDLE_LANG,
                use_gpu=_PADDLE_USE_GPU,
                det_db_thresh=0.2,
                det_db_box_thresh=0.4,
                rec_batch_num=6
            )
            logger.info(
                "PaddleOCR initialized (lang=%s, legacy-gpu=%s, enhanced detection)",
                _PADDLE_LANG,
                'on' if _PADDLE_USE_GPU else 'off'
            )
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
        result = engine.ocr(np.array(image), cls=True)
        if not result or not result[0]:
            logger.info("PaddleOCR returned no text; falling back")
            return None
        texts = []
        confidences = []
        for line in result[0]:
            text = (line[1][0] or '').strip()
            score = float(line[1][1]) if line[1][1] is not None else 0.0
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

        _easyocr_reader = easyocr.Reader(['en'], gpu=_PADDLE_USE_GPU)
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
    """Extract text using PaddleOCR with EasyOCR/Tesseract fallback."""

    try:
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
    except Exception as exc:
        return {'success': False, 'text': '', 'error': f'Failed to open image: {exc}'}

    for runner in (_paddle_ocr, _easyocr_ocr, _pytesseract_ocr):
        result = runner(image)
        if result and result.get('text'):
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
