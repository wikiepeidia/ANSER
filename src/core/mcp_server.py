"""
MCPServer — lớp tính toán tài chính DETERMINISTIC (KHÔNG dùng LLM).

Tính VAT theo Nghị định 72/2024/NĐ-CP và đối chiếu tổng hóa đơn bằng code thuần.
Nguyên tắc deterministic-first: mọi số tiền dùng cho sổ sách phải đi qua đây;
không tin số do LLM/VLM sinh ra mà không tính lại.
"""
from decimal import Decimal, ROUND_HALF_UP

# Thuế suất GTGT (VAT)
VAT_STANDARD = 0.10   # mức chuẩn (mặc định)
VAT_REDUCED = 0.08    # mức giảm theo NĐ 72/2024


def _round_vnd(amount: float) -> int:
    """Làm tròn về số nguyên VND theo round-half-up (không dùng banker's rounding của round())."""
    return int(Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class MCPServer:
    @staticmethod
    def calculate_vat(base_price: float, is_reduced: bool = False) -> dict:
        """
        Tính VAT cho một khoản tiền trước thuế.
        MẶC ĐỊNH 10% (mức chuẩn); chỉ 8% khi is_reduced=True (diện giảm theo NĐ 72/2024).
        """
        tax_rate = VAT_REDUCED if is_reduced else VAT_STANDARD
        base = _round_vnd(base_price)
        tax_amount = _round_vnd(base_price * tax_rate)
        return {
            "base_price": base,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_price": base + tax_amount,
        }

    @staticmethod
    def validate_invoice_total(
        items: list[dict],
        stated_total: float,
        default_is_reduced: bool = False,
        rel_tol: float = 0.001,
        abs_tol: float = 10.0,
    ) -> dict:
        """
        Tính lại tổng hóa đơn từ danh sách item rồi đối chiếu với tổng ghi trên hóa đơn.

        items: [{"name": str, "price": float (đơn giá trước thuế), "qty": int,
                 "is_reduced_vat": bool | None (tùy chọn)}]

        Diện thuế mỗi dòng: nếu item KHÔNG nói rõ (None/khuyết) -> dùng default_is_reduced
        (mặc định False = 10% chuẩn cho cả hóa đơn).

        Hợp lệ khi: |calculated - stated| <= max(abs_tol, rel_tol * stated_total)
          - rel_tol=0.1%  bắt lỗi OCR đọc nhầm chữ số (sai lệch lớn).
          - abs_tol=10 VND bỏ qua nhiễu làm tròn từng dòng.
        2 ngưỡng này nên tinh chỉnh theo quy mô hóa đơn (xem spec Phụ lục, câu hỏi mở #4 —
        hóa đơn sản xuất giá trị lớn có thể cần rel_tol khác hóa đơn bán lẻ).
        """
        calculated_total = 0
        line_breakdown = []

        for item in items:
            price = float(item.get("price", 0) or 0)
            qty = int(item.get("qty", 1) or 1)
            base = price * qty

            is_reduced = item.get("is_reduced_vat")
            if is_reduced is None:
                is_reduced = default_is_reduced

            vat = MCPServer.calculate_vat(base, bool(is_reduced))
            calculated_total += vat["total_price"]
            line_breakdown.append({
                "name": item.get("name", "Unknown"),
                "base": vat["base_price"],
                "tax_rate": vat["tax_rate"],
                "line_total": vat["total_price"],
            })

        stated_total = float(stated_total or 0)
        tolerance = max(abs_tol, rel_tol * stated_total)
        difference = abs(calculated_total - stated_total)
        is_valid = difference <= tolerance

        return {
            "calculated_total": calculated_total,
            "stated_total": _round_vnd(stated_total),
            "difference": _round_vnd(difference),
            "tolerance": _round_vnd(tolerance),
            "is_valid": is_valid,
            "lines": line_breakdown,
        }