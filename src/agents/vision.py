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
    MANUFACTURING_METADATA_FIELDS = (
        "farmer",
        "region_grown",
        "part",
        "form",
        "gacp_cert",
        "doc_no",
        "customer_code",
        "region",
        "deadline",
    )

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
        "manufacturing": (
            "Bạn là hệ thống trích xuất chứng từ sản xuất. Ảnh có thể là MỘT trong hai loại "
            "chứng từ: (1) phiếu nhập nguyên liệu từ nông dân/HTX, hoặc (2) đơn đặt hàng của "
            "khách hàng. Đọc ảnh và trả về DUY NHẤT một JSON hợp lệ, KHÔNG kèm giải thích, "
            "với ĐÚNG các trường và kiểu sau (đây là mô tả kiểu, không phải giá trị mẫu):\n"
            "- items: mảng các dòng hàng; mỗi dòng có items[].sku (chuỗi hoặc null), "
            "items[].name (chuỗi), items[].qty (số), items[].unit_price (số).\n"
            "- total: số.\n"
            "- farmer, region_grown, part, form, gacp_cert, doc_no, customer_code, region, "
            "deadline: chuỗi hoặc null.\n"
            "TẤT CẢ 11 khóa cấp cao sau PHẢI luôn xuất hiện trong JSON, không được bỏ bất kỳ khóa nào: "
            "items, total, farmer, region_grown, part, form, gacp_cert, doc_no, customer_code, "
            "region, deadline.\n"
            "Ánh xạ nhãn thường gặp, kể cả bản không dấu hoặc khác chữ hoa/thường:\n"
            "- Số chứng từ / So chung tu -> doc_no.\n"
            "- Mã khách hàng / Ma Khach hang -> customer_code.\n"
            "- Khu vực giao / Khu vuc giao -> region.\n"
            "- Hạn giao / Han giao -> deadline.\n"
            "- Mã SKU sản phẩm / Ma SKU san pham -> items[].sku.\n"
            "- Tên sản phẩm / Ten san pham -> items[].name.\n"
            "- Số lượng đặt / So luong dat -> items[].qty.\n"
            "- Đơn giá (trước thuế) / Don gia (truoc thue) -> items[].unit_price.\n"
            "- Tổng cộng thanh toán / Tong cong thanh toan -> total.\n"
            "- Nông dân hoặc HTX -> farmer; vùng trồng -> region_grown; bộ phận cây -> part; "
            "dạng tươi/khô -> form; chứng nhận GACP -> gacp_cert.\n"
            "Quy tắc: chỉ điền các trường THỰC SỰ xuất hiện trên chứng từ, các trường còn lại "
            "để null — KHÔNG suy đoán hay bịa thông tin. 'unit_price' là ĐƠN GIÁ trước thuế; "
            "'total' là tổng tiền ghi trên chứng từ. Mọi số tiền là số nguyên VND, không dùng "
            "dấu phân cách hàng nghìn. Nếu ảnh mờ/không đọc được: trả về items: [], total: 0, "
            "và MỌI trường khác là null — TUYỆT ĐỐI không bịa dữ liệu."
        ),
        "manufacturing_metadata": (
            "Bạn là hệ thống trích xuất metadata chứng từ sản xuất. Ảnh có thể là "
            "phiếu nhập nguyên liệu từ nông dân/HTX hoặc đơn đặt hàng khách hàng. "
            "Chỉ đọc phần thông tin nhận diện/chứng từ và trả về DUY NHẤT một JSON hợp lệ, "
            "KHÔNG kèm giải thích. Chỉ dùng đúng 9 khóa cấp cao sau: farmer, region_grown, "
            "part, form, gacp_cert, doc_no, customer_code, region, deadline. Tất cả 9 khóa "
            "phải xuất hiện; giá trị là chuỗi đọc được hoặc null. Không trả về items, SKU, "
            "số lượng, đơn giá hay total trong lượt này.\n"
            "Ánh xạ nhãn thường gặp, kể cả bản không dấu hoặc khác chữ hoa/thường:\n"
            "- Nông dân / Nong dan / HTX -> farmer.\n"
            "- Vùng trồng / Vung trong -> region_grown.\n"
            "- Bộ phận cây / Bo phan cay -> part.\n"
            "- Dạng tươi/khô / Dang tuoi/kho -> form.\n"
            "- Chứng nhận GACP / Chung nhan GACP -> gacp_cert.\n"
            "- Số chứng từ / So chung tu -> doc_no.\n"
            "- Mã khách hàng / Ma Khach hang -> customer_code.\n"
            "- Khu vực giao / Khu vuc giao -> region.\n"
            "- Hạn giao / Han giao -> deadline.\n"
            "Chỉ điền thông tin THỰC SỰ xuất hiện trên ảnh. Trường không xuất hiện hoặc "
            "không đọc được phải là null — KHÔNG suy đoán hay bịa thông tin."
        ),
    }

    def __init__(self, engine):
        if engine is None:
            raise ValueError("VisionAgent cần một ModelEngine instance")
        self.engine = engine
        logger.info("VisionAgent ready (dùng chung Qwen2-VL-2B của ModelEngine)")

    def _prompt_for(self, task_hint: str) -> str:
        task_hint = (task_hint or "").lower()
        if "manufacturing_metadata" in task_hint:
            return self.PROMPTS["manufacturing_metadata"]
        if "manufacturing" in task_hint or "san_xuat" in task_hint or "sanxuat" in task_hint:
            return self.PROMPTS["manufacturing"]
        if "invoice" in task_hint or "hoa_don" in task_hint or "hóa đơn" in task_hint:
            return self.PROMPTS["invoice"]
        if "ocr" in task_hint:
            return self.PROMPTS["ocr"]
        return self.PROMPTS["caption"]

    @staticmethod
    def _normalize_json_object(parsed):
        """Accept a mapping or an unambiguous one-mapping wrapper only."""
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
            return parsed[0]
        return None

    @classmethod
    def _merge_manufacturing_metadata(cls, primary: dict, metadata: dict) -> dict:
        """Fill missing top-level metadata while keeping primary line facts authoritative."""
        merged = dict(primary)
        for field in cls.MANUFACTURING_METADATA_FIELDS:
            primary_value = merged.get(field)
            secondary_value = metadata.get(field)
            primary_present = primary_value is not None and not (
                isinstance(primary_value, str) and not primary_value.strip()
            )
            secondary_present = secondary_value is not None and not (
                isinstance(secondary_value, str) and not secondary_value.strip()
            )
            if not primary_present and secondary_present:
                merged[field] = secondary_value
        return merged

    async def analyze_image(self, image_path: str, task_hint: str = "caption") -> str:
        """Trả về text. task_hint ∈ {'caption', 'ocr', 'invoice', 'manufacturing'}."""
        prompt = self._prompt_for(task_hint)
        th = (task_hint or "").lower()
        max_tokens = 1024 if ("ocr" in th or "invoice" in th or "manufacturing" in th) else 512
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

    async def extract_manufacturing_invoice(self, image_path: str) -> dict:
        """
        Trích xuất chứng từ sản xuất (nhập nguyên liệu HOẶC đơn khách hàng) ra JSON
        đã parse từ output của VLM. Trả {'error': ...} nếu không đọc/parse được —
        KHÔNG bịa số (thin sibling of extract_invoice, same never-fabricate pattern).
        """
        primary_raw = await self.analyze_image(image_path, task_hint="manufacturing")
        if isinstance(primary_raw, str) and primary_raw.startswith("Error"):
            return {"error": primary_raw}
        try:
            repaired = repair_json(primary_raw, return_objects=True)
            parsed = self._normalize_json_object(repaired)
            if parsed is not None:
                missing_keys = sorted({"items", "total"} - parsed.keys())
                if missing_keys:
                    logger.warning(
                        "Manufacturing VLM JSON missing required keys %s; parsed keys=%s",
                        missing_keys,
                        sorted(parsed.keys()),
                    )
                    return {
                        "error": "VLM JSON thiếu trường bắt buộc: " + ", ".join(missing_keys),
                        "raw": primary_raw,
                    }
            else:
                return {"error": "VLM không trả JSON object", "raw": primary_raw}
        except Exception as exc:
            return {"error": f"parse_failed: {exc}", "raw": primary_raw}

        metadata_raw = await self.analyze_image(
            image_path,
            task_hint="manufacturing_metadata",
        )
        if isinstance(metadata_raw, str) and metadata_raw.startswith("Error"):
            logger.warning("Manufacturing metadata pass failed; keeping primary extraction")
            return parsed

        try:
            repaired_metadata = repair_json(metadata_raw, return_objects=True)
            metadata = self._normalize_json_object(repaired_metadata)
        except Exception as exc:
            logger.warning(
                "Manufacturing metadata JSON parse failed; keeping primary extraction: %s",
                exc,
            )
            return parsed
        if metadata is None:
            logger.warning(
                "Manufacturing metadata VLM did not return a JSON object; keeping primary extraction"
            )
            return parsed

        return self._merge_manufacturing_metadata(parsed, metadata)
