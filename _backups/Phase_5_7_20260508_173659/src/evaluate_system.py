import sys
import os
import json
import time
from json_repair import repair_json
from openai import OpenAI

# --- PATH FIXER (CRITICAL FOR COLAB) ---
current_dir = os.path.dirname(os.path.abspath(__file__)) 
project_root = os.path.dirname(current_dir)              
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---------------------------------------

from src.core.engine import ModelEngine
from src.core.memory import MemoryManager
from src.agents.manager import ManagerAgent
from src.agents.coder import CoderAgent

# --- CONFIGURATION ---
DATASET_PATH = os.path.join(project_root, "src", "data", "training_dataset.jsonl")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
TEST_LIMIT = 10 # Number of workflows to test per run to save time/API costs

class DeepSeekJudge:
    def __init__(self):
        if not DEEPSEEK_API_KEY:
            print("⚠️ WARNING: DEEPSEEK_API_KEY not found in environment. The Judge will be disabled.")
            self.client = None
        else:
            self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    def grade_workflow(self, prompt: str, expected_json: str, actual_json: str) -> dict:
        if not self.client:
            return {"score": 0, "rationale": "DeepSeek API Key missing. Grading skipped."}

        system_prompt = """You are a Senior Retail Automation Engineer acting as an impartial judge.
Your job is to grade an AI-generated Make.com JSON workflow against a Ground Truth blueprint.

CRITERIA:
5 = Perfect. Logically identical to the ground truth and solves the user's prompt.
4 = Good. Minor structural differences, but functionally correct.
3 = Acceptable. Needs minor manual fixing by the user to work.
2 = Poor. Major logic flaws, missing critical nodes, or hallucinated tools.
1 = Fail. Invalid JSON, completely wrong intent, or empty.

OUTPUT FORMAT:
You must output ONLY a valid JSON object with two keys: "score" (integer 1-5) and "rationale" (short string explaining why)."""

        user_prompt = f"""USER REQUEST: {prompt}

GROUND TRUTH BLUEPRINT:
{expected_json}

AI GENERATED WORKFLOW:
{actual_json}"""

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0.0
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {"score": 0, "rationale": f"Judge API Error: {e}"}

def load_test_data(filepath: str, limit: int):
    """Automatically loads test cases from the fine-tuning JSONL dataset."""
    dataset =[]
    if not os.path.exists(filepath):
        print(f"❌ Dataset not found at: {filepath}")
        return dataset

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            # The format is: system (0), user (1), assistant (2)
            user_msg = data['messages'][1]['content']
            expected_json = data['messages'][2]['content']
            dataset.append({
                "prompt": user_msg,
                "expected": expected_json
            })
            if len(dataset) >= limit:
                break
    return dataset

def evaluate_pipeline():
    print("🎓 Booting Production Evaluation Suite...\n" + "="*60)
    
    # 1. Initialize Components
    try:
        engine = ModelEngine()
        memory = MemoryManager()
        manager = ManagerAgent(engine, memory)
        coder = CoderAgent(engine, memory)
        judge = DeepSeekJudge()
    except Exception as e:
        print(f"❌ Failed to load AI Engine: {e}")
        return

    # 2. Load Data
    test_cases = load_test_data(DATASET_PATH, TEST_LIMIT)
    if not test_cases:
        return
    print(f"📂 Loaded {len(test_cases)} real test cases from {DATASET_PATH}")

    # 3. Metrics Tracking
    metrics = {
        "total_runs": 0,
        "valid_json_count": 0,
        "total_latency_sec": 0.0,
        "total_approx_tokens": 0,
        "total_business_score": 0
    }

    print("\n" + "="*60)
    print("🚀 RUNNING BATCH EVALUATION")
    print("="*60)

    for i, test in enumerate(test_cases, 1):
        print(f"\n▶️ Test {i}/{len(test_cases)}")
        print(f"   Prompt: '{test['prompt'][:80]}...'")
        
        # --- TIMED EXECUTION ---
        start_time = time.time()
        
        # Routing & Planning
        decision = manager.analyze_task(test['prompt'])
        plan = manager.plan_or_ask(test['prompt'])
        
        # Generation
        raw_code = coder.write_code(test['prompt'], plan)
        
        latency = time.time() - start_time
        # Rough token approximation for Vietnamese/Code (1 token ~= 3.5 chars)
        approx_tokens = len(raw_code) / 3.5 
        tps = approx_tokens / latency
        
        # --- JSON VALIDATION ---
        is_valid = False
        final_json_str = raw_code
        try:
            parsed_data = json.loads(raw_code)
            is_valid = True
        except json.JSONDecodeError:
            try:
                parsed_data = repair_json(raw_code, return_objects=True)
                if parsed_data:
                    final_json_str = json.dumps(parsed_data)
                    is_valid = True
            except (TypeError, ValueError):
                pass

        # --- DEEPSEEK JUDGE ---
        print(f"   ⚖️  Calling DeepSeek Judge...")
        evaluation = judge.grade_workflow(test['prompt'], test['expected'], final_json_str)
        score = evaluation.get("score", 0)
        rationale = evaluation.get("rationale", "No rationale provided.")

        # --- LOGGING ---
        metrics["total_runs"] += 1
        metrics["total_latency_sec"] += latency
        metrics["total_approx_tokens"] += approx_tokens
        if is_valid: metrics["valid_json_count"] += 1
        metrics["total_business_score"] += score

        print(f"   ⏱️  Performance: {latency:.2f}s | {tps:.1f} Tokens/Sec")
        print(f"   ✅  JSON Valid:  {is_valid}")
        print(f"   ⭐  Judge Score: {score}/5")
        print(f"   🧠  Rationale:   {rationale}")

    # --- FINAL REPORT ---
    print("\n" + "="*60)
    print("📊 FINAL EVALUATION REPORT")
    print("="*60)
    
    avg_latency = metrics["total_latency_sec"] / metrics["total_runs"]
    avg_tps = metrics["total_approx_tokens"] / metrics["total_latency_sec"]
    validity_rate = (metrics["valid_json_count"] / metrics["total_runs"]) * 100
    avg_score = metrics["total_business_score"] / metrics["total_runs"]

    print(f"⚡ Hardware Efficiency (A100):")
    print(f"   - Average Latency per Task: {avg_latency:.2f} seconds")
    print(f"   - Average Throughput:       {avg_tps:.1f} Tokens/Second")
    
    print(f"\n🧩 Software Reliability:")
    print(f"   - JSON Validity Rate:       {validity_rate:.1f}%")
    
    print(f"\n🧠 Business Accuracy (DeepSeek Judge):")
    print(f"   - Average Score:            {avg_score:.1f} / 5.0")
    
    if avg_score >= 4.0:
        print("\n🟢 STATUS: PRODUCTION READY. The model understands retail logic.")
    elif avg_score >= 3.0:
        print("\n🟡 STATUS: NEEDS PROMPT TUNING. The model works but makes minor mistakes.")
    else:
        print("\n🔴 STATUS: NEEDS FINE-TUNING. The model is failing to grasp the workflow logic.")

if __name__ == "__main__":
    evaluate_pipeline()