"""
Configuration Settings
Centralized configuration for the entire application
"""
import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Directory Paths
DATA_DIR = BASE_DIR / 'data'
MODEL_DIR = BASE_DIR / 'saved_models'
UPLOAD_DIR = BASE_DIR / 'uploads'
STATIC_DIR = BASE_DIR / 'static'
TEMPLATE_DIR = BASE_DIR / 'ui' / 'templates'

# Ensure directories exist
MODEL_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Convert Path to string for compatibility
UPLOAD_DIR = str(UPLOAD_DIR)

# Model Paths
LSTM_MODEL_PATH = MODEL_DIR / 'lstm_text_recognizer.weights.h5'
LSTM_SCALER_PATH = MODEL_DIR / 'lstm_text_recognizer.weights_scaler.pkl'
LAYOUT_WEIGHTS_DIR = MODEL_DIR / 'layout_detector' / 'weights'
LAYOUT_WEIGHTS_PATH = Path(os.getenv('LAYOUT_WEIGHTS_PATH', LAYOUT_WEIGHTS_DIR / 'best.pt'))
LAYOUT_INFER_DEVICE = os.getenv('LAYOUT_INFER_DEVICE', 'auto')
LAYOUT_METRICS_PATH = LAYOUT_WEIGHTS_DIR.parent / 'training_metrics.json'

# Data Paths
CATALOG_PATH = DATA_DIR / 'product_catalogs.json'
DATASET_PATH = DATA_DIR / 'DATASET-tung1000.csv'

# Image Settings
IMG_HEIGHT = 224
IMG_WIDTH = 224
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

# Model Settings
LSTM_SEQUENCE_LENGTH = 7  # Updated for time-series model (7-day history)
LSTM_NUM_FEATURES = 7  # Updated: sale_qty, day_of_week, is_weekend, cumulative_sales, days_since_import, initial_stock, retail_price

# Store Configuration
STORE_NAME_LOOKUP = {
    'store1': 'Retail Store',
    'store2': 'General Store'
}

# Training Settings
EPOCHS = 50
BATCH_SIZE = 32
VALIDATION_SPLIT = 0.2
LEARNING_RATE = 0.001

# Flask Settings
FLASK_DEBUG = False
FLASK_HOST = '127.0.0.1'
FLASK_PORT = 5000

# History Storage
MAX_INVOICE_HISTORY = 300
