"""OCR Routes
Accept image uploads and return extracted text using the OCR service.
"""
from flask import Blueprint, request, jsonify
import time
from utils.validators import validate_image_file, ValidationError
from utils.logger import get_logger, log_api_request
from services.ocr_service import extract_text_from_image_bytes

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api/ocr')
logger = get_logger(__name__)


@ocr_bp.route('/', methods=['POST'])
def ocr_image():
    start_time = time.time()
    try:
        file = None
        if 'image' in request.files:
            file = request.files['image']
        elif 'file' in request.files:
            file = request.files['file']
        else:
            raise ValidationError('No file provided. Please upload an image.')

        validate_image_file(file)

        filename = getattr(file, 'filename', 'uploaded')
        logger.info(f"OCR request for: {filename}")

        file_bytes = file.read()

        result = extract_text_from_image_bytes(file_bytes)

        duration = (time.time() - start_time) * 1000
        log_api_request('/api/ocr/', 'POST', params={'file': filename}, status_code=200 if result.get('success') else 500, duration=duration)

        if not result.get('success'):
            return jsonify({'success': False, 'message': result.get('error', 'OCR failed')}), 500

        # Return compatible structure used by invoice processing utilities
        response = {
            'success': True,
            'extracted_text': result.get('text', ''),
            'text': result.get('text', ''),
            'backend': result.get('backend'),
            'confidence': float(result.get('confidence', 0.0)),
            'message': 'OCR completed'
        }

        return jsonify(response)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"OCR error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
