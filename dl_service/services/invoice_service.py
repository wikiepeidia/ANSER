from datetime import datetime
from collections import deque
import cv2

from utils.invoice_processor import parse_products_from_text, extract_products_from_text, load_product_catalogs, build_catalog_index
from config import CATALOG_PATH
from utils.data_processor import normalize_text
from utils.database import save_invoice_to_db, get_invoices_from_db
from utils.logger import get_logger
from services.ocr_service import extract_text_from_image_bytes
from services.layout_service import detect_layout_regions, crop_region, get_layout_training_metrics

logger = get_logger(__name__)

# Storage for invoice history (in-memory),backward compatibility
invoice_history = deque(maxlen=50)

accuracy_stats = {
    'layout_conf_sum': 0.0,
    'layout_conf_count': 0,
    'ocr_precision_sum': 0.0,
    'ocr_precision_count': 0
}

# ── Catalog singleton (loaded once at import time) ─────────────────
_product_catalogs = load_product_catalogs(CATALOG_PATH)
_catalog_index = build_catalog_index(_product_catalogs)
logger.info("[INVOICE_SERVICE] Catalog loaded: %d SKUs from %s", len(_catalog_index), CATALOG_PATH)


def _enrich_with_catalog(products, catalog_index):
    """Match parsed product names against catalog. Keep qty/price/total from structural parser."""
    for product in products:
        raw_name = product.get('product_name', '')
        norm_name = normalize_text(raw_name)
        if len(norm_name) < 3:
            continue
        best_match = None
        best_len = 0
        for entry in catalog_index:
            cat_norm = entry['name_normalized']
            if not cat_norm or len(cat_norm) < 3:
                continue
            if cat_norm in norm_name or norm_name in cat_norm:
                if len(cat_norm) > best_len:
                    best_len = len(cat_norm)
                    best_match = entry
        if best_match and best_len >= 4:
            product['product_id'] = best_match['product'].get('id')
            product['product_name'] = best_match['product'].get('name', raw_name)
    matched = sum(1 for p in products if p.get('product_id'))
    logger.info("[INVOICE_SERVICE] Catalog enrichment: %d/%d products matched", matched, len(products))


