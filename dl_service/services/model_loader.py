import os
from utils.logger import get_logger

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from models.lstm_model import ImportForecastLSTM
from config import LSTM_MODEL_PATH, LSTM_SEQUENCE_LENGTH, LSTM_NUM_FEATURES, LAYOUT_WEIGHTS_PATH
from services.layout_service import initialize_layout_detector

logger = get_logger(__name__)

# Global model instances
lstm_model = None
layout_ready = False


def initialize_models():
    
    logger.info("Initializing deep learning models")
    
    logger.info("Loading Layout Detector (YOLO)")
    global layout_ready
    try:
        initialize_layout_detector()
        layout_ready = True
        logger.info("Layout weights loaded from %s", LAYOUT_WEIGHTS_PATH)
    except Exception as exc:
        error_msg = str(exc).encode('ascii', 'ignore').decode('ascii')
        layout_ready = False
        logger.warning("Unable to initialize layout detector: %s", error_msg)
    
    # Model 2: LSTM
    logger.info("Loading Model 2: LSTM Forecasting")
    global lstm_model
    try:
        lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
        if LSTM_MODEL_PATH.exists():
            lstm_model.load_model(str(LSTM_MODEL_PATH))
            logger.info("Loaded LSTM weights from %s", LSTM_MODEL_PATH.name)
        else:
            lstm_model.build_model()
            logger.warning("Pre-trained LSTM weights not found; using freshly initialized model")
    except Exception as exc:
        error_msg = str(exc).encode('ascii', 'ignore').decode('ascii')
        logger.warning("Unable to load ImportForecastLSTM: %s", error_msg)
        lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
        lstm_model.build_model()
    
    logger.info("Models initialized - ready to build on demand")


def get_lstm_model():
    """Lazy load LSTM model"""
    global lstm_model
    if lstm_model is None:
        logger.info("Loading ImportForecastLSTM on demand")
        try:
            lstm_model = ImportForecastLSTM(lookback=LSTM_SEQUENCE_LENGTH, features=LSTM_NUM_FEATURES)
            if LSTM_MODEL_PATH.exists():
                lstm_model.load_model(str(LSTM_MODEL_PATH))
            else:
                lstm_model.build_model()
        except Exception as exc:
            logger.warning("Fallback to fresh ImportForecastLSTM due to: %s", exc)
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
