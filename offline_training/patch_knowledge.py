"""
patch_knowledge.py — NGÀY 6, bước 1
Thêm ngưỡng tương đồng vào KnowledgeBase.search()

VẤN ĐỀ:
  search() luôn trả về top_k tài liệu bất kể điểm reranker.
  Hỏi "Fibonacci là gì" → không có tài liệu liên quan → vẫn nhồi
  3 đoạn chính sách cửa hàng vào ngữ cảnh → model sinh chuỗi vô nghĩa.

GIẢI PHÁP:
  Cross-encoder ms-marco-MiniLM cho điểm logit:
    > 0   : liên quan
    < -5  : hoàn toàn không liên quan
  Lọc bỏ tài liệu dưới ngưỡng, trả chuỗi rỗng còn hơn nhồi rác.

CHẠY:  python offline_training/patch_knowledge.py
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGET = ROOT / "src" / "core" / "knowledge.py"

OLD = """        # Stage 2: Cross-Encoder Reranking
        pairs = [[query, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)

        # Sort by score
        scored_docs = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        best_docs = [doc for score, doc in scored_docs[:top_k]]

        return "\\n\\n---\\n\\n".join(best_docs)"""

NEW = '''        # Stage 2: Cross-Encoder Reranking
        pairs = [[query, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)

        # Sort by score
        scored_docs = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)

        # Stage 3: Lọc theo ngưỡng liên quan
        # Cross-encoder ms-marco cho logit: dương = liên quan, âm sâu = không liên quan.
        # Không lọc thì câu hỏi ngoài lĩnh vực vẫn nhận được tài liệu ngẫu nhiên
        # -> model bị nhồi ngữ cảnh sai -> sinh nội dung vô nghĩa.
        relevant = [(s, d) for s, d in scored_docs if s >= self.relevance_threshold]

        if not relevant:
            logger.info(
                "KB: không có tài liệu vượt ngưỡng %.1f (điểm cao nhất %.2f) — trả rỗng",
                self.relevance_threshold,
                scored_docs[0][0] if scored_docs else float("nan"),
            )
            return ""

        best_docs = [doc for _, doc in relevant[:top_k]]
        logger.info(
            "KB: %d/%d tài liệu vượt ngưỡng, điểm cao nhất %.2f",
            len(relevant), len(scored_docs), relevant[0][0],
        )
        return "\\n\\n---\\n\\n".join(best_docs)'''


def main():
    if not TARGET.exists():
        print(f"❌ Không thấy {TARGET}")
        return

    src = TARGET.read_text(encoding="utf-8")

    if "relevance_threshold" in src:
        print("✓ Đã vá rồi — bỏ qua")
        return

    if OLD not in src:
        print("❌ Không khớp đoạn code cần sửa.")
        print("   Có thể file đã bị thay đổi. Kiểm tra thủ công đoạn Stage 2.")
        return

    # Backup
    bak = TARGET.with_suffix(".py.bak")
    shutil.copy(TARGET, bak)
    print(f"✓ Backup: {bak.name}")

    src = src.replace(OLD, NEW)

    # Thêm thuộc tính relevance_threshold vào __init__
    m = re.search(r"(def __init__\(self[^\)]*\):\n)", src)
    if m:
        insert_at = m.end()
        # Tìm dòng đầu tiên trong body để lấy đúng thụt lề
        rest = src[insert_at:]
        indent_m = re.match(r"(\s+)", rest)
        indent = indent_m.group(1) if indent_m else "        "
        attr = (
            f"{indent}# Ngưỡng điểm cross-encoder để coi là liên quan.\n"
            f"{indent}# Tăng lên nếu vẫn lọt tài liệu lạc đề, giảm nếu bỏ sót.\n"
            f"{indent}self.relevance_threshold = float(\n"
            f"{indent}    os.getenv(\"KB_RELEVANCE_THRESHOLD\", \"0.0\")\n"
            f"{indent})\n"
        )
        src = src[:insert_at] + attr + src[insert_at:]
        print("✓ Thêm self.relevance_threshold vào __init__")

    # Đảm bảo có import os và logger
    if not re.search(r"^import os$", src, re.M):
        src = "import os\n" + src
        print("✓ Thêm import os")

    if "logger" not in src.split("class ")[0]:
        lines = src.split("\n")
        # Chèn logger sau khối import
        for i, l in enumerate(lines):
            if l.startswith("class ") or l.startswith("def "):
                lines.insert(i, 'logger = logging.getLogger("projecta.knowledge")\n')
                break
        src = "\n".join(lines)
        if not re.search(r"^import logging$", src, re.M):
            src = "import logging\n" + src
        print("✓ Thêm logger")

    TARGET.write_text(src, encoding="utf-8")
    print(f"\n✅ Đã vá {TARGET.name}")
    print("\n   Điều chỉnh ngưỡng bằng biến môi trường nếu cần:")
    print("     export KB_RELEVANCE_THRESHOLD=0.0    # mặc định")
    print("     export KB_RELEVANCE_THRESHOLD=2.0    # chặt hơn")
    print("     export KB_RELEVANCE_THRESHOLD=-2.0   # nới lỏng")


if __name__ == "__main__":
    main()
