"""
API Routes Package
"""
from .model1_routes import model1_bp
from .model2_routes import model2_bp
from .history_routes import history_bp

__all__ = ['model1_bp', 'model2_bp', 'history_bp', 'ocr_bp']