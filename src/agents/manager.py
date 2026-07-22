import logging

import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from src.agents.base import BaseAgent
from src.core.prompts import Prompts

logger = logging.getLogger("projecta.agents.manager")


class SemanticRouter:
    """
    Định tuyến câu hỏi người dùng vào 1 trong 4 nhánh bằng cosine similarity.
    Ví dụ mẫu là tiếng Việt, đúng domain bán lẻ/sản xuất (thay bộ ví dụ benchmark
    tiếng Anh cũ: MBPP/Spider/SQuAD — vốn khiến câu tiếng Việt bị route sai).
    """

    def __init__(self, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 embedder=None):
        # Cho phép TÁI SỬ DỤNG embedder của KnowledgeBase để khỏi nạp trùng model lên VRAM.
        if embedder is not None:
            self.embedder = embedder
            logger.info("SemanticRouter dùng chung embedder có sẵn")
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.embedder = SentenceTransformer(model_name, device=device)
            logger.info("SemanticRouter tự nạp embedder (device=%s)", device)

        # Ví dụ mẫu cho từng route (tiếng Việt, domain thật)
        self.routes = {
            # Sinh workflow tự động hóa -> CoderAgent
            "TECHNICAL": [
                "tạo quy trình tự động hóa gửi báo cáo doanh số mỗi tối",
                "tự động đọc file google sheet rồi gửi email",
                "khi tồn kho dưới ngưỡng thì cảnh báo qua Discord",
                "lên lịch tự động nhập hàng hàng tuần",
                "tạo workflow đồng bộ đơn hàng sang google sheet",
                "gửi thông báo Discord khi có đơn hàng mới",
                "thiết lập tự động hóa xuất báo cáo cuối ngày",
            ],
            # Truy vấn dữ liệu nội bộ (DB cửa hàng) -> SaasAPI
            "DATA_INTERNAL": [
                "còn bao nhiêu hàng tồn kho sản phẩm sữa",
                "doanh thu hôm nay là bao nhiêu",
                "giá bán hiện tại của sản phẩm này là bao nhiêu",
                "tổng số đơn hàng trong tuần này",
                "sản phẩm nào bán chạy nhất tháng này",
                "kiểm tra tồn kho mặt hàng bỉm",
                "báo cáo doanh số tháng trước",
            ],
            # Tra cứu tài liệu / luật / hướng dẫn -> RAG (KnowledgeBase)
            "RETRIEVAL": [
                "quy định về thuế VAT theo nghị định 72 là gì",
                "cách tính thuế giá trị gia tăng cho hàng hóa",
                "chính sách đổi trả hàng của cửa hàng như thế nào",
                "hướng dẫn sử dụng tính năng ví điện tử",
                "điều kiện áp dụng thuế suất 8 phần trăm",
                "tài liệu hướng dẫn tạo phiếu nhập kho",
            ],
            # Hội thoại tự do
            "GENERAL": [
                "xin chào",
                "bạn có khỏe không",
                "cảm ơn bạn nhiều",
                "hôm nay thời tiết thế nào",
                "bạn tên là gì",
                "giúp tôi một chút",
            ],
        }

        # Precompute embeddings cho tất cả ví dụ
        self.route_embeddings = {
            route: self.embedder.encode(examples)
            for route, examples in self.routes.items()
        }

    def route(self, query: str, threshold: float = 0.4) -> str:
        query_vec = self.embedder.encode([query])
        best_route = "GENERAL"
        highest_sim = -1.0

        for route, embeddings in self.route_embeddings.items():
            sims = cosine_similarity(query_vec, embeddings)[0]
            max_sim = float(np.max(sims))
            if max_sim > highest_sim:
                highest_sim = max_sim
                best_route = route

        logger.debug("Router match=%s sim=%.2f", best_route, highest_sim)
        if highest_sim < threshold:
            return "GENERAL"
        return best_route


class ManagerAgent(BaseAgent):
    def __init__(self, engine, memory, kb=None):
        super().__init__(engine, "manager")
        self.kb = kb  # Knowledge Base
        # Dùng chung embedder của KB nếu có -> tránh nạp MiniLM 2 lần lên VRAM
        shared_embedder = getattr(kb, "embedder", None) if kb else None
        self.router = SemanticRouter(embedder=shared_embedder)

    async def analyze_task(self, clean_text: str):
        text = clean_text.lower().strip()
        route = self.router.route(text)
        return {"category": route}

    async def plan_or_ask(self, full_context: str):
        # Prompt sạch (không ChatML) -> để apply_chat_template lo định dạng
        return await self.generate_chat(
            system=Prompts.PLANNER_SYSTEM,
            user=full_context,
            max_new_tokens=256,
            temperature=0.1,
        )

    async def consult(self, task: str, context: str = "", history: str = ""):
        system = Prompts.CONSULT_SYSTEM.format(schema=Prompts.DB_SCHEMA, context=context)
        user = task if not history else f"{history}\n\n{task}"
        return await self.generate_chat(system=system, user=user, max_new_tokens=512)