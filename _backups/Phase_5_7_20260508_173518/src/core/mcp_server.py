class MCPServer:
    @staticmethod
    def calculate_vat(base_price: float, is_reduced: bool = True) -> dict:
        """
        Calculate VAT per Decree 72/2024/NĐ-CP (typically 8% if reduced, else 10%).
        """
        tax_rate = 0.08 if is_reduced else 0.10
        tax_amount = base_price * tax_rate
        total_price = base_price + tax_amount
        return {
            "base_price": base_price,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_price": total_price
        }

    @staticmethod
    def validate_invoice_total(items: list[dict], stated_total: float) -> dict:
        """
        Validates invoice total by summing up item prices and applying VAT.
        items: [{"price": float, "qty": int, "is_reduced_vat": bool}]
        """
        calculated_total = 0.0
        for item in items:
            base = item.get("price", 0) * item.get("qty", 1)
            is_reduced = item.get("is_reduced_vat", True)
            vat_result = MCPServer.calculate_vat(base, is_reduced)
            calculated_total += vat_result["total_price"]
        
        is_valid = abs(calculated_total - stated_total) < 0.01
        return {
            "calculated_total": calculated_total,
            "stated_total": stated_total,
            "is_valid": is_valid,
            "difference": abs(calculated_total - stated_total)
        }
