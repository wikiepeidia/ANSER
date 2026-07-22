# src/agents/vision.py
"""
VisionAgent — lớp mỏng bọc quanh ModelEngine.generate_vision (Qwen2-VL-2B).

MỘT model VLM duy nhất cho cả 3 vai trò (đã LOẠI BỎ Florence-2):
  1. caption  — mô tả ảnh bằng tiếng Việt
  2. ocr      — trích xuất văn bản thô
  3. invoice  — trích xuất hóa đơn ra JSON có cấu trúc (cho luồng nhập kho)

VisionAgent KHÔNG tự load model; nó dùng chung Qwen2-VL-2B do ModelEngine sở hữu,
nên không còn cảnh nạp 2 model vision song song.
"""
import logging

from json_repair import repair_json

logger = logging.getLogger("projecta.agents.vision")


class VisionAgent:
    PROMPTS = {
        "caption": "Mô tả chi tiết nội dung hình ảnh này bằng tiếng Việt.",
        "ocr": (
            "Trích xuất TOÀN BỘ văn bản xuất hiện trong ảnh. "
            "Giữ nguyên thứ tự dòng và dấu tiếng Việt. "
            "Chỉ trả về văn bản, không thêm giải thích."
        ),
        "invoice": (
            "Bạn là hệ thống trích xuất hóa đơn. Đọc ảnh hóa đơn và trả về DUY NHẤT "
            "một JSON hợp lệ, KHÔNG kèm giải thích, đúng schema:\n"
            '{"items": [{"name": "string", "price": 0, "qty": 1}], "total": 0}\n'
            "Quy tắc: 'price' là ĐƠN GIÁ trước thuế; 'total' là tổng tiền ghi trên hóa đơn "
            "(đã gồm thuế). Mọi số tiền là số nguyên VND, không dùng dấu phân cách hàng nghìn. "
            "Bỏ qua dòng nào không đọc được."
        ),
    }

    def __init__(self, engine):
        if engine is None:
            raise ValueError("VisionAgent cần một ModelEngine instance")
        self.engine = engine
        logger.info("VisionAgent ready (dùng chung Qwen2-VL-2B của ModelEngine)")

    def _prompt_for(self, task_hint: str) -> str:
        task_hint = (task_hint or "").lower()
        if "invoice" in task_hint or "hoa_don" in task_hint or "hóa đơn" in task_hint:
            return self.PROMPTS["invoice"]
        if "ocr" in task_hint:
            return self.PROMPTS["ocr"]
        return self.PROMPTS["caption"]

    async def analyze_image(self, image_path: str, task_hint: str = "caption") -> str:
        """Trả về text. task_hint ∈ {'caption', 'ocr', 'invoice'}."""
        prompt = self._prompt_for(task_hint)
        th = (task_hint or "").lower()
        max_tokens = 1024 if ("ocr" in th or "invoice" in th) else 512
        try:
            return await self.engine.generate_vision(image_path, prompt, max_new_tokens=max_tokens)
        except Exception as exc:
            logger.exception("Vision inference failed: %s", exc)
            return f"Error analyzing image: {exc}"

    async def extract_invoice(self, image_path: str) -> dict:
        """
        Vai trò 2 (OCR hóa đơn): trả dict {items, total} đã parse từ JSON của VLM.
        Trả {'error': ...} nếu không đọc/parse được — KHÔNG bịa số.
        """
        raw = await self.analyze_image(image_path, task_hint="invoice")
        if isinstance(raw, str) and raw.startswith("Error"):
            return {"error": raw}
        try:
            parsed = repair_json(raw, return_objects=True)
            if isinstance(parsed, dict):
                return parsed
            return {"error": "VLM không trả JSON object", "raw": raw}
        except Exception as exc:
            return {"error": f"parse_failed: {exc}", "raw": raw}