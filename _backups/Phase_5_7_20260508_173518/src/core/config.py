
import os

class Config:
    def __init__(self):
        # Path Setup
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.DATA_DIR = os.path.join(self.PROJECT_ROOT, 'src', 'data')
        
        # Database
        raw_url = os.getenv("DATABASE_URL", "")
        if raw_url.startswith("postgres://"):
            self.DB_URL = raw_url.replace("postgres://", "postgresql+psycopg2://")
        elif raw_url.startswith("postgresql://"):
            self.DB_URL = raw_url.replace("postgresql://", "postgresql+psycopg2://")
        else:
            self.DB_URL = "sqlite:///:memory:"

        self.DOCS_DIR = os.path.join(self.DATA_DIR, 'docs') 
        os.makedirs(self.DATA_DIR, exist_ok=True)
        
        self.SYSTEM_CONTEXT = "You are Project A, a Retail Automation Architect."

        # --- HEAVYWEIGHT UPGRADE ---
        # Brain: 32B Parameter Model (AWQ for speed/memory efficiency on A100)
        self.text_model_id = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"
        
        # Eye: 7B Vision Model (Native BFloat16)
        self.vision_model_id = "Qwen/Qwen2-VL-7B-Instruct"
        
        # vLLM Config
        self.vllm_config = {
            "gpu_memory_utilization": 0.5, # Give 50% (40GB) to the 32B model
            "max_model_len": 8192,         # Huge context window
            "dtype": "half"                # AWQ requires half/float16
        }
