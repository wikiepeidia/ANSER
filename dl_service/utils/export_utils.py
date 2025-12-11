"""
Export Utilities
Export data to various formats (CSV, JSON)
"""
import csv
import json
from io import StringIO
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


def export_to_json(data, filename=None):
    """
    Export data to JSON
    
    Args:
        data: List of dictionaries or single dictionary
        filename: Optional filename to save to
        
    Returns:
        str: JSON string or path to saved file
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        
        if filename:
            filepath = Path('exports') / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            logger.info(f"Exported to JSON: {filepath}")
            return str(filepath)
        
        return json_str
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        raise


def export_to_csv(data, filename=None):
    """
    Export data to CSV
    
    Args:
        data: List of dictionaries
        filename: Optional filename to save to
        
    Returns:
        str: CSV string or path to saved file
    """
    try:
        if not data:
            return "" if not filename else None
        
        # Get all unique keys from all dictionaries
        fieldnames = set()
        for item in data:
            if isinstance(item, dict):
                fieldnames.update(item.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        # Create CSV
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for item in data:
            # Convert nested objects to JSON strings
            row = {}
            for key, value in item.items():
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False)
                else:
                    row[key] = value
            writer.writerow(row)
        
        csv_str = output.getvalue()
        
        if filename:
            filepath = Path('exports') / filename
            filepath.parent.mkdir(exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                f.write(csv_str)
            
            logger.info(f"Exported to CSV: {filepath}")
            return str(filepath)
        
        return csv_str
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        raise


def export_invoices(invoices, format='json', filename=None):
    """
    Export invoices in specified format
    
    Args:
        invoices: List of invoice dictionaries
        format: 'json' or 'csv'
        filename: Optional filename
        
    Returns:
        str: Exported data
    """
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"invoices_{timestamp}.{format}"
    
    if format == 'json':
        return export_to_json(invoices, filename)
    elif format == 'csv':
        return export_to_csv(invoices, filename)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")


def export_forecasts(forecasts, format='json', filename=None):
    """
    Export forecasts in specified format
    
    Args:
        forecasts: List of forecast dictionaries
        format: 'json' or 'csv'
        filename: Optional filename
        
    Returns:
        str: Exported data
    """
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"forecasts_{timestamp}.{format}"
    
    if format == 'json':
        return export_to_json(forecasts, filename)
    elif format == 'csv':
        return export_to_csv(forecasts, filename)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'csv'.")
