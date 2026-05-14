"""
Model 1 Routes
Invoice Detection API endpoints
"""
from flask import Blueprint, request, jsonify, send_file
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from datetime import datetime
import time
import os

from services.invoice_service import process_invoice_image, format_invoice_response
from config import ALLOWED_EXTENSIONS, UPLOAD_DIR
from utils.validators import validate_image_file, ValidationError
from utils.database import save_invoice_to_db
from utils.logger import get_logger, log_api_request

# Create blueprint
model1_bp = Blueprint('model1', __name__, url_prefix='/api/model1')
logger = get_logger(__name__)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@model1_bp.route('/detect', methods=['POST'])
def detect_invoice():
    """Detect invoice from uploaded image"""
    start_time = time.time()

    try:
        # Validate file upload - check both 'image' and 'file' for compatibility
        file = None
        if 'image' in request.files:
            file = request.files['image']
        elif 'file' in request.files:
            file = request.files['file']
        else:
            raise ValidationError('No file provided. Please upload an image.')

        # Validate file
        validate_image_file(file)

        logger.info(f"Processing invoice image: {file.filename}")

        # Read image
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if image is None:
            raise ValidationError('Failed to read image')

        # Process invoice
        logger.info(f"[ROUTE] About to call process_invoice_image from {process_invoice_image.__module__}")
        invoice_data = process_invoice_image(image)
        logger.info(f"[ROUTE] Returned from process_invoice_image, got {len(invoice_data.get('products',[]))} products")

        # Save to database
        try:
            save_invoice_to_db(invoice_data)
        except Exception as db_error:
            logger.warning(f"Failed to save invoice to database: {db_error}")

        # Format response
        response = format_invoice_response(invoice_data)

        # Log API request
        duration = (time.time() - start_time) * 1000
        log_api_request('/api/model1/detect', 'POST',
                        params={'file': file.filename},
                        status_code=200, duration=duration)

        logger.info(f"Invoice processed successfully in {duration:.2f}ms")

        return jsonify(response)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error processing image: {str(e)}'
        }), 500
