import os
import sys
from core.logger import get_logger

logger = get_logger(__name__)

# Add dl_service to system path so its internal imports (like 'services', 'utils') work
current_dir = os.getcwd()
dl_service_path = os.path.join(current_dir, 'dl_service')
sys.path.append(dl_service_path)

def create_dl_app():
    try:
        from model_app import app as dl_app
        return dl_app
    except ImportError as e:
        logger.error("Error importing DL app: %s", e)
        # Fallback: try importing as package if path setup failed
        try:
            from dl_service.model_app import app as dl_app
            return dl_app
        except ImportError:
            raise e

if __name__ == "__main__":
    logger.info("Starting Deep Learning Service on port 5001")
    app = create_dl_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
