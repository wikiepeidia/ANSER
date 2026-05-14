import os

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from models.lstm_model import ImportForecastLSTM
from config import LSTM_MODEL_PATH, LSTM_SEQUENCE_LENGTH, LSTM_NUM_FEATURES, LAYOUT_WEIGHTS_PATH
from services.layout_service import initialize_layout_detector

# Global model instances
lstm_model = None
layout_ready = False


def initialize_models():
    
    print("\n" + "="*60)
    print("INITIALIZING DEEP LEARNING MODELS")
    print("="*60)
    
    print("Loading Layout Detector (YOLO)...")
    global layout_ready
    try:
        initialize_layout_detector()
        layout_ready = True
        print(f"   [OK] Layout weights loaded from {LAYOUT_WEIGHTS_PATH}")
    except Exception as exc:
        error_msg = str(exc).encode('ascii', 'ignore').decode('ascii')
        layout_ready = False
        print(f"   [WARNING] Unable to initialize layout detector: {error_msg}")
    
    # Model 2: LSTM
    print("Loading Model 2: LSTM Forecasting...")
    global lstm_model
    try:
        lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
        if LSTM_MODEL_PATH.exists():
            lstm_model.load_model(str(LSTM_MODEL_PATH))
            print(f"   [OK] Loaded LSTM weights from {LSTM_MODEL_PATH.name}")
        else:
            lstm_model.build_model()
            print("   [WARNING] Pre-trained LSTM weights not found; using freshly initialized model")
    except Exception as exc:
        error_msg = str(exc).encode('ascii', 'ignore').decode('ascii')
        print(f"   [WARNING] Unable to load ImportForecastLSTM: {error_msg}")
        lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
        lstm_model.build_model()
    
    print("="*60)
    print("MODELS INITIALIZED - READY TO BUILD ON DEMAND")
    print("="*60 + "\n")


def get_lstm_model():
    """Lazy load LSTM model"""
    global lstm_model
    if lstm_model is None:
        print("Loading ImportForecastLSTM on demand...")
        try:
            lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
            if LSTM_MODEL_PATH.exists():
                lstm_model.load_model(str(LSTM_MODEL_PATH))
            else:
                lstm_model.build_model()
        except Exception as exc:
            print(f"   [WARNING] Fallback to fresh ImportForecastLSTM due to: {exc}")
            lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
            lstm_model.build_model()
    return lstm_model


def get_models_info():
    
    return {
        'layout_detector': {
            'name': 'YOLO Layout Detector',
            'input': 'Invoice image',
            'output': 'Header/Table/Total regions',
            'architecture': 'YOLOv8 fine-tuned on synthetic invoices',
            'status': 'Ready' if layout_ready else 'Not loaded',
            'weights': str(LAYOUT_WEIGHTS_PATH)
        },
        'model2_lstm': {
            'name': 'Import Forecast LSTM',
            'input': 'Structured invoice history (quantity, price, sales, stock, demand)',
            'output': 'Predicted import quantity & confidence',
            'architecture': 'Stacked LSTM for time-series forecasting',
            'status': 'Ready' if lstm_model and getattr(lstm_model, 'model', None) else 'Not loaded',
            'lookback': lstm_model.lookback if lstm_model else 'Not loaded',
            'features': lstm_model.features if lstm_model else 'Not loaded',
            'weights': str(LSTM_MODEL_PATH) if LSTM_MODEL_PATH.exists() else 'In-memory'
        }
    }
