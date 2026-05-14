import os
import sys

# Add dl_service to system path so its internal imports (like 'services', 'utils') work
current_dir = os.getcwd()
dl_service_path = os.path.join(current_dir, 'dl_service')
sys.path.append(dl_service_path)

try:
    from model_app import app
except ImportError as e:
    print(f"Error importing DL app: {e}")
    # Fallback: try importing as package if path setup failed
    try:
        from dl_service.model_app import app
    except ImportError:
        raise e

if __name__ == "__main__":
    print("Starting Deep Learning Service on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
