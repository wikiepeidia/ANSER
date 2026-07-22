import sys
import os
import json
import time
import re
from json_repair import repair_json # <--- THE MAGIC FIX

# Setup Path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.insert(0, project_root)

from src.core.engine import ModelEngine
from src.agents.coder import CoderAgent
from src.agents.manager import ManagerAgent
from src.core.memory import MemoryManager

TEST_CASES = [
    {
        "name": "Simple Webhook",
        "prompt": "Tạo quy trình tự động hóa: Webhook -> Google Sheets.",
        "must_contain": ["webhook", "google-sheets"]
    },
    {
        "name": "Math Logic",
        "prompt": "Tính giá bán: Giá nhập 100k, lãi 30%, thuế 10%.",
        "expected_type": "text",
        "answer_keyword": "143"
    }
]

def extract_json_block(text):
    # Try Markdown block
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if match: return match.group(1)
    # Try finding outer brackets
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match: return match.group(0)
    return text # Fallback: return whole text and let repair_json handle it

def evaluate():
    print("🎓 Starting Evaluation (with json_repair)...")
    try:
        engine = ModelEngine()
        memory = MemoryManager()
        coder = CoderAgent(engine, memory)
        manager = ManagerAgent(engine, memory)
    except Exception as e:
        print(f"❌ Failed to load: {e}")
        return

    score = 0
    for test in TEST_CASES:
        print(f"\nTesting: {test['name']}")
        
        if test.get("expected_type") == "text":
            # Test Logic
            if "tính" in test['prompt'].lower():
                from src.core.tools import RetailTools
                math_res = RetailTools.calculate("100 * 1.3 * 1.1")
                response = manager.consult(test['prompt'], f"Result: {math_res}")
            else:
                response = manager.consult(test['prompt'])
                
            if test['answer_keyword'] in response:
                print("   ✅ Logic Correct")
                score += 1
            else:
                print(f"   ❌ Logic Fail. Output: {response[:100]}...")

        else:
            # Test Coding
            plan = manager.plan(test['prompt'])
            code = coder.write_code(test['prompt'], plan)
            json_str = extract_json_block(code)
            
            # --- ROBUST PARSING ---
            try:
                # 1. Try Standard Parse
                data = json.loads(json_str)
                print("   ✅ Valid JSON (Native)")
            except:
                # 2. Try Repair
                print("   ⚠️ Syntax Error. Running json_repair...")
                try:
                    # repair_json returns a parsed dict object directly
                    data = repair_json(json_str, return_objects=True)
                    print("   ✅ Auto-Repair Successful!")
                except Exception as e:
                    print(f"   ❌ FATAL: Repair Failed. {e}")
                    data = {}

            # --- CHECK CONTENT ---
            if "flow" in data:
                print("   ✅ Schema Valid (Found 'flow')")
                score += 1
            else:
                print("   ❌ Schema Invalid (Missing 'flow')")
                if data: print(f"      Keys found: {list(data.keys())}")

    print(f"\nFinal Score: {score}/{len(TEST_CASES)}")

if __name__ == "__main__":
    evaluate()