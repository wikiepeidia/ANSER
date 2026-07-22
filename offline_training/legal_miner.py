"""
legal_miner.py — Scrape tài liệu pháp lý Việt Nam phục vụ RAG + distillation.

CÁCH CHẠY:
  export FIRECRAWL_API_KEY=fc-xxxxxxxxxxxx
  python offline_training/legal_miner.py

KẾT QUẢ:
  src/data/legal_raw.jsonl   — raw markdown từng trang
  src/data/legal_chunks.jsonl — chunks ≤1500 token, sẵn sàng nạp ChromaDB
"""

import os
import sys
import asyncio
import json
import logging
import re
import time
from pathlib import Path

import httpx

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("anser.legal_miner")

# ── Config ────────────────────────────────────────────────────────────────────
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_URL     = "https://api.firecrawl.dev/v1/scrape"
MAX_CONCURRENT    = 3        # giới hạn Firecrawl free tier
RETRY_MAX         = 3
RETRY_BACKOFF     = 2.0      # seconds
CHUNK_SIZE        = 1200     # ký tự / chunk (≈ 400-500 token)
CHUNK_OVERLAP     = 150

USE_MOCK = not FIRECRAWL_API_KEY or FIRECRAWL_API_KEY.startswith("mock")

# ── Scrape targets ─────────────────────────────────────────────────────────────
#  Mỗi entry: (url, topic, priority)
#  priority: "high" = scrape trước, "low" = scrape sau nếu còn thời gian
SCRAPE_TARGETS = [
    # ── Thuế & Hóa đơn ─────────────────────────────────────────────────────
    ("https://thuvienphapluat.vn/van-ban/Thue/Nghi-dinh-72-2024-ND-CP-giam-thue-gia-tri-gia-tang-627388.aspx",
     "NĐ 72/2024 — Giảm thuế GTGT 2% (8%)", "high"),
    ("https://thuvienphapluat.vn/van-ban/Ke-toan-Kiem-toan/Nghi-dinh-123-2020-ND-CP-hoa-don-chung-tu-455618.aspx",
     "NĐ 123/2020 — Hóa đơn điện tử", "high"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Thong-tu-80-2021-TT-BTC-huong-dan-Luat-Quan-ly-thue-488779.aspx",
     "TT 80/2021 — Luật Quản lý thuế", "high"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Luat-Thue-gia-tri-gia-tang-13-2008-QH12-73985.aspx",
     "Luật Thuế GTGT 2008 (sửa đổi 2022)", "high"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Nghi-quyet-142-2024-QH15-thu-tien-thue-GTGT-657098.aspx",
     "NQ 142/2024 — Gia hạn giảm VAT đến 2025", "high"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Thong-tu-78-2021-TT-BTC-hoa-don-dien-tu-486807.aspx",
     "TT 78/2021 — Hướng dẫn hóa đơn điện tử", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Nghi-dinh-15-2022-ND-CP-giam-thue-gia-tri-gia-tang-506258.aspx",
     "NĐ 15/2022 — Giảm VAT trước NĐ 72", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Thue/Nghi-dinh-82-2023-ND-CP-gia-han-nop-thue-tiep-thi-thuong-mai-626006.aspx",
     "NĐ 82/2023 — Gia hạn thuế SME", "medium"),

    # ── Thương mại & Bán lẻ ────────────────────────────────────────────────
    ("https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-85-2021-ND-CP-thuong-mai-dien-tu-490491.aspx",
     "NĐ 85/2021 — Thương mại điện tử", "high"),
    ("https://thuvienphapluat.vn/van-ban/Bao-ve-quyen-loi-nguoi-tieu-dung/Luat-Bao-ve-quyen-loi-nguoi-tieu-dung-2023-564584.aspx",
     "Luật BVQLNTD 2023", "high"),
    ("https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-98-2020-ND-CP-xu-phat-hanh-chinh-thuong-mai-452721.aspx",
     "NĐ 98/2020 — Xử phạt hành chính thương mại", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Thuong-mai/Luat-Canh-tranh-2018-23-2018-QH14-403578.aspx",
     "Luật Cạnh tranh 2018", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-111-2021-ND-CP-nhan-hang-hoa-492437.aspx",
     "NĐ 111/2021 — Nhãn hàng hóa", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Thuong-mai/Thong-tu-40-2021-TT-BTC-thue-thuong-mai-dien-tu-487399.aspx",
     "TT 40/2021 — Thuế TMĐT hộ kinh doanh", "high"),

    # ── An toàn thực phẩm & Dược liệu ─────────────────────────────────────
    ("https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Luat-An-toan-thuc-pham-2010-55-2010-QH12-107698.aspx",
     "Luật An toàn thực phẩm 2010", "high"),
    ("https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-43-2014-TT-BYT-thuc-pham-chuc-nang-247169.aspx",
     "TT 43/2014 — Thực phẩm chức năng (TPCN)", "high"),
    ("https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Nghi-dinh-15-2018-ND-CP-an-toan-thuc-pham-352568.aspx",
     "NĐ 15/2018 — An toàn thực phẩm", "medium"),
    ("https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-21-2018-TT-BYT-GACP-duoc-lieu-394217.aspx",
     "TT 21/2018 — GACP dược liệu (WHO)", "high"),

    # ── Lao động & Bảo hiểm ────────────────────────────────────────────────
    ("https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-luat-Lao-dong-2019-333670.aspx",
     "Bộ Luật Lao động 2019", "medium"),
    ("https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Nghi-dinh-74-2024-ND-CP-luong-toi-thieu-vung-638208.aspx",
     "NĐ 74/2024 — Lương tối thiểu vùng 2024", "high"),

    # ── Bảo vệ dữ liệu ─────────────────────────────────────────────────────
    ("https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-13-2023-ND-CP-bao-ve-du-lieu-ca-nhan-556745.aspx",
     "NĐ 13/2023 — Bảo vệ dữ liệu cá nhân (PDPA VN)", "high"),
]

