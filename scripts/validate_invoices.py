#!/usr/bin/env python3
"""validate_invoices.py
Run DL invoice detection over a directory and validate the returned schema.
Usage: python scripts/validate_invoices.py --dir "backup/dl imgs/generated_invoices/test" --pretty
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.services.dl_client import DLClient

parser = argparse.ArgumentParser(description='Validate invoice detection outputs in a folder')
parser.add_argument('--dir', '-d', default=os.path.join('backup', 'dl imgs', 'generated_invoices', 'test'), help='Directory to scan')
parser.add_argument('--pretty', action='store_true', help='Pretty print failures')
args = parser.parse_args()

scan_dir = os.path.abspath(os.path.join(ROOT, args.dir))
if not os.path.isdir(scan_dir):
    print(f"ERROR: Directory not found: {scan_dir}")
    sys.exit(2)

print(f"Scanning folder: {scan_dir}")

client = DLClient(use_local=True)

files = [p for p in Path(scan_dir).iterdir() if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}]
print(f"Found {len(files)} images")

failures = []

for p in files:
    try:
        print(f"\nProcessing {p.name}...")
        res = client.detect_invoice(file_path=str(p))
        # If wrapped by success/data
        if isinstance(res, dict) and res.get('success') and 'data' in res:
            data = res['data']
        else:
            data = res

        # Basic checks
        if not isinstance(data, dict):
            failures.append((p.name, 'Invalid response shape'))
            continue

        products = data.get('products') or data.get('invoice', {}).get('items') or data.get('data', {}).get('products')
        total = data.get('total_amount') or data.get('total')
        if products is None or not isinstance(products, list):
            failures.append((p.name, 'No products list found'))
            continue
        if total is None:
            failures.append((p.name, 'No total_amount found'))
            continue

        # Validate product fields
        for i, prod in enumerate(products, 1):
            if not prod.get('product_name') and not prod.get('name'):
                failures.append((p.name, f'Product {i} missing name'))
            if 'quantity' not in prod:
                failures.append((p.name, f'Product {i} missing quantity'))
            if 'unit_price' not in prod and 'price' not in prod:
                failures.append((p.name, f'Product {i} missing unit price'))
            if 'line_total' not in prod and 'total' not in prod:
                failures.append((p.name, f'Product {i} missing line total'))

        # Check totals
        sum_lines = 0
        for prod in products:
            lt = prod.get('line_total') or prod.get('total') or 0
            try:
                sum_lines += float(lt)
            except Exception:
                pass
        try:
            total_val = float(total)
            if total_val == 0:
                # Allow some invoices to be zero for tests but warn
                failures.append((p.name, 'Total amount is zero'))
            else:
                # Allow 5% tolerance
                if abs(sum_lines - total_val) / max(total_val, 1) > 0.05:
                    failures.append((p.name, f'Total mismatch: sum_lines={sum_lines} total={total_val}'))
        except Exception:
            failures.append((p.name, 'Total amount not numeric'))

    except Exception as e:
        failures.append((p.name, f'Exception: {e}'))

# Summary
print('\n--- Summary ---')
print(f'Total files checked: {len(files)}')
print(f'Failures: {len(failures)}')
if failures:
    print('\nFailures detail:')
    for f in failures:
        print(f'- {f[0]}: {f[1]}')
    if args.pretty:
        print('\nRun single test with --pretty to see full JSON for a file.')
else:
    print('All files passed basic validation ✅')