def process_invoice_image(image):
   
    logger.info(f"[MODEL 1] *** ENTRY POINT *** Processing invoice image (shape: {image.shape})")

    invoice_id = f"INV_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    invoice_data = {
        'invoice_id': invoice_id,
        'date': datetime.now().isoformat(),
        'products': [],
        'total_amount': 0.0,
        'detection_confidence': 0.0,
        'products_source': 'ocr',
        'layout_regions': {}
    }

    layout_regions = {}
    layout_score_actual = None
    try:
        detected = detect_layout_regions(image)
        if detected:
            avg_conf = sum(region.confidence for region in detected.values()) / len(detected)
            layout_score_actual = round(avg_conf, 4)
            invoice_data['detection_confidence'] = layout_score_actual
            layout_regions = {
                name: {'bbox': region.bbox, 'confidence': region.confidence}
                for name, region in detected.items()
            }
        invoice_data['layout_regions'] = layout_regions
        logger.info("[INVOICE_SERVICE] Layout regions detected: %s", list(layout_regions.keys()))
    except Exception as exc:
        logger.warning("[LAYOUT] Detector failed: %s", exc, exc_info=True)
        invoice_data['layout_warning'] = str(exc)

    table_region = layout_regions.get('table')
    table_image = crop_region(image, tuple(table_region['bbox'])) if table_region else image

    # Run OCR: Brain VLM (Qwen2-VL) → PaddleOCR → EasyOCR → Tesseract
    logger.info("[OCR] Starting OCR extraction attempt...")
    ocr_precision = None
    try:
        ok, buffer = cv2.imencode('.png', table_image)
        if ok:
            logger.info("[INVOICE_SERVICE] Table crop encoded OK, buffer size=%d bytes", len(buffer.tobytes()))
            ocr_result = extract_text_from_image_bytes(buffer.tobytes())
            logger.info(
                "[INVOICE_SERVICE] OCR result: success=%s, backend=%s, text_len=%d, error=%s",
                ocr_result.get('success'),
                ocr_result.get('backend'),
                len(ocr_result.get('text', '')),
                ocr_result.get('error'),
            )
            if ocr_result.get('success'):
                invoice_data['ocr_text'] = text = ocr_result.get('text', '').strip()
                invoice_data['ocr_backend'] = ocr_result.get('backend')
                invoice_data['ocr_confidence'] = float(ocr_result.get('confidence', 0.0))
                
                logger.debug("[INVOICE_SERVICE] Full OCR text:\n%s", text)

                # Step 1: Structural parsing — correct qty/price/total via LINE_REGEX
                parsed_products = parse_products_from_text(text)
                logger.info("[INVOICE_SERVICE] Structural parser found %d products", len(parsed_products))

                # Step 2: Enrich with catalog names/IDs (keeps parsed numbers)
                if parsed_products and _catalog_index:
                    _enrich_with_catalog(parsed_products, _catalog_index)
                elif not parsed_products and _catalog_index:
                    catalog_products, _ = extract_products_from_text(text, _catalog_index)
                    if catalog_products:
                        parsed_products = catalog_products
                        logger.info(
                            "[INVOICE_SERVICE] Fallback catalog extraction found %d products",
                            len(catalog_products),
                        )

                logger.info("[INVOICE_SERVICE] Parser found %d products", len(parsed_products))
                if parsed_products:
                    for idx, p in enumerate(parsed_products[:3], 1):
                        logger.debug(
                            "[INVOICE_SERVICE] Parsed product %d: %s qty=%s unit=%s total=%s",
                            idx,
                            p['product_name'][:30],
                            p['quantity'],
                            p['unit_price'],
                            p['line_total'],
                        )
                logger.info(
                    "[OCR] Backend=%s confidence=%.3f parsed_items=%d",
                    invoice_data['ocr_backend'],
                    invoice_data['ocr_confidence'],
                    len(parsed_products)
                )
                if parsed_products:
                    invoice_data['products'] = []
                    total = 0.0
                    for idx, product in enumerate(parsed_products, start=1):
                        qty = max(1, int(round(product['quantity'])))
                        unit_price = float(product['unit_price'])
                        line_total = float(product['line_total']) or (unit_price * qty)
                        total += line_total
                        invoice_data['products'].append({
                            'product_id': f"OCR_{idx}",
                            'product_name': product['product_name'],
                            'quantity': qty,
                            'unit_price': round(unit_price, 2),
                            'line_total': round(line_total, 2)
                        })
                    invoice_data['total_amount'] = round(total, 2)
                    ocr_precision = _estimate_ocr_precision(text, len(parsed_products))
                else:
                    invoice_data['products_source'] = 'ocr'
                    invoice_data['ocr_warning'] = 'OCR succeeded but no line items detected'
                    logger.info("[INVOICE_SERVICE] Parser returned 0 products from text length %d", len(text))
            else:
                invoice_data['products_source'] = 'ocr'
                invoice_data['ocr_error'] = ocr_result.get('error', 'OCR failed')
                logger.warning("[INVOICE_SERVICE] OCR failed: %s", ocr_result.get('error'))
        else:
            invoice_data['products_source'] = 'ocr'
            invoice_data['ocr_error'] = 'Failed to encode image for OCR'
            logger.warning("[INVOICE_SERVICE] cv2.imencode failed")
    except Exception as exc:
        logger.error(f"[OCR] Exception during OCR processing: {exc}", exc_info=True)
        invoice_data['products_source'] = 'ocr'
        invoice_data['ocr_error'] = str(exc)

    if not invoice_data['products']:
        invoice_data['products_source'] = 'layout'

    if not invoice_data['detection_confidence']:
        invoice_data['detection_confidence'] = 0.75

    logger.info(
        "[INVOICE_SERVICE] OCR complete. products_source=%s, product_count=%d",
        invoice_data.get('products_source'),
        len(invoice_data.get('products', [])),
    )

    invoice_metrics = {
        'layout_confidence': layout_score_actual if layout_score_actual is not None else invoice_data['detection_confidence'],
        'ocr_precision': round(ocr_precision, 4) if ocr_precision is not None else 0.0,
        'ocr_backend_confidence': invoice_data.get('ocr_confidence', 0.0)
    }
    invoice_data['metrics'] = invoice_metrics
    _record_accuracy_metrics(layout_score_actual, ocr_precision)
    
    # Store last 50 invoices + Create time-series sequences
    try:
        save_invoice_to_db(invoice_data)
        logger.info(f"[DATABASE] Saved Y1 output to INVOICE HISTORY DATABASE: {invoice_data['invoice_id']}")
    except Exception as e:
        logger.warning(f"[DATABASE] Failed to save to database: {e}")

    # save to memory history (backward compatibility)
    invoice_history.append(invoice_data)

    logger.info(f"[MODEL 1] Invoice detection completed:")
    logger.info(f" - Invoice ID: {invoice_data['invoice_id']}")
    # Store name removed from logging
    logger.info(f" - Products detected: {len(invoice_data['products'])}")
    logger.info(f" - Total amount: {int(invoice_data['total_amount']):,} VND")
    logger.info(f" - Confidence: {invoice_data['detection_confidence']:.3f}")
    logger.info(f" - Total in DATABASE: {len(get_invoices_from_db(limit=1000))}")

    return invoice_data


def format_invoice_response(invoice_data):

    product_lines = [
        f"{product.get('product_name', 'Unknown')} - {product.get('quantity', 0)}"
        for product in invoice_data.get('products', [])
    ]

    recognized_text = invoice_data.get('ocr_text')
    if not recognized_text:
        recognized_text = (
            f"Invoice ID: {invoice_data['invoice_id']}\n\n"
            f"Products:\n" + "\n".join(product_lines) + 
            f"\n\nTotal: {int(invoice_data['total_amount']):,} VND"
        )

    response = {
        'success': True,
        'recognized_text': recognized_text,
        'confidence': invoice_data['detection_confidence'],
        'data': invoice_data,
        'total_history_count': len(invoice_history)
    }

    response['products_source'] = invoice_data.get('products_source', 'ocr')

    if invoice_data.get('ocr_backend'):
        response['ocr_backend'] = invoice_data['ocr_backend']
        response['ocr_confidence'] = invoice_data.get('ocr_confidence', 0.0)
    if invoice_data.get('ocr_error') and not invoice_data.get('ocr_text'):
        response['ocr_error'] = invoice_data['ocr_error']

    accuracy_payload = get_accuracy_metrics()
    if invoice_data.get('metrics') or accuracy_payload:
        response['metrics'] = {
            'invoice': invoice_data.get('metrics'),
            **(accuracy_payload or {})
        }

    return response


def get_invoice_history(limit=10):
    
    try:
        # Database
        db_invoices = get_invoices_from_db(limit=limit)

        return {
            'success': True,
            'count': len(db_invoices),
            'invoices': db_invoices,
            'source': 'database'
        }
    except Exception as e:
        logger.warning(f"Failed to get from database, using memory: {e}")
        # Fallback to memory
        return {
            'success': True,
            'count': len(invoice_history),
            'invoices': invoice_history[-limit:] if limit else invoice_history,
            'source': 'memory'
        }


def clear_invoice_history():
    
    invoice_history.clear()

    try:
        from utils.database import clear_database
        clear_database()
        logger.info("Cleared invoice history from database and memory")
    except Exception as e:
        logger.warning(f"Failed to clear database: {e}")

    return {
        'success': True,
        'message': 'Invoice history cleared from database and memory'
    }


def get_history_count():
    
    return len(invoice_history)


def _record_accuracy_metrics(layout_score: float | None, ocr_precision: float | None):
    if layout_score is not None:
        accuracy_stats['layout_conf_sum'] += layout_score
        accuracy_stats['layout_conf_count'] += 1
    if ocr_precision is not None:
        accuracy_stats['ocr_precision_sum'] += max(0.0, min(1.0, ocr_precision))
        accuracy_stats['ocr_precision_count'] += 1


def _estimate_ocr_precision(text: str, detected_items: int) -> float:
    if not text:
        return 0.0
    lines = [line for line in text.splitlines() if line.strip()]
    signal_lines = [line for line in lines if any(ch.isdigit() for ch in line)]
    denom = len(signal_lines) or len(lines) or 1
    precision = min(1.0, detected_items / denom)
    return round(precision, 4)


def get_accuracy_metrics():
    running = {}
    if accuracy_stats['layout_conf_count']:
        running['layout_confidence_avg'] = round(
            accuracy_stats['layout_conf_sum'] / accuracy_stats['layout_conf_count'], 4
        )
    if accuracy_stats['ocr_precision_count']:
        running['ocr_precision_avg'] = round(
            accuracy_stats['ocr_precision_sum'] / accuracy_stats['ocr_precision_count'], 4
        )

    payload = {}
    if running:
        payload['running_average'] = running

    training_metrics = get_layout_training_metrics()
    if training_metrics:
        payload['layout_training'] = training_metrics

    return payload
