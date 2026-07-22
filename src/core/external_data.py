import logging

import httpx
from ddgs import DDGS

logger = logging.getLogger(__name__)


class ExternalIntelligence:

    def get_weather_forecast(self, lat, lon):
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_probability_max&timezone=Asia%2FBangkok"
            response = httpx.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            temp_max = data['daily']['temperature_2m_max'][0]
            rain_prob = data['daily']['precipitation_probability_max'][0]

            condition = "Sunny"
            if rain_prob > 50:
                condition = "Rainy"
            elif temp_max > 35:
                condition = "Hot"

            return {
                "temp": temp_max,
                "rain_prob": rain_prob,
                "condition": condition,
                "summary": f"Temp: {temp_max}°C, Rain Chance: {rain_prob}% ({condition})"
            }
        except httpx.HTTPStatusError:
            logger.error("Weather API returned error for lat=%s lon=%s", lat, lon, exc_info=True)
            return {"error": "http_error", "summary": "Weather data unavailable"}
        except (KeyError, IndexError):
            logger.error("Unexpected weather response structure for lat=%s lon=%s", lat, lon, exc_info=True)
            return {"error": "parse_error", "summary": "Weather data unavailable"}
        except httpx.HTTPError:
            logger.error("Weather API request failed for lat=%s lon=%s", lat, lon, exc_info=True)
            return {"error": "request_error", "summary": "Weather data unavailable"}

    def check_market_prices(self, product_name):
        try:
            with DDGS() as ddgs:
                query = f"{product_name} giá bao nhiêu shopee lazada"
                results = list(ddgs.text(query, max_results=3))

                return {
                    "market_status": "Active",
                    "competitor_snippets": [r['body'] for r in results]
                }
        except (KeyError, IndexError):
            logger.error("Unexpected DDGS response for product='%s'", product_name, exc_info=True)
            return {"market_status": "Unknown", "competitor_snippets": []}
        except Exception:
            logger.error("DDGS search failed for product='%s'", product_name, exc_info=True)
            return {"market_status": "Unknown", "competitor_snippets": []}