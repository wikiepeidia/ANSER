"""
History & Utility Routes
History, model info, and utility API endpoints
"""
from flask import Blueprint, request, jsonify
from datetime import datetime

from services.invoice_service import get_invoice_history, clear_invoice_history, invoice_history
from services.model_loader import get_models_info
from utils.database import (
    get_invoices_from_db,
    get_forecasts_from_db,
    get_statistics,
    clear_database
)
from utils.logger import get_logger

# Create blueprint
history_bp = Blueprint('history', __name__, url_prefix='/api')
logger = get_logger(__name__)


@history_bp.route('/history', methods=['GET'])
def get_history():
    """Get invoice history from memory"""
    try:
        history = get_invoice_history()
        
        return jsonify({
            'success': True,
            'count': len(history),
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@history_bp.route('/history/database', methods=['GET'])
def get_database_history():
    """Get invoice and forecast history from database"""
    try:
        # Get pagination parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Get data
        invoices = get_invoices_from_db(limit=limit, offset=offset)
        forecasts = get_forecasts_from_db(limit=limit)
        
        return jsonify({
            'success': True,
            'invoices': {
                'count': len(invoices),
                'data': invoices
            },
            'forecasts': {
                'count': len(forecasts),
                'data': forecasts
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting database history: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@history_bp.route('/history/clear', methods=['POST'])
def clear_history():
    """Clear invoice history"""
    try:
        # Clear memory
        count = clear_invoice_history()
        
        # Optionally clear database
        clear_db = request.args.get('database', 'false').lower() == 'true'
        if clear_db:
            clear_database()
            logger.info("Cleared database history")
        
        logger.info(f"Cleared {count} invoices from memory")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {count} invoices',
            'database_cleared': clear_db
        })
        
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@history_bp.route('/statistics', methods=['GET'])
def get_stats():
    """Get statistics from database"""
    try:
        stats = get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@history_bp.route('/models/info', methods=['GET'])
def models_info():
    """Get information about loaded models"""
    try:
        models = get_models_info()
        
        return jsonify({
            'success': True,
            'models': models,
            'invoice_history_count': len(invoice_history)
        })
        
    except Exception as e:
        logger.error(f"Error getting models info: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@history_bp.route('/models/train', methods=['POST'])
def train_models():
    """Training endpoint (not implemented)"""
    return jsonify({
        'success': False,
        'message': 'Training endpoint not implemented. Use train_models.py script instead.'
    }), 501

