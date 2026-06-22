import requests
import os
from core.logger import get_logger

logger = get_logger(__name__)

class DLClient:
    """
    Client for the Deep Learning Microservice.
    Supports both local execution (direct integration) and remote HTTP calls.
    """
    def __init__(self, use_local=False, base_url=None):
        self.use_local = use_local
        self.base_url = base_url or os.environ.get('DL_SERVICE_URL', 'http://localhost:5001')
        self.timeout = int(os.environ.get('DL_SERVICE_TIMEOUT', 30))

    def detect_invoice(self, file_path=None, file_bytes=None, filename=None):
        """
        Calls /api/model1/detect to extract invoice data.
        """
        if self.use_local:
            try:
                from services.invoice_service import process_invoice_image
                import numpy as np
                import cv2
                
                # process_invoice_image expects a cv2 image (numpy array)
                # It returns a dict with 'invoice_data' etc.
                if file_path:
                    with open(file_path, 'rb') as f:
                        image_bytes = f.read()
                elif file_bytes:
                    image_bytes = file_bytes
                else:
                    raise ValueError("Either file_path or file_bytes must be provided")
                
                # Convert bytes to cv2 image
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is None:
                     raise ValueError("Could not decode image bytes")

                result = process_invoice_image(image)
                return result
            except Exception as e:
                logger.exception("Local DL error during invoice detection")
                return {"error": str(e), "status": "failed"}
        
        url = f"{self.base_url}/api/model1/detect"
        files = {}
        
        try:
            if file_path:
                files = {'file': open(file_path, 'rb')}
            elif file_bytes:
                files = {'file': (filename or 'invoice.jpg', file_bytes)}
            else:
                raise ValueError("Either file_path or file_bytes must be provided")

            response = requests.post(url, files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("DL service error during invoice detection: %s", e)
            return {"error": str(e), "status": "failed"}
        finally:
            if file_path and 'file' in files:
                files['file'].close()

    def _forecast_payload(self, data):
        if not isinstance(data, dict):
            return data

        products = data.get('products')
        if not products and isinstance(data.get('items'), list):
            products = data['items']

        invoice_data = data.get('invoice_data')
        if not products and isinstance(invoice_data, dict):
            products = invoice_data.get('products') or invoice_data.get('items')
        elif not products and isinstance(invoice_data, list):
            products = invoice_data

        inner_data = data.get('data')
        if not products and isinstance(inner_data, dict):
            products = inner_data.get('products') or inner_data.get('items')
        elif not products and isinstance(inner_data, list):
            products = inner_data

        if products:
            payload = dict(data)
            payload['products'] = products
            return payload

        return data

    def forecast_quantity(self, data):
        """
        Calls /api/model2/forecast to predict quantities.
        """
        # Guard: validate data before processing
        if data is None:
            return {"error": "No data provided for forecasting. Connect an OCR/data node or provide sales data.", "status": "failed"}
        if isinstance(data, str):
            # Try to parse JSON string
            try:
                import json as _json
                data = _json.loads(data)
            except Exception:
                return {"error": f"Invalid data format: expected JSON object, got string: '{data[:100]}'", "status": "failed"}
        if not isinstance(data, dict):
            return {"error": f"Invalid data format: expected dict, got {type(data).__name__}", "status": "failed"}

        data = self._forecast_payload(data)

        if self.use_local:
            try:
                # Lazy imports to avoid heavy startup cost
                from services.model_loader import get_lstm_model
                from services.forecast_service import forecast_quantity, format_forecast_response
                
                products = data.get('products', [])
                if not products:
                    # Try alternative keys from OCR output
                    if 'invoice_data' in data:
                        inv = data['invoice_data']
                        if isinstance(inv, dict) and 'items' in inv:
                            products = inv['items']
                        elif isinstance(inv, list):
                            products = inv
                    elif 'items' in data:
                        products = data['items']
                    elif 'data' in data:
                        inner = data['data']
                        if isinstance(inner, list):
                            products = inner
                        elif isinstance(inner, dict):
                            products = inner.get('products', inner.get('items', []))
                
                if not products:
                    return {"error": "No product/item data found in input. Ensure the previous node outputs product data.", "status": "failed"}
                
                lstm_model = get_lstm_model()
                if not lstm_model:
                     return {"error": "LSTM model failed to load", "status": "failed"}
                
                result = forecast_quantity(lstm_model, products)
                return format_forecast_response(result)
            except Exception as e:
                logger.exception("Local DL error during forecast")
                return {"error": str(e), "status": "failed"}

        url = f"{self.base_url}/api/model2/forecast"
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("DL service error during forecast: %s", e)
            return {"error": str(e), "status": "failed"}

    def run_ocr(self, file_path=None, file_bytes=None, filename=None):
        """
        Calls /api/ocr/ for raw text extraction.
        """
        if self.use_local:
            try:
                from services.ocr_service import extract_text
                
                if file_path:
                    with open(file_path, 'rb') as f:
                        image_bytes = f.read()
                elif file_bytes:
                    image_bytes = file_bytes
                else:
                    raise ValueError("Either file_path or file_bytes must be provided")
                    
                text = extract_text(image_bytes)
                return {"text": text, "status": "success"}
            except Exception as e:
                logger.exception("Local DL error during OCR")
                return {"error": str(e), "status": "failed"}

        url = f"{self.base_url}/api/ocr/"
        files = {}
        try:
            if file_path:
                files = {'image': open(file_path, 'rb')} # Note: API might expect 'image' or 'file'
            elif file_bytes:
                files = {'image': (filename or 'doc.jpg', file_bytes)}
            
            response = requests.post(url, files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("DL service error during OCR: %s", e)
            return {"error": str(e), "status": "failed"}
        finally:
            if file_path and 'image' in files:
                files['image'].close()
