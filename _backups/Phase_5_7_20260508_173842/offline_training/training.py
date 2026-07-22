import os
import sys
import json
import asyncio
from pathlib import Path

# Add project root to sys.path to allow imports from src
root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

async def generate_teacher_data():
    """
    Query DeepSeek-R1 API to generate Chain-of-Thought datasets.
    In LOCAL mode, uses mock data. In COLAB mode, replace mock block with
    actual httpx calls via HttpClientPool.
    """
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "mock-key")
    
    prompts = [
        "Explain the VAT reduction under Decree 72/2024/NĐ-CP for software products.",
        "Calculate the total for an invoice with 2 items at 50,000 VND (8% VAT) and 1 item at 100,000 VND (10% VAT)."
    ]
    
    dataset = []
    
    for prompt in prompts:
        try:
            # TODO(COLAB): Replace this mock block with:
            #   from src.core.utils import HttpClientPool
            #   client = HttpClientPool.get_client()
            #   response = await client.post(url, json=payload, headers=headers)
            #   data = response.json()
            data = {
                "choices": [{
                    "message": {
                        "reasoning_content": "First, I need to identify the VAT rates. Decree 72/2024 reduces VAT from 10% to 8% for applicable groups...",
                        "content": "The VAT reduction applies..."
                    }
                }]
            }
            
            msg = data["choices"][0]["message"]
            think_tag = msg.get("reasoning_content", "")
            final_answer = msg.get("content", "")
            
            # Format for Unsloth / HuggingFace SFT
            dataset.append({
                "instruction": prompt,
                "reasoning": think_tag,
                "output": final_answer,
                "text": f"User: {prompt}\nAssistant: <think>\n{think_tag}\n</think>\n{final_answer}"
            })
        except Exception as e:
            print(f"Failed to generate data for prompt: {e}")
            
    # Save to JSONL
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True, parents=True)
    out_file = output_dir / "distillation_v1.jsonl"
    
    with open(out_file, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"Saved {len(dataset)} items to {out_file}")

if __name__ == "__main__":
    asyncio.run(generate_teacher_data())
