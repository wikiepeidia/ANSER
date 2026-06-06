#!/usr/bin/env python3
"""Excel file parsing helper for import operations."""
import openpyxl
from io import BytesIO
from typing import List, Dict, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ExcelParser:
    """Parse Excel files for import transactions."""
    
    @staticmethod
    def parse_import_file(file_content: bytes, sheet_name: str = None) -> Dict:
        """
        Parse Excel file for import data.
        
        Expected format:
        - Column A: Product Code (or Product ID)
        - Column B: Product Name (optional, will lookup if code provided)
        - Column C: Quantity
        - Column D: Unit Price
        
        Returns: {
            'success': bool,
            'items': List[{product_code, quantity, unit_price}],
            'error': str (if not success)
        }
        """
        try:
            # Load workbook from bytes
            wb = openpyxl.load_workbook(BytesIO(file_content))
            
            # Get sheet (first sheet by default or specific sheet)
            if sheet_name:
                if sheet_name not in wb.sheetnames:
                    return {
                        'success': False,
                        'error': f"Sheet '{sheet_name}' not found. Available: {', '.join(wb.sheetnames)}"
                    }
                ws = wb[sheet_name]
            else:
                ws = wb.active
            
            logger.info(f"Parsing Excel sheet: {ws.title}")
            
            items = []
            row_count = 0
            error_rows = []
            
            # Skip header row (row 1)
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
                row_count += 1
                
                try:
                    # Extract values
                    product_code = row[0].value if row[0] else None
                    product_name = row[1].value if len(row) > 1 else None
                    quantity = row[2].value if len(row) > 2 else None
                    unit_price = row[3].value if len(row) > 3 else None
                    
                    # Validate required fields
                    if not product_code:
                        continue  # Skip empty rows
                    
                    if not quantity or not unit_price:
                        error_rows.append(f"Row {row_idx}: Missing quantity or price")
                        continue
                    
                    try:
                        qty = float(quantity)
                        price = float(unit_price)
                    except (ValueError, TypeError):
                        error_rows.append(f"Row {row_idx}: Invalid quantity/price format")
                        continue
                    
                    items.append({
                        'product_code': str(product_code).strip(),
                        'product_name': str(product_name).strip() if product_name else None,
                        'quantity': qty,
                        'unit_price': price
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {row_idx}: {e}")
                    error_rows.append(f"Row {row_idx}: {str(e)}")
                    continue
            
            if not items:
                return {
                    'success': False,
                    'error': f"No valid items found in Excel file. Errors: {'; '.join(error_rows) if error_rows else 'Empty file'}"
                }
            
            result = {
                'success': True,
                'items': items,
                'row_count': len(items)
            }
            
            if error_rows:
                result['warnings'] = error_rows
            
            logger.info(f"Successfully parsed {len(items)} items from Excel")
            return result
            
        except openpyxl.utils.exceptions.InvalidFileException:
            return {
                'success': False,
                'error': 'Invalid Excel file format. Please upload a .xlsx file.'
            }
        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Error parsing Excel file: {str(e)}"
            }
    
    @staticmethod
    def get_sample_template() -> bytes:
        """Generate a sample Excel template for import."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Import Template"
        
        # Headers
        headers = ["Product Code", "Product Name", "Quantity", "Unit Price"]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = openpyxl.styles.Font(bold=True)
            cell.fill = openpyxl.styles.PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.font = openpyxl.styles.Font(bold=True, color="FFFFFF")
        
        # Sample data
        sample_data = [
            ["SKU001", "Product A", 10, 50000],
            ["SKU002", "Product B", 5, 75000],
        ]
        for row_idx, row_data in enumerate(sample_data, 2):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx).value = value
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 15
        
        # Convert to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
