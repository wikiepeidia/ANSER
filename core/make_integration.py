import requests
import time
import json

from core.logger import get_logger

logger = get_logger(__name__)


def trigger_webhook(url, method="POST", payload=None):
    """
    Triggers a real HTTP request.
    """
    logger.info("HTTP %s %s", method, url)
    logger.info("HTTP payload: %s", payload)

    try:
        if method.upper() == "POST":
            response = requests.post(url, json=payload, timeout=5)
        elif method.upper() == "GET":
            response = requests.get(url, params=payload, timeout=5)
        else:
            return {"status": "error", "message": f"Unsupported method: {method}"}

        # Try to parse JSON response, otherwise return text
        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            data = response.text

        return {
            "status": "success",
            "status_code": response.status_code,
            "response": data
        }

    except requests.RequestException as e:
        logger.error("HTTP request error for %s %s: %s", method, url, e, exc_info=True)
        return {"status": "error", "message": str(e)}
