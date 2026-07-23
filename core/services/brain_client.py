import io

import requests

from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

# Qwen2-VL's visual-token count (and therefore VRAM) scales with input
# resolution. A full-resolution phone photo can push CUDA OOM on an
# already-loaded L4 GPU (confirmed live: "Tried to allocate 37.60 GiB").
# 1536px on the long side is comfortably enough for a VLM to read invoice
# text/tables while keeping memory bounded.
MAX_IMAGE_DIMENSION = 1536


def _downscale_if_needed(file_bytes, filename=None):
    """Resize an image so its longest side is <= MAX_IMAGE_DIMENSION.

    Never upscales. Re-encodes as JPEG (smaller, faster upload) when a
    resize happens. If the bytes aren't a Pillow-openable image (e.g. a
    PDF, which this upload path also accepts), returns them unchanged —
    same as today's behavior, not a regression.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not available — skipping image downscale")
        return file_bytes

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
    except Exception:
        return file_bytes

    width, height = img.size
    if max(width, height) <= MAX_IMAGE_DIMENSION:
        return file_bytes

    scale = MAX_IMAGE_DIMENSION / max(width, height)
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = img.convert("RGB").resize(new_size, Image.LANCZOS)

    out = io.BytesIO()
    resized.save(out, format="JPEG", quality=90)
    logger.info(
        "Downscaled invoice image %s: %dx%d -> %dx%d",
        filename or "<upload>", width, height, new_size[0], new_size[1],
    )
    return out.getvalue()


class BrainClient:
    """
    Client for Brain's real POST /ocr endpoint (external VLM invoice
    digitization service, ngrok-tunneled). Mirrors DLClient's shape/error
    handling in core/services/dl_client.py but talks to Brain's actual
    contract (see workflow_templates/invoice_vlm_digitize.CONTRACT.md).
    """

    def __init__(self, base_url=None, token=None, timeout=None):
        self.base_url = (base_url or Config.BRAIN_URL or '').rstrip('/')
        self.token = token or Config.BRAIN_TOKEN
        # Brain's own /ocr call can take 30-60s+ per live testing — 90s
        # gives headroom over that observed range.
        self.timeout = timeout or 90

    def run_ocr(self, file_bytes, filename=None):
        """
        POST the uploaded invoice image to Brain's real /ocr endpoint.
        Returns Brain's raw response dict unchanged on success, or
        {"error": "<message>"} on any network/parsing failure — never
        raises.
        """
        if not self.base_url:
            return {"error": "BRAIN_URL is not configured"}

        url = f"{self.base_url}/ocr"
        file_bytes = _downscale_if_needed(file_bytes, filename)
        files = {'file': (filename or 'invoice.jpg', file_bytes)}
        headers = {'ngrok-skip-browser-warning': 'true'}
        if self.token:
            headers['X-API-Token'] = self.token

        try:
            response = requests.post(url, files=files, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("Brain /ocr request failed: %s", e)
            return {"error": str(e)}
        except ValueError as e:
            logger.error("Brain /ocr returned an invalid response: %s", e)
            return {"error": "Brain returned an invalid response"}
