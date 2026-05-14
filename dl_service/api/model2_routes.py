"""
Model 2 Routes
Forecast API endpoints
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import time

from services.model_loader import get_lstm_model
from services.forecast_service import parse_manual_invoice_data, forecast_quantity, format_forecast_response
from services.invoice_service import invoice_history
from utils.validators import validate_invoice_data, ValidationError
from utils.database import save_forecast_to_db
from utils.logger import get_logger, log_api_request

# Create blueprint
model2_bp = Blueprint('model2', __name__, url_prefix='/api/model2')
logger = get_logger(__name__)


@model2_bp.route('/forecast', methods=['POST'])
def forecast():
    """Forecast product quantities"""
    start_time = time.time()

    try:
        # Get invoice data - accept both formats
        data = request.get_json() or {}

        # NEW: Support direct products array
        products = data.get('products', [])
        if products:
            logger.info(f"Using {len(products)} products from request")
            invoice_items = products
        else:
            # OLD: Manual invoice data text
            manual_invoice = data.get('invoice_data', '').strip()

            if manual_invoice:
                validate_invoice_data(manual_invoice)
                parsed_products = parse_manual_invoice_data(manual_invoice)
                if not parsed_products:
                    raise ValidationError('No valid products found in input')
                invoice_items = parsed_products
            else:
                # Use last invoice from history
                if not invoice_history:
                    raise ValidationError('No invoice history. Please upload invoices first or provide products array.')

                last_invoice = invoice_history[-1]
                invoice_items = last_invoice.get('products', [])

        logger.info(f"Processing forecast for {len(invoice_items)} items")

        # Get LSTM model
        lstm_model = get_lstm_model()
        if lstm_model is None:
            logger.error("LSTM model not loaded")
            return jsonify({
                'success': False,
                'message': 'LSTM model not loaded. Please initialize models first.'
            }), 500

        # Perform forecast
        forecast_result = forecast_quantity(lstm_model, invoice_items)

        # Save to database
        try:
            save_forecast_to_db(forecast_result)
        except Exception as db_error:
            logger.warning(f"Failed to save forecast to database: {db_error}")

        # Format response
        response = format_forecast_response(forecast_result)

        # Log API request
        duration = (time.time() - start_time) * 1000
        log_api_request('/api/model2/forecast', 'POST',
                        params={'num_products': len(invoice_items)},
                        status_code=200, duration=duration)

        logger.info(f"Forecast completed successfully in {duration:.2f}ms")

        return jsonify(response)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error generating forecast: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error generating forecast: {str(e)}'
        }), 500
