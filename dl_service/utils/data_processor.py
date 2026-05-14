"""
Data Processing Utilities
Handles invoice data extraction and processing
"""
import re
import unicodedata
from datetime import datetime


def normalize_text(text):
    """Normalize Vietnamese text for matching"""
    if not isinstance(text, str):
        return ''
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def extract_numbers_from_line(line):
    """Extract all numbers from a text line"""
    matches = re.findall(r'\d{1,3}(?:[\.,]\d{3})+|\d+', line)
    values = []
    for match in matches:
        clean = re.sub(r'[^0-9]', '', match)
        if clean:
            try:
                values.append(int(clean))
            except ValueError:
                continue
    return values


def extract_quantity_from_line(line):
    """Extract quantity from invoice line"""
    line_lower = line.lower()
    
    # Check for multiplier pattern (x5, ×3, etc.)
    multiplier_match = re.search(r'(?:x|×|\*)\s*(\d{1,3})', line_lower)
    if multiplier_match:
        return int(multiplier_match.group(1))
    
    # Check for unit patterns
    unit_match = re.search(
        r'(\d{1,3})\s*(?:pcs|chai|hop|kg|sp|unit|units|box|thung|ly|goi|bich|dong)',
        line_lower
    )
    if unit_match:
        return int(unit_match.group(1))
    
    # Check for reasonable quantity numbers (1-500)
    numbers = extract_numbers_from_line(line)
    for value in numbers:
        if 0 < value <= 500:
            return value
    return None


def extract_price_candidates(line):
    """Extract potential price values from line"""
    numbers = extract_numbers_from_line(line)
    return [value for value in numbers if value >= 1000]


def build_dataframe_from_invoices(invoices):
    """Convert invoice history to DataFrame for LSTM"""
    import pandas as pd
    
    records = []
    for invoice in invoices:
        products = invoice.get('products', [])
        total_quantity = sum(max(product.get('quantity', 0), 0) for product in products)
        
        if total_quantity <= 0:
            total_quantity = max(invoice.get('total_quantity', 0), 0)
        
        total_amount = invoice.get('total_amount', 0) or sum(
            (product.get('line_total') or product.get('quantity', 0) * product.get('unit_price', 0))
            for product in products
        )
        
        average_price = 0.0
        if total_quantity > 0:
            average_price = total_amount / total_quantity
        elif products:
            average_price = sum(product.get('unit_price', 0) for product in products) / max(len(products), 1)
        
        # Estimate auxiliary metrics
        estimated_sales = total_quantity * 0.9
        estimated_stock = max(total_quantity * 1.15, total_quantity + 10)
        demand_indicator = estimated_sales / (estimated_stock + 1)
        
        records.append({
            'quantity': float(total_quantity),
            'price': float(max(average_price, 0)),
            'sales': float(max(estimated_sales, 0)),
            'stock': float(max(estimated_stock, 0)),
            'demand': float(max(demand_indicator, 0))
        })
    
    if not records:
        return pd.DataFrame(columns=['quantity', 'price', 'sales', 'stock', 'demand'])
    
    return pd.DataFrame(records)
