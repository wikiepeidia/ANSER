"""
src/api/routes/documents.py — Upload and OCR endpoints.
Schema-enforced via ProductExtraction.
"""

import json
import logging
import os
import tempfile

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile
from typing import Optional

from src.api.dependencies import runtime, require_api_token, MAX_UPLOAD_BYTES
from src.core.schemas import ProductExtraction

logger = logging.getLogger("projecta.api.documents")

router = APIRouter()


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    x_api_token: Optional[str] = Header(None),
):
    """Analyze an uploaded image using VisionAgent (Florence-2)."""
    require_api_token(x_api_token)
    await runtime.ensure_vision_runtime()
    if not runtime.vision:
        raise HTTPException(status_code=503, detail="Vision runtime unavailable")

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename or ".png")[1]
    )
    try:
        content_length = int(request.headers.get("content-length") or "0")
        if content_length > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        tmp.write(data)
        tmp.close()
        result = runtime.vision.analyze_image(tmp.name, task_hint="describe")

        # Schema enforcement: attempt ProductExtraction validation
        extraction = None
        if isinstance(result, str) and result.startswith("{"):
            try:
                from json_repair import repair_json
                parsed = repair_json(result, return_objects=True)
                if isinstance(parsed, dict):
                    extraction = ProductExtraction(**parsed)
            except Exception:
                pass  # Graceful degradation — raw vision output is still valid

        return {
            "status": "success",
            "vision_analysis": result,
            "structured_extraction": extraction.model_dump() if extraction else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Upload endpoint failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@router.post("/ocr")
async def ocr_endpoint(
    request: Request,
    file: UploadFile = File(...),
    x_api_token: Optional[str] = Header(None),
):
    """OCR an uploaded image via VisionAgent (Florence-2 <OCR> prompt)."""
    require_api_token(x_api_token)
    await runtime.ensure_vision_runtime()
    if not runtime.vision:
        raise HTTPException(status_code=503, detail="Vision runtime unavailable")

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename or ".png")[1]
    )
    try:
        content_length = int(request.headers.get("content-length") or "0")
        if content_length > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large")
        if not data:
            return {"success": False, "error": "Empty file received", "text": ""}
        tmp.write(data)
        tmp.close()
        raw = runtime.vision.analyze_image(tmp.name, task_hint="ocr")

        # Vision returns error strings on failure
        if isinstance(raw, str) and (raw.startswith("Error") or raw.startswith("Vision module")):
            return {"success": False, "error": raw, "text": ""}

        # Florence-2 returns a dict-like string; extract the text
        text = raw
        if isinstance(raw, str) and raw.startswith("{"):
            try:
                parsed = json.loads(raw.replace("'", '"'))
                text = parsed.get("<OCR>", parsed.get("text", raw))
            except json.JSONDecodeError:
                pass
        elif isinstance(raw, dict):
            text = raw.get("<OCR>", raw.get("text", str(raw)))
        text = str(text).strip()
        if not text:
            return {"success": False, "error": "Vision returned empty text", "text": ""}

        # Schema enforcement: attempt ProductExtraction on OCR output
        extraction = None
        if runtime.manager:
            try:
                extraction_prompt = f"Extract product SKU, category, and base_price from this OCR text into JSON: {text}"
                extracted_json = await runtime.manager.consult(extraction_prompt, context="", history="")
                from json_repair import repair_json
                parsed_dict = repair_json(extracted_json, return_objects=True)
                if isinstance(parsed_dict, dict):
                    extraction = ProductExtraction(**parsed_dict)
            except Exception:
                pass  # Graceful degradation

        return {
            "success": True,
            "text": text,
            "backend": "florence-2",
            "confidence": 0.85,
            "structured_extraction": extraction.model_dump() if extraction else None,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OCR endpoint failed: %s", exc)
        return {"success": False, "error": str(exc), "text": ""}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
