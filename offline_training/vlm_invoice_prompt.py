"""
vlm_invoice_prompt.py — Prompt cho TẦNG 1 (Qwen2-VL-2B)

Không cần training — chỉ prompt engineering.
Dùng với engine.generate_vision(image_path, prompt).

TÍCH HỢP VÀO BODY:
  from offline_training.vlm_invoice_prompt import VLM_INVOICE_PROMPT
  raw = await engine.generate_vision(image_path, VLM_INVOICE_PROMPT, max_new_tokens=1536)
  vlm_json = parse_vlm_output(raw)
  # rồi đưa vlm_json sang Qwen2.5-7B (tầng 2) để verify + match + action
"""
import json
import re

VLM_INVOICE_PROMPT = """Đọc hóa đơn trong ảnh và trích xuất thành JSON.

Trả về ĐÚNG định dạng sau, không thêm giải thích:

{
  "supplier_name": "<tên nhà cung cấp>",
  "invoice_code": "<số hóa đơn>",
  "invoice_date": "<YYYY-MM-DD>",
  "items": [
    {
      "line": 1,
      "name": "<tên sản phẩm đầy đủ>",
      "quantity": <số>,
      "unit": "<đơn vị: hộp/chai/kg/thùng...>",
      "unit_price": <số, không dấu phân cách>,
      "amount": <số, không dấu phân cách>,
      "confidence": <0.0-1.0>
    }
  ],
  "subtotal": <số>,
  "vat_rate": <5, 8 hoặc 10>,
  "vat_amount": <số>,
  "total_amount": <số>,
  "overall_confidence": <0.0-1.0>
}

QUY TẮC:
- Đọc CHÍNH XÁC những gì thấy trên ảnh, KHÔNG tự tính toán hay sửa số
- Nếu một ô bị mờ/che, vẫn ghi giá trị đọc được và hạ confidence xuống dưới 0.7
- Nếu không đọc được hoàn toàn, ghi null và confidence 0.0
- Số tiền bỏ hết dấu chấm/phẩy: "1.250.000" → 1250000
- Ngày tháng chuyển sang YYYY-MM-DD
- confidence phản ánh độ rõ nét của chữ, không phải độ hợp lý của số liệu
"""


def parse_vlm_output(raw: str) -> dict | None:
    """Parse output của VLM thành dict. Trả về None nếu không parse được."""
    # Markdown fence
    for m in re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Brace matching
    depth, start = 0, -1
    for i, c in enumerate(raw):
        if c == '{':
            if depth == 0:
                start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(raw[start:i + 1])
                except Exception:
                    start = -1
    return None


def quick_sanity_check(vlm: dict) -> list[str]:
    """
    Kiểm tra nhanh trước khi gửi sang tầng 2 — tiết kiệm 1 lần gọi LLM
    nếu dữ liệu rõ ràng không dùng được.
    """
    issues = []
    if not vlm:
        return ["không parse được JSON từ VLM"]

    items = vlm.get("items") or []
    if not items:
        issues.append("không có mặt hàng nào")
        return issues

    if (vlm.get("overall_confidence") or 0) < 0.5:
        issues.append(f"overall_confidence quá thấp ({vlm.get('overall_confidence')})")

    for it in items:
        if it.get("quantity") is None or it.get("unit_price") is None:
            issues.append(f"dòng {it.get('line')}: thiếu số lượng hoặc đơn giá")
        if (it.get("confidence") or 0) < 0.4:
            issues.append(f"dòng {it.get('line')}: confidence {it.get('confidence')} quá thấp")

    return issues


# ── Ví dụ tích hợp vào Body ────────────────────────────────────────────────
EXAMPLE_INTEGRATION = '''
# routes/dl_routes.py hoặc core/services/invoice_service.py

from offline_training.vlm_invoice_prompt import (
    VLM_INVOICE_PROMPT, parse_vlm_output, quick_sanity_check
)

async def digitize_invoice(image_path: str, user_id: int):
    engine = ModelEngine()

    # ── TẦNG 1: Qwen2-VL đọc ảnh ──────────────────────────────
    raw = await engine.generate_vision(
        image_path, VLM_INVOICE_PROMPT, max_new_tokens=1536
    )
    vlm_json = parse_vlm_output(raw)

    issues = quick_sanity_check(vlm_json)
    if issues:
        return {"status": "needs_manual_review", "issues": issues, "raw": raw}

    # ── TẦNG 2: Qwen2.5-7B verify + match + sinh action ───────
    prompt = (
        "Từ kết quả Qwen2-VL sau, sau khi đã kiểm tra, hãy sinh JSON action "
        "để tạo phiếu nhập kho trong hệ thống:\\n\\n"
        f"```json\\n{json.dumps(vlm_json, ensure_ascii=False, indent=1)}\\n```"
    )
    answer = await engine.generate_chat(prompt)

    # AgentMiddleware parse JSON action rồi ghi DB
    return middleware.process_ai_response(answer, user_id)
'''

if __name__ == "__main__":
    print("VLM_INVOICE_PROMPT:")
    print("-" * 60)
    print(VLM_INVOICE_PROMPT)
    print("-" * 60)
    print("\nVí dụ tích hợp:")
    print(EXAMPLE_INTEGRATION)
