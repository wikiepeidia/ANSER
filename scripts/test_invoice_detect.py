#!/usr/bin/env python3
"""test_invoice_detect.py
Run DL invoice detection on a single invoice image and print JSON + a summary table.
Usage: python scripts/test_invoice_detect.py [--path PATH] [--pretty]
"""
import argparse
import json
import os
import sys
import traceback

# Ensure project root is in sys.path so imports work when run from anywhere
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.services.dl_client import DLClient

DEFAULT_PATH = os.path.join('backup', 'dl imgs', 'generated_invoices', 'test', 'invoice_test_1080.png')

parser = argparse.ArgumentParser(description='Run DL invoice detection on a test image')
parser.add_argument('--path', '-p', default=DEFAULT_PATH, help='Path to invoice image')
parser.add_argument('--pretty', action='store_true', help='Pretty print JSON')
parser.add_argument('--local', action='store_true', help='Force local DL execution (default)')
args = parser.parse_args()

invoice_path = args.path
if not os.path.isabs(invoice_path):
    invoice_path = os.path.join(ROOT, invoice_path)

if not os.path.exists(invoice_path):
    print(f"ERROR: Invoice image not found: {invoice_path}")
    sys.exit(2)

print(f"Running invoice detection on: {invoice_path}\n")

# Initialize DL client (local mode by default)
client = DLClient(use_local=True)

try:
    result = client.detect_invoice(file_path=invoice_path)
except Exception as e:
    print("Exception while running DL detect:")
    traceback.print_exc()
    sys.exit(1)

# Print full JSON
if args.pretty:
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(json.dumps(result, ensure_ascii=False))

# Try to extract products from known possible structures
products = None
if isinstance(result, dict):
    # Common shapes
    products = result.get('products')
    if products is None and 'invoice' in result and isinstance(result['invoice'], dict):
        products = result['invoice'].get('items') or result['invoice'].get('products')
    if products is None and 'data' in result and isinstance(result['data'], dict):
        products = result['data'].get('products') or result['data'].get('items')

# Normalize and print table
if products and isinstance(products, list) and len(products) > 0:
    print('\nExtracted Products:')
    # Compute column widths
    names = [p.get('product_name') or p.get('name') or p.get('product') or '' for p in products]
    qtys = [str(p.get('quantity', '')) for p in products]
    unit_prices = [str(p.get('unit_price', p.get('price', ''))) for p in products]
    totals = [str(p.get('line_total', p.get('total', ''))) for p in products]

    name_w = max(10, max((len(n) for n in names)))
    print(f" {'#':>3}  {'Name':{name_w}}  {'Qty':>5}  {'Unit':>10}  {'Total':>10}")
    print('-' * (6 + name_w + 31))
    for i, p in enumerate(products, 1):
        name = (p.get('product_name') or p.get('name') or p.get('product') or '')[:name_w]
        qty = p.get('quantity', '')
        unit = p.get('unit_price', p.get('price', ''))
        total = p.get('line_total', p.get('total', ''))
        print(f" {i:3d}. {name:{name_w}}  {str(qty):>5}  {str(unit):>10}  {str(total):>10}")
else:
    print('\nNo products detected (or returned structure not recognized).')

# Print brief summary of top-level keys for inspection
if isinstance(result, dict):
    print('\nTop-level keys in result:', ', '.join(sorted(result.keys())))

print('\nDone.')
