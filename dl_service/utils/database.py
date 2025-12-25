"""
Database Module
SQLite database for persistent storage
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from config import BASE_DIR
from utils.logger import get_logger

logger = get_logger(__name__)

# Database path
DB_DIR = BASE_DIR / 'database'
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / 'invoices.db'


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Invoices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id TEXT UNIQUE NOT NULL,
                store_name TEXT,
                store_key TEXT,
                total_amount REAL,
                confidence REAL,
                products TEXT,  -- JSON string
                extracted_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Forecasts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                predicted_quantity INTEGER,
                trend TEXT,
                confidence REAL,
                recommendation TEXT,
                history_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        logger.info("Database initialized successfully")


def save_invoice_to_db(invoice_data):
    """
    Save invoice to database
    
    Args:
        invoice_data: Invoice dictionary
        
    Returns:
        int: Row ID
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use INSERT OR REPLACE to handle duplicates
            cursor.execute('''
                INSERT OR REPLACE INTO invoices 
                (invoice_id, store_name, store_key, total_amount, confidence, products, extracted_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data.get('invoice_id'),
                invoice_data.get('store_name'),
                invoice_data.get('store_key'),
                invoice_data.get('total_amount'),
                invoice_data.get('detection_confidence'),
                json.dumps(invoice_data.get('products', []), ensure_ascii=False),
                invoice_data.get('extracted_text')
            ))
            
            logger.info(f"Saved invoice {invoice_data.get('invoice_id')} to database")
            return cursor.lastrowid
            
    except sqlite3.IntegrityError:
        logger.warning(f"Invoice {invoice_data.get('invoice_id')} already exists")
        return None
    except Exception as e:
        logger.error(f"Error saving invoice: {e}")
        raise


def save_forecast_to_db(forecast_data):
    """
    Save forecast to database
    
    Args:
        forecast_data: Forecast dictionary
        
    Returns:
        int: Row ID
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO forecasts 
                (predicted_quantity, trend, confidence, recommendation, history_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                forecast_data.get('predicted_quantity'),
                forecast_data.get('trend'),
                forecast_data.get('confidence'),
                forecast_data.get('recommendation_text'),
                forecast_data.get('history_count', 0)
            ))
            
            logger.info(f"Saved forecast to database (ID: {cursor.lastrowid})")
            return cursor.lastrowid
            
    except Exception as e:
        logger.error(f"Error saving forecast: {e}")
        raise


def get_invoices_from_db(limit=100, offset=0):
    """
    Get invoices from database
    
    Args:
        limit: Number of records to return
        offset: Offset for pagination
        
    Returns:
        list: List of invoice dictionaries
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM invoices 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            rows = cursor.fetchall()
            
            invoices = []
            for row in rows:
                invoice = dict(row)
                # Parse JSON products (handle NULL or empty values)
                products_json = invoice.get('products')
                if products_json:
                    try:
                        invoice['products'] = json.loads(products_json)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode products JSON for invoice {invoice.get('invoice_id')}")
                        invoice['products'] = []
                else:
                    invoice['products'] = []
                invoices.append(invoice)
            
            return invoices
            
    except Exception as e:
        logger.error(f"Error getting invoices: {e}")
        return []


def get_invoice_by_id(invoice_id):
    """
    Get single invoice by ID
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        dict: Invoice data or None
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM invoices WHERE invoice_id = ?',
                (invoice_id,)
            )
            
            row = cursor.fetchone()
            if row:
                invoice = dict(row)
                products_json = invoice.get('products')
                if products_json:
                    try:
                        invoice['products'] = json.loads(products_json)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode products JSON for invoice {invoice.get('invoice_id')}")
                        invoice['products'] = []
                else:
                    invoice['products'] = []
                return invoice
            return None
            
    except Exception as e:
        logger.error(f"Error getting invoice {invoice_id}: {e}")
        return None


def get_forecasts_from_db(limit=50):
    """
    Get forecasts from database
    
    Args:
        limit: Number of records to return
        
    Returns:
        list: List of forecast dictionaries
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM forecasts 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    except Exception as e:
        logger.error(f"Error getting forecasts: {e}")
        return []


def get_statistics():
    """
    Get database statistics
    
    Returns:
        dict: Statistics
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Count invoices
            cursor.execute('SELECT COUNT(*) as count FROM invoices')
            invoice_count = cursor.fetchone()['count']
            
            # Count forecasts
            cursor.execute('SELECT COUNT(*) as count FROM forecasts')
            forecast_count = cursor.fetchone()['count']
            
            # Total amount
            cursor.execute('SELECT SUM(total_amount) as total FROM invoices')
            total_amount = cursor.fetchone()['total'] or 0
            
            # Average confidence
            cursor.execute('SELECT AVG(confidence) as avg FROM invoices')
            avg_confidence = cursor.fetchone()['avg'] or 0
            
            return {
                'total_invoices': invoice_count,
                'total_forecasts': forecast_count,
                'total_amount': total_amount,
                'average_confidence': avg_confidence
            }
            
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return {}


def clear_database():
    """Clear all data from database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM invoices')
            cursor.execute('DELETE FROM forecasts')
            
            logger.info("Database cleared successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return False
