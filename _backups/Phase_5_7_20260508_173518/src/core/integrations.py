import json
import time
import os
import re
import logging
from json_repair import repair_json # <--- Import Healer

logger = logging.getLogger(__name__)

class IntegrationManager:
    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.save_dir = "my_workflows"
        os.makedirs(self.save_dir, exist_ok=True)

    def _sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    def deploy_internal(self, store_id, blueprint_json, name="New Automation"):
        print(f"    [Internal] Saving workflow '{name}'...")
        
        # --- ROBUST VALIDATION & REPAIR ---
        try:
            if isinstance(blueprint_json, str):
                # Try standard load first
                try:
                    payload = json.loads(blueprint_json)
                except json.JSONDecodeError:
                    # If fail, try repair
                    print("    [Warning] Malformed JSON detected. Repairing...")
                    payload = repair_json(blueprint_json, return_objects=True)
            else:
                payload = blueprint_json
                
            if not payload:
                raise ValueError("Empty JSON after repair")
                
        except Exception as e:
            return {"status": "error", "message": f"Invalid JSON format: {e}"}

        # 1. SAVE TO DB
        wf_id = self.memory.save_workflow(store_id, name, payload)
        
        # 2. SAVE TO FILE
        safe_name = self._sanitize_filename(name)
        filename = f"{self.save_dir}/WF_{wf_id}_{safe_name}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        return {
            "status": "success",
            "workflow_id": wf_id,
            "file_path": filename,
            "message": "Workflow saved (Auto-Repaired)."
        }

    def post_to_social(self, platform, content):
        time.sleep(1)
        return {"status": "published", "link": "http://fb.com/post/123"}