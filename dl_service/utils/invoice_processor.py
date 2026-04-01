"""
Invoice Processing Utilities
Handles product extraction and invoice data building
"""
import json
from datetime import datetime
from pathlib import Path
from utils.data_processor import (
    normalize_text, extract_quantity_from_line,
    extract_price_candidates
)
import re
from typing import List, Dict


def load_product_catalogs(catalog_file: Path):
    """Load product catalogs from JSON file"""
    if catalog_file.exists():
        try:
            with catalog_file.open('r', encoding='utf-8') as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
        except (OSError, ValueError) as exc:
            print(f"Warning: Unable to load product catalogs ({exc})")
    return {}


def build_catalog_index(product_catalogs):
    """Build searchable index from product catalogs"""
    catalog_index = []
    for store_key, products in product_catalogs.items():
        for product in products:
            catalog_index.append({
                'store': store_key,
                'product': product,
                'name_normalized': normalize_text(product.get('name', ''))
            })
    return catalog_index


def lookup_catalog_price(catalog_index, product_id=None, product_name=None):
    """Lookup price in catalog by ID or name"""
    if product_id:
        for entry in catalog_index:
            if entry['product'].get('id') == product_id:
                return entry['product'].get('price', 0)
    
    if product_name:
        normalized_name = normalize_text(product_name)
        for entry in catalog_index:
            if entry['name_normalized'] == normalized_name:
                return entry['product'].get('price', 0)
    return 0


def extract_products_from_text(text, catalog_index):
    """Extract products from invoice text"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized_lines = [normalize_text(line) for line in lines]
    
    aggregated = {}
    store_counts = {}
    
    for original_line, normalized_line in zip(lines, normalized_lines):
        for entry in catalog_index:
            name_normalized = entry['name_normalized']
            if not name_normalized or name_normalized not in normalized_line:
                continue
            
            store_key = entry['store']
            store_counts[store_key] = store_counts.get(store_key, 0) + 1
            
            product = entry['product']
            product_id = product.get('id')
            
            if product_id not in aggregated:
                aggregated[product_id] = {
                    'product_id': product_id,
                    'product_name': product.get('name', 'Unknown Product'),
                    'quantity': 0,
                    'unit_price': product.get('price', 0),
                    'line_total': 0
                }
            
            record = aggregated[product_id]
            quantity = extract_quantity_from_line(original_line)
            if quantity:
                record['quantity'] += quantity
            
            prices = extract_price_candidates(original_line)
            if prices:
                candidate_unit = min(prices)
                if candidate_unit < record['unit_price'] * 5 and candidate_unit > 0:
                    record['unit_price'] = candidate_unit
                
                candidate_total = max(prices)
                if record['quantity']:
                    record['line_total'] = max(
                        record['line_total'],
                        candidate_total,
                        record['unit_price'] * record['quantity']
                    )
                else:
                    record['line_total'] = max(record['line_total'], candidate_total)
    
    # Finalize products
    products = []
    for record in aggregated.values():
        if record['quantity'] <= 0:
            record['quantity'] = 1
        if record['unit_price'] <= 0:
            record['unit_price'] = lookup_catalog_price(
                catalog_index,
                record.get('product_id'),
                record.get('product_name')
            ) or 10000
        
        line_estimate = record['unit_price'] * record['quantity']
        record['line_total'] = max(record['line_total'], line_estimate)
        record['quantity'] = int(round(record['quantity']))
        record['unit_price'] = int(round(record['unit_price']))
        record['line_total'] = int(round(record['line_total']))
        products.append(record)
    
    products.sort(key=lambda item: item['line_total'], reverse=True)
    return products[:12], store_counts


def build_invoice_data(ocr_result, catalog_index, product_catalogs, store_name_lookup):
    """Build structured invoice data from OCR result"""
    extracted_text = ocr_result.get('extracted_text', '') or ''
    parsed_data = ocr_result.get('parsed_data') or {}
    
    products, store_counts = extract_products_from_text(extracted_text, catalog_index)
    
    # Use all products from catalog if no products detected
    if not products:
        # Get first catalog (they're all merged now anyway)
        catalog = list(product_catalogs.values())[0][:3] if product_catalogs else []
        products = [{
            'product_id': p.get('id'),
            'product_name': p.get('name'),
            'quantity': 1,
            'unit_price': p.get('price', 0),
            'line_total': p.get('price', 0)
        } for p in catalog]
    
    total_amount = sum(product.get('line_total', 0) for product in products)
    
    invoice_identifier = parsed_data.get('invoice_number') or f"INV_{int(datetime.now().timestamp())}"
    
    return {
        'invoice_id': invoice_identifier,
        'products': products,
        'total_amount': int(round(total_amount)),
        'detection_confidence': float(ocr_result.get('confidence', 0.85)),
        'text_regions_count': max(len(products), 1),
        'extracted_text': extracted_text,
        'date': datetime.now().isoformat()
    }

LINE_REGEX = re.compile(
    r"^(?P<name>.+?)\s+(?P<qty>\d{1,3})\s+(?P<unit>[\d.,]+)(?:\s+(?P<total>[\d.,]+))?$"
)

_CURRENCY_TOKENS = {'vnd', 'vnđ', 'đ', 'd', 'dong'}
_SKIP_LINES = {
    'hoa don', 'invoice', 'san pham', 'product', 'don gia', 'unit price', 
    'thanh tien', 'total', 'so luong', 'quantity', 'ngay', 'date',
    'ten', 'name', 'gia', 'price', 'tong', 'sum'
}


def _parse_int_token(token: str) -> int:
    token = token.strip().rstrip('xX')
    digits = re.sub(r'[^0-9]', '', token)
    return int(digits) if digits and len(digits) <= 4 else None


def _parse_money_token(token: str) -> float:
    # Treat dot/comma as separators and drop currency markers
    cleaned = re.sub(r'[^0-9]', '', token)
    if not cleaned or len(cleaned) > 12:
        return None
    return float(cleaned)


def _is_price_token(token: str) -> bool:
    """Check if a token looks like a price (has separator or is pure digits >= 4 chars)."""
    cleaned = token.strip()
    has_sep = ',' in cleaned or '.' in cleaned
    digits_only = re.sub(r'[^0-9]', '', cleaned)
    # A price token is pure numeric with separators, or pure digits with 4+ chars
    non_digit_non_sep = re.sub(r'[0-9,.]', '', cleaned)
    if non_digit_non_sep:
        return False  # Contains letters → not a price
    return has_sep or len(digits_only) >= 4


def _is_text_line(line: str) -> bool:
    """Check if a line is primarily text (more letters than digits)."""
    alpha = sum(1 for c in line if c.isalpha())
    digit = sum(1 for c in line if c.isdigit())
    return alpha > digit


# Minimum plausible unit price in VND for Vietnamese retail invoices
_MIN_PRICE_VND = 500


def parse_products_from_text(ocr_text: str) -> List[Dict]:
    """Parse invoice products from OCR text with tolerant heuristics."""
    items: List[Dict] = []
    if not ocr_text:
        return items

    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    
    # First pass: single-line parsing for well-formatted tabular invoices
    for line in lines:
        if len(line) < 5:
            continue
        
        # Skip header/label lines
        line_lower = re.sub(r'[^a-z\s]', '', line.lower())
        if any(skip in line_lower for skip in _SKIP_LINES):
            continue

        # Quick regex path for neat tabular lines with explicit quantity
        match = LINE_REGEX.match(line)
        if match:
            name = match.group('name').strip().rstrip('-:')
            try:
                qty = int(match.group('qty'))
                unit = float(match.group('unit').replace(',', '').replace('.', ''))
                total_str = match.group('total')
                total = float(total_str.replace(',', '').replace('.', '')) if total_str else unit * qty
            except (ValueError, AttributeError):
                pass
            else:
                if name and qty > 0 and unit >= _MIN_PRICE_VND:
                    items.append({
                        'product_name': name,
                        'quantity': qty,
                        'unit_price': unit,
                        'line_total': total
                    })
                    continue

        # General token-based parsing (handles Vietnamese format: name unit_price total)
        simplified = re.sub(r'[\t•·]', ' ', line)
        simplified = re.sub(r'^\d+[).:-]?\s*', '', simplified)
        simplified = re.sub(r'\.{2,}', ' ', simplified)
        simplified = re.sub(r'\s{2,}', ' ', simplified).strip()
        if len(simplified) < 5:
            continue

        tokens = simplified.split()
        while tokens and tokens[-1].lower().strip('.,') in _CURRENCY_TOKENS:
            tokens.pop()
        if len(tokens) < 2:
            continue

        filtered_tokens = [t for t in tokens if t.lower() not in {'x', 'x.', 'x,'}]
        if len(filtered_tokens) < 2:
            continue
        tokens = filtered_tokens

        # Try: name + qty + unit + total (explicit quantity) — check BEFORE 3-token
        if len(tokens) >= 4:
            total = _parse_money_token(tokens[-1])
            unit = _parse_money_token(tokens[-2])
            qty = _parse_int_token(tokens[-3])
            name_tokens = tokens[:-3]
            
            if (qty and unit and qty > 0 and unit >= _MIN_PRICE_VND
                    and _is_price_token(tokens[-1]) and _is_price_token(tokens[-2])):
                if total is None:
                    total = unit * qty
                line_name = ' '.join(name_tokens).strip('-:•')
                if line_name and len(line_name) > 2:
                    items.append({
                        'product_name': line_name,
                        'quantity': qty,
                        'unit_price': unit,
                        'line_total': total
                    })
                    continue

        # Try: name + unit_price + total (Vietnamese format, no quantity column)
        if len(tokens) >= 3:
            total = _parse_money_token(tokens[-1])
            unit = _parse_money_token(tokens[-2])
            if (total and unit and total >= unit and unit >= _MIN_PRICE_VND
                    and _is_price_token(tokens[-1]) and _is_price_token(tokens[-2])):
                qty = max(1, int(round(total / unit)))
                name_tokens = tokens[:-2]
                line_name = ' '.join(name_tokens).strip('-:•')
                if line_name and len(line_name) > 2:
                    items.append({
                        'product_name': line_name,
                        'quantity': qty,
                        'unit_price': unit,
                        'line_total': total
                    })
                    continue

    # Second pass: multi-line parsing for OCR engines that return each field
    # on a separate line (e.g., EasyOCR). Pattern: text → number → number
    if not items:
        buffer = []
        for line in lines:
            line_lower = re.sub(r'[^a-z\s]', '', line.lower())
            if any(skip in line_lower for skip in _SKIP_LINES):
                continue
            
            # If line has more letters than digits, it's a product name
            # But handle OCR-misread digits (0/O confusion): "0oo" or "OO0" are likely numbers
            line_digits_normalized = line.replace('o', '0').replace('O', '0')
            pure_digits = re.sub(r'[^0-9]', '', line_digits_normalized)
            if len(line.strip()) <= 4 and pure_digits and len(pure_digits) >= len(line.strip()) * 0.5:
                # Short line that's mostly digit-like — treat as number
                val = float(pure_digits) if pure_digits else 0
                if val > 0:
                    buffer.append(('number', val) if val >= _MIN_PRICE_VND else ('qty', int(val)))
                    continue
            if _is_text_line(line):
                buffer.append(('text', line.strip()))
                continue
            
            # Pure numeric / price-like line
            line_clean = line.lstrip(',.;:')
            clean_val = re.sub(r'[^0-9]', '', line_clean)
            if not clean_val:
                if len(line) > 2:
                    buffer.append(('text', line.strip()))
                continue
            
            val = float(clean_val)
            has_separator = ',' in line_clean or '.' in line_clean
            
            # Price: has separator or large number (>= 4 digits)
            if (has_separator and val >= _MIN_PRICE_VND) or len(clean_val) >= 4:
                buffer.append(('number', val))
            # Small integer without separators → quantity
            elif len(clean_val) <= 2 and val > 0 and val < 100 and not has_separator:
                buffer.append(('qty', int(val)))
            # Isolated 3-digit number → could be price or code
            elif len(line_clean.strip()) == len(clean_val) and val > 0:
                buffer.append(('number', val))
            else:
                buffer.append(('text', line.strip()))
        
        # Process buffer: look for product patterns
        i = 0
        while i < len(buffer):
            found_match = False
            
            # Pattern 1: text+ → qty → number → number (4-field)
            for j in range(i, min(i + 4, len(buffer) - 3)):
                if (buffer[j][0] == 'text' and 
                    buffer[j+1][0] == 'qty' and 
                    buffer[j+2][0] == 'number' and 
                    buffer[j+3][0] == 'number'):
                    
                    name_parts = [b[1] for b in buffer[i:j+1] if b[0] == 'text']
                    name = ' '.join(name_parts)
                    qty = buffer[j+1][1]
                    unit = buffer[j+2][1]
                    total = buffer[j+3][1]
                    
                    if total >= unit and unit >= _MIN_PRICE_VND and len(name) > 2 and qty > 0:
                        items.append({
                            'product_name': name,
                            'quantity': qty,
                            'unit_price': unit,
                            'line_total': total
                        })
                        i = j + 4
                        found_match = True
                        break
            
            # Pattern 2: text+ → number → number (3-field, derive qty)
            if not found_match:
                for j in range(i, min(i + 4, len(buffer) - 2)):
                    if (buffer[j][0] == 'text' and 
                        buffer[j+1][0] == 'number' and 
                        buffer[j+2][0] == 'number'):
                        
                        name_parts = [b[1] for b in buffer[i:j+1] if b[0] == 'text']
                        name = ' '.join(name_parts)
                        unit = buffer[j+1][1]
                        total = buffer[j+2][1]
                        
                        if total >= unit and unit >= _MIN_PRICE_VND and len(name) > 2:
                            qty = max(1, int(round(total / unit)))
                            if qty <= 200:  # Sanity check
                                items.append({
                                    'product_name': name,
                                    'quantity': qty,
                                    'unit_price': unit,
                                    'line_total': total
                                })
                                i = j + 3
                                found_match = True
                                break
            
            if not found_match:
                i += 1

    return items
