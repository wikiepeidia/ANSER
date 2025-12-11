# -*- coding: utf-8 -*-
"""
Flask App - Invoice Forecast Deep Learning Demo
CLEAN VERSION using existing api/, services/, utils/ structure
"""

import os
import sys
import warnings
import logging

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=UserWarning, module='keras')
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('keras').setLevel(logging.ERROR)

from flask import Flask, render_template
from config import (
    TEMPLATE_DIR, STATIC_DIR, FLASK_DEBUG, FLASK_HOST, FLASK_PORT
)

# Import services
from services.model_loader import initialize_models
from utils.database import init_database

# Import API blueprints
from api.model1_routes import model1_bp
from api.model2_routes import model2_bp
from api.history_routes import history_bp
from api.ocr_routes import ocr_bp

# Create Flask app
app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR)
)
app.config['JSON_AS_ASCII'] = False
app.config['ENCODING'] = 'utf-8'

# Homepage route
@app.route('/')
def index():
	"""Main page"""
	return render_template('index.html')

# Register blueprints
app.register_blueprint(model1_bp)
app.register_blueprint(model2_bp)
app.register_blueprint(history_bp)
app.register_blueprint(ocr_bp)

# Initialize database
init_database()

# Initialize models at startup
initialize_models()

if __name__ == '__main__':
    print("\n" + "="*70)
    print("INVOICE FORECAST SYSTEM - DEEP LEARNING DEMO")
    print("="*70)
    print("Model 1: YOLO Layout Detector + OCR Pipeline")
    print("Model 2: LSTM - Quantity Forecasting")
    print("="*70)
    print(f"Server: http://{FLASK_HOST}:{FLASK_PORT}")
    print("\nAPI Endpoints:")
    print(" POST /api/model1/detect - Upload invoice image")
    print(" POST /api/model2/forecast - Get quantity forecast")
    print(" POST /api/ocr/ - Upload image for OCR (field: 'image' or 'file')")
    print(" GET /api/history - View invoice history")
    print(" POST /api/history/clear - Clear history")
    print("="*70 + "\n")

    app.run(debug=FLASK_DEBUG, port=FLASK_PORT, host=FLASK_HOST, use_reloader=False)
