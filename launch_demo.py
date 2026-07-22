import os
import subprocess
import sys
import shutil
import threading
import time
import nest_asyncio

import pyngrok.installer
pyngrok.installer.install_ngrok = lambda *args, **kwargs: None
from pyngrok import conf
from pyngrok import ngrok



nest_asyncio.apply()

def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def vram_monitor_thread(project_root):
    """
    Background thread to monitor VRAM usage.
    If VRAM > 90%, it generates an artifact alert.
    """
    try:
        import torch
    except ImportError:
        return

    alert_file = os.path.join(project_root, "VRAM_Alert.md")
    while True:
        try:
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated()
                reserved = torch.cuda.memory_reserved()
                max_memory = torch.cuda.get_device_properties(0).total_memory
                if max_memory > 0:
                    percent_used = (allocated / max_memory) * 100
                    if percent_used > 90.0:
                        with open(alert_file, "w") as f:
                            f.write(f"# VRAM CRITICAL ALERT\n\nVRAM Usage has exceeded 90% ({percent_used:.1f}%).\nFallback mechanism triggered.")
                        print(f"\n[ALERT] VRAM exceeded 90%: {percent_used:.1f}%")
        except Exception:
            pass
        time.sleep(10)

def main():
    print("Setting up Project A demo environment...")
    # This gets the folder where 'launch_demo.py' actually lives
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Project root detected: {project_root}")

    # Start VRAM monitor
    monitor = threading.Thread(target=vram_monitor_thread, args=(project_root,), daemon=True)
    monitor.start()

    # 2. PREPARE ENVIRONMENT
    env = os.environ.copy()
    env["DATABASE_URL"] = _require_env("DATABASE_URL")
    
    # CRITICAL FIX: Add project_root to PYTHONPATH
    # This tells Python/Uvicorn: "Look for modules in this folder first"
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    env["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

    # 3. INSTALL DRIVERS (If missing)
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("Installing psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])

    ngrok_path = shutil.which("ngrok")
    if ngrok_path:
        conf.get_default().ngrok_path = ngrok_path

    ngrok_token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)

    try:
     public_url = ngrok.connect(8000).public_url
     print("\n==================================================================")
     print(f"PUBLIC URL: {public_url}")
     print("==================================================================\n")
    except Exception as e:
     print(f"Ngrok error: {e}")

    # 4. LAUNCH UVICORN
    # We remove '--reload' for Colab stability (it causes multiprocessing issues in notebooks)
    cmd = [
        "uvicorn", 
        "src.api.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    print(f"Executing server in: {project_root}")
    
    # We pass 'cwd=project_root' to ensure Uvicorn runs INSIDE the correct folder
    subprocess.run(cmd, cwd=project_root, env=env)

if __name__ == "__main__":
    main()