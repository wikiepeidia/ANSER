"""
Test import Excel thật vào NeonDB.
Chạy: python scripts/test_import_real.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from core.services.product_service import import_products_from_excel

SAMPLE_FILE = os.path.join(os.path.dirname(__file__), 'sample_products.xlsx')


def create_sample_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Products'

    # Header
    ws.append(['code', 'name', 'category', 'unit', 'price', 'stock_quantity', 'description'])

    # Dữ liệu mẫu
    ws.append(['HH001', 'Mì tôm Hảo Hảo',     'Thực phẩm', 'Thùng', 85000,  100, 'Mì tôm vị tôm chua cay'])
    ws.append(['HH002', 'Nước ngọt Pepsi',      'Đồ uống',   'Két',  120000,  50, '24 lon/két'])
    ws.append(['HH003', 'Bánh Oreo',             'Bánh kẹo',  'Hộp',  35000,  200, 'Bánh quy kem'])
    ws.append(['HH004', 'Dầu ăn Tường An 1L',   'Thực phẩm', 'Chai', 45000,   80, ''])
    ws.append(['HH005', 'Xà phòng Lifebuoy',     'Vệ sinh',   'Cái',  18000,  150, ''])
    ws.append(['HH001', 'Mì tôm Hảo Hảo UPDATE','Thực phẩm', 'Thùng', 90000,  120, 'Giá mới'])  # trùng code → UPDATE

    wb.save(SAMPLE_FILE)
    print(f'✅ Đã tạo file mẫu: {SAMPLE_FILE}')


def run_import():
    print('\n📦 Bắt đầu import...\n')
    with open(SAMPLE_FILE, 'rb') as f:
        f.name = SAMPLE_FILE
        result = import_products_from_excel(f, created_by=1)

    print(f"  ✅ Thêm mới  : {result['inserted']}")
    print(f"  🔄 Cập nhật  : {result['updated']}")
    print(f"  ⏭️  Bỏ qua    : {result['skipped']}")
    if result['errors']:
        print(f"  ❌ Lỗi ({len(result['errors'])}):")
        for e in result['errors']:
            print(f"     {e}")
    print()


if __name__ == '__main__':
    create_sample_excel()
    run_import()
