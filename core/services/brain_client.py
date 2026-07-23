import requests

from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)


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
