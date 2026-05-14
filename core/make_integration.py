import requests
import time
import json

def trigger_webhook(url, method="POST", payload=None):
    """
    Triggers a real HTTP request.
    """
    print(f"[HTTP] {method} {url}")
    print(f"[HTTP] Payload: {payload}")
    
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
        except:
            data = response.text
            
        return {
            "status": "success",
            "status_code": response.status_code,
            "response": data
        }
        
    except Exception as e:
        print(f"[HTTP] Error: {e}")
        return {"status": "error", "message": str(e)}
