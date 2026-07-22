import requests
import json
from ddgs import DDGS

class ExternalIntelligence:
    def __init__(self):
        pass

    def get_weather_forecast(self, lat, lon):
        """
        Fetches real-time weather from Open-Meteo.
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_probability_max&timezone=Asia%2FBangkok"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            # Extract today's forecast
            temp_max = data['daily']['temperature_2m_max'][0]
            rain_prob = data['daily']['precipitation_probability_max'][0]
            
            condition = "Sunny"
            if rain_prob > 50: condition = "Rainy"
            elif temp_max > 35: condition = "Hot"
            
            return {
                "temp": temp_max,
                "rain_prob": rain_prob,
                "condition": condition,
                "summary": f"Temp: {temp_max}°C, Rain Chance: {rain_prob}% ({condition})"
            }
        except Exception as e:
            return {"error": str(e), "summary": "Weather data unavailable"}

    def check_market_prices(self, product_name):
        """
        Uses DuckDuckGo to find competitor prices.
        """
        try:
            with DDGS() as ddgs:
                # Search for 'Product Name price Vietnam'
                query = f"{product_name} giá bao nhiêu shopee lazada"
                results = list(ddgs.text(query, max_results=3))
                
                # Simple extraction (In production, use an LLM to parse this)
                return {
                    "market_status": "Active",
                    "competitor_snippets": [r['body'] for r in results]
                }
        except Exception:
            return {"market_status": "Unknown", "competitor_snippets": []}