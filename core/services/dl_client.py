import requests
import json
import os
import sys

# Add dl_service to sys.path to allow imports
current_dir = os.getcwd()
dl_service_path = os.path.join(current_dir, 'dl_service')
if dl_service_path not in sys.path:
    sys.path.append(dl_service_path)

class DLClient:
    """
    Client for the Deep Learning Microservice.
    Supports both local execution (direct integration) and remote HTTP calls.
    """
    def __init__(self, use_local=True, base_url=None):
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
                
                # process_invoice_image expects file_path or bytes
                # It returns a dict with 'invoice_data' etc.
                if file_path:
                    with open(file_path, 'rb') as f:
                        image_bytes = f.read()
                elif file_bytes:
                    image_bytes = file_bytes
                else:
                    raise ValueError("Either file_path or file_bytes must be provided")
                
                result = process_invoice_image(image_bytes)
                return result
            except Exception as e:
                print(f"Local DL Error (Detect): {e}")
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
            print(f"DL Service Error (Detect): {e}")
            return {"error": str(e), "status": "failed"}
        finally:
            if file_path and 'file' in files:
                files['file'].close()

    def forecast_quantity(self, data):
        """
        Calls /api/model2/forecast to predict quantities.
        """
        if self.use_local:
            try:
                # Lazy imports to avoid heavy startup cost
                from services.model_loader import get_lstm_model
                from services.forecast_service import forecast_quantity, format_forecast_response
                
                products = data.get('products', [])
                
                lstm_model = get_lstm_model()
                if not lstm_model:
                     return {"error": "LSTM model failed to load", "status": "failed"}
                
                result = forecast_quantity(lstm_model, products)
                return format_forecast_response(result)
            except Exception as e:
                print(f"Local DL Error (Forecast): {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e), "status": "failed"}

        url = f"{self.base_url}/api/model2/forecast"
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"DL Service Error (Forecast): {e}")
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
                print(f"Local DL Error (OCR): {e}")
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
            print(f"DL Service Error (OCR): {e}")
            return {"error": str(e), "status": "failed"}
        finally:
            if file_path and 'image' in files:
                files['image'].close()