# ── Helpers ────────────────────────────────────────────────────────────────────
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chia văn bản thành chunks có overlap."""
    if not text or len(text) < 100:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if len(chunk) > 100:
            chunks.append(chunk)
        start += size - overlap
    return chunks

def clean_markdown(md: str) -> str:
    """Làm sạch markdown: bỏ header ảnh, link dư, whitespace thừa."""
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)          # ảnh
    md = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md)  # link → text
    md = re.sub(r"#{1,6}\s*", "", md)                 # heading marker
    md = re.sub(r"\n{3,}", "\n\n", md)                # blank lines thừa
    return md.strip()

MOCK_CONTENT = {
    "NĐ 72/2024": """Nghị định 72/2024/NĐ-CP ngày 30/6/2024 quy định chính sách giảm thuế GTGT.
Điều 1. Giảm thuế GTGT 2% đối với nhóm hàng hóa, dịch vụ đang áp dụng mức thuế suất 10%.
Điều 2. Thời gian áp dụng: từ ngày 01/7/2024 đến ngày 31/12/2024.
Phụ lục I. Danh mục hàng hóa, dịch vụ không được giảm thuế GTGT theo Nghị định này bao gồm: viễn thông, tài chính, ngân hàng, chứng khoán, bảo hiểm, bất động sản, kim loại, sản phẩm từ kim loại, sản phẩm khai khoáng (không kể khai thác than), than cốc, dầu mỏ tinh chế và sản phẩm hóa chất, sản phẩm hàng hóa và dịch vụ chịu thuế tiêu thụ đặc biệt.
Hàng hóa, dịch vụ quy định tại Điều 1 Nghị định này được giảm thuế GTGT còn 8%.""",

    "NĐ 123/2020": """Nghị định 123/2020/NĐ-CP ngày 19/10/2020 quy định về hóa đơn, chứng từ.
Điều 10. Nội dung hóa đơn gồm: tên hóa đơn, ký hiệu mẫu số hóa đơn, ký hiệu hóa đơn, số hóa đơn, tên, địa chỉ, mã số thuế của người bán, tên, địa chỉ, mã số thuế của người mua, tên hàng hóa dịch vụ, đơn vị tính, số lượng, đơn giá, thành tiền, chữ ký.
Điều 13. Hóa đơn điện tử: người bán phải lập hóa đơn điện tử kể từ thời điểm hàng hóa dịch vụ được cung cấp.
Điều 19. Thời điểm lập hóa đơn đối với hàng hóa là thời điểm chuyển giao quyền sở hữu hoặc quyền sử dụng hàng hóa cho người mua.""",

    "TT 21/2018 GACP": """Thông tư 21/2018/TT-BYT ngày 12/9/2018 quy định về thực hành tốt nuôi trồng và thu hái cây thuốc (GACP-WHO).
