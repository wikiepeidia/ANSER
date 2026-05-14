"""
Error Handlers
error handling for Flask app
"""
from flask import jsonify
from utils.logger import get_logger

logger = get_logger(__name__)


def register_error_handlers(app):
    """Register error handlers with Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        logger.warning(f"Bad Request: {error}")
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else str(error)
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found"""
        logger.warning(f"Not Found: {error}")
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed"""
        logger.warning(f"Method Not Allowed: {error}")
        return jsonify({
            'success': False,
            'error': 'Method Not Allowed',
            'message': 'The HTTP method is not allowed for this endpoint'
        }), 405
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle 413 Request Entity Too Large"""
        logger.warning(f"Request Too Large: {error}")
        return jsonify({
            'success': False,
            'error': 'Request Entity Too Large',
            'message': 'The uploaded file is too large (max 16MB)'
        }), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server Error"""
        logger.error(f"Internal Server Error: {error}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred. Please try again later.'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all uncaught exceptions"""
        logger.error(f"Unhandled Exception: {error}", exc_info=True)
        
        # Don't expose internal errors in production
        return jsonify({
            'success': False,
            'error': 'Server Error',
            'message': 'An unexpected error occurred'
        }), 500


class APIError(Exception):
    """Base API Error"""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['success'] = False
        rv['message'] = self.message
        return rv


class ValidationError(APIError):
    """Validation Error"""
    def __init__(self, message):
        super().__init__(message, status_code=400)


class NotFoundError(APIError):
    """Not Found Error"""
    def __init__(self, message):
        super().__init__(message, status_code=404)


class ProcessingError(APIError):
    """Processing Error"""
    def __init__(self, message):
        super().__init__(message, status_code=500)
