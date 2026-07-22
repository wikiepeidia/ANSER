import os
import sys
import asyncio
import httpx
import json
import logging
from pathlib import Path

# Add project root to sys.path to allow imports from src
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("projecta.legal_miner")

# Environment configs (Tavily/Firecrawl mocks)
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "mock-key")
BASE_URL = "https://api.firecrawl.dev/v1/scrape"

# Enforce rate limits with a strict semaphore (max 3 concurrent connections)
SEMAPHORE = asyncio.Semaphore(3)

async def scrape_legal_document(client: httpx.AsyncClient, url: str, target_topic: str) -> dict:
    """
    Scrape a specific URL for legal knowledge using Firecrawl/Tavily.
    """
    async with SEMAPHORE:
        logger.info(f"Scraping '{target_topic}' at {url}...")
        try:
            # Simulate a request to Firecrawl/Tavily
            response = await client.post(
                BASE_URL,
                json={"url": url, "formats": ["markdown"]},
                headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return {"url": url, "topic": target_topic, "content": data.get("markdown", ""), "status": "success"}
        except httpx.HTTPError as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {"url": url, "topic": target_topic, "error": str(e), "status": "failed"}

async def main():
    logger.info("Initializing async legal data miner with pagination...")
    
    # Target regulations (base url, topic, max_pages)
    scrape_targets = [
        ("https://thuvienphapluat.vn/Decree-123", "Decree 123/2020/NĐ-CP (Invoices and Documents)", 3),
        ("https://thuvienphapluat.vn/VAT-reduction-2026", "VAT Reduction Policies 2026", 2),
        ("https://thuvienphapluat.vn/Circular-78", "Circular 78/2021/TT-BTC", 1),
    ]
    
    from src.core.utils import HttpClientPool
    client = HttpClientPool.get_client()
    try:
        tasks = []
        for base_url, topic, max_pages in scrape_targets:
            for page in range(1, max_pages + 1):
                paginated_url = f"{base_url}?page={page}"
                tasks.append(scrape_legal_document(client, paginated_url, f"{topic} (Page {page})"))
                
        results = await asyncio.gather(*tasks)
    finally:
        await HttpClientPool.close()
        
    # Save the mined data
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = output_dir / "legal_data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Successfully mined {len([r for r in results if r['status'] == 'success'])} legal documents across all pages.")
    logger.info(f"Data saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