Yêu cầu đối với vùng trồng: đất trồng phải được kiểm tra và đảm bảo không bị ô nhiễm, không sử dụng bùn thải, pH đất phù hợp với từng loài cây thuốc.
Yêu cầu thu hái: thu hái đúng bộ phận dùng, đúng thời điểm, bảo đảm hoạt chất cao nhất.
Đối với atiso (Cynara scolymus L.): thu hoạch cụm hoa khi còn chắc, trước khi nở hoàn toàn. Rễ và lá thu hoạch vào cuối mùa hoa.
Hàm lượng cynarin trong atiso phải đạt tối thiểu 0.1% theo dược liệu khô.""",
}

async def scrape_one(
    client: httpx.AsyncClient,
    url: str,
    topic: str,
) -> dict:
    """Scrape một URL với retry."""
    if USE_MOCK:
        logger.info(f"[MOCK] {topic}")
        await asyncio.sleep(0.1)
        content = next(
            (v for k, v in MOCK_CONTENT.items() if k in topic),
            f"[MOCK] Nội dung mẫu cho: {topic}\nURL: {url}"
        )
        return {"url": url, "topic": topic, "content": content, "status": "mock"}

    async with SEMAPHORE:
        for attempt in range(1, RETRY_MAX + 1):
            try:
                logger.info(f"[{attempt}/{RETRY_MAX}] Scraping: {topic}")
                resp = await client.post(
                    FIRECRAWL_URL,
                    json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
                    headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                raw_md = data.get("data", {}).get("markdown", "") or data.get("markdown", "")
                content = clean_markdown(raw_md)
                if len(content) < 200:
                    logger.warning(f"  ⚠ Nội dung quá ngắn ({len(content)} chars): {topic}")
                logger.info(f"  ✓ {len(content)} chars — {topic}")
                return {"url": url, "topic": topic, "content": content, "status": "success"}
            except httpx.HTTPStatusError as e:
                logger.error(f"  HTTP {e.response.status_code} cho {url}")
                if e.response.status_code == 429:  # rate limit
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.info(f"  Rate limited — chờ {wait:.0f}s")
                    await asyncio.sleep(wait)
                elif attempt == RETRY_MAX:
                    return {"url": url, "topic": topic, "error": str(e), "status": "failed"}
            except Exception as e:
                logger.error(f"  Lỗi: {e}")
                if attempt < RETRY_MAX:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                else:
                    return {"url": url, "topic": topic, "error": str(e), "status": "failed"}
    return {"url": url, "topic": topic, "error": "max retries", "status": "failed"}

def build_chunks(raw_results: list[dict]) -> list[dict]:
    """Chia raw content thành chunks sẵn sàng nạp ChromaDB."""
    chunks = []
    for doc in raw_results:
        if doc["status"] not in ("success", "mock"):
            continue
        for i, chunk in enumerate(chunk_text(doc["content"])):
            chunks.append({
                "id":     f"{doc['topic'][:40].replace(' ','_')}_{i:04d}",
                "topic":  doc["topic"],
                "url":    doc["url"],
                "chunk":  i,
                "text":   chunk,
            })
    return chunks

async def main():
    if USE_MOCK:
        logger.warning("⚠ FIRECRAWL_API_KEY chưa set — chạy MOCK mode")
        logger.warning("  Để scrape thật: export FIRECRAWL_API_KEY=fc-xxxx")

    out_dir = root_path / "src" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_file    = out_dir / "legal_raw.jsonl"
    chunks_file = out_dir / "legal_chunks.jsonl"

    # Priority sort: high → medium → low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    targets_sorted = sorted(SCRAPE_TARGETS, key=lambda t: priority_order.get(t[2], 9))

    logger.info(f"Bắt đầu scrape {len(targets_sorted)} tài liệu pháp lý")
    start = time.time()

    async with httpx.AsyncClient(timeout=35.0) as client:
        tasks = [scrape_one(client, url, topic) for url, topic, _ in targets_sorted]
        results = await asyncio.gather(*tasks)

    # Lưu raw
    ok  = [r for r in results if r["status"] in ("success", "mock")]
    bad = [r for r in results if r["status"] == "failed"]
    with open(raw_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Build và lưu chunks
    chunks = build_chunks(results)
    with open(chunks_file, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    elapsed = time.time() - start
    logger.info(f"")
    logger.info(f"=== KẾT QUẢ ===")
    logger.info(f"  Thành công : {len(ok):3d} / {len(results)}")
    logger.info(f"  Thất bại   : {len(bad):3d}")
    logger.info(f"  Chunks     : {len(chunks):3d} (sẵn sàng ChromaDB)")
    logger.info(f"  Thời gian  : {elapsed:.1f}s")
    logger.info(f"  Raw        : {raw_file}")
    logger.info(f"  Chunks     : {chunks_file}")

    if bad:
        logger.warning("\n  URLs thất bại:")
        for b in bad:
            logger.warning(f"    {b['topic']}: {b.get('error','?')}")

if __name__ == "__main__":
    asyncio.run(main())
