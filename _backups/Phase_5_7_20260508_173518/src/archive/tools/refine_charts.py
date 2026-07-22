import os
import json
import time
from openai import OpenAI

# --- CONFIGURATION ---
# Use environment variable instead of hardcoding credentials
API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-reasoner"  # Use Thinking Mode for deep analysis

# Input/Output
INPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/chart_data.jsonl"
OUTPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/distilled_reasoning_charts.jsonl"

def load_chart_data():
    data = []
    if os.path.exists(INPUT_FILE):
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
    return data

def distill_charts(client, chunks):
    dataset = []
    print(f"🧪 Starting Chart Distillation (Teacher: {MODEL_NAME})...")
    
    for i, chunk in enumerate(chunks):
        print(f"   📊 Analyzing Chart {i+1}/{len(chunks)} from {chunk['source']}...")
        
        # The Prompt: Forces the Teacher to simulate a business scenario based on the visual data
        prompt = f'''
        CONTEXT: The text below is a computer vision description of a Chart/Graph from a Vietnam Retail Report.
        
        VISUAL DATA:
        """{chunk['content']}"""
        
        TASK:
        1. **Interpret:** What is the key business insight from this graph?
        2. **Scenario:** Imagine a Vietnamese Store Owner asking a question that requires this specific data to answer.
        3. **Reasoning:** Show your internal logic (Chain of Thought).
        4. **Response:** Answer the store owner in Vietnamese, citing the trend in the graph.
        
        OUTPUT JSON FORMAT:
        {{
            "user_query": "The question (Vietnamese)",
            "thought_process": "The reasoning (English or Vietnamese)",
            "response": "The final answer (Vietnamese)"
        }}
        '''
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a JSON Data Generator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ 'type': 'json_object' } 
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Format for Qwen Training
            full_response = f"<think>{data['thought_process']}</think>\n{data['response']}"
            
            entry = {
                "messages": [
                    {"role": "system", "content": "You are Project A, an expert Data Analyst."},
                    {"role": "user", "content": data['user_query']},
                    {"role": "assistant", "content": full_response}
                ]
            }
            
            dataset.append(entry)
            print(f"      ✅ Generated Insight: {data['user_query'][:50]}...")
            
        except Exception as e:
            print(f"      ⚠️ API Error: {e}")
            
    return dataset

def main():
    if not API_KEY:
        raise RuntimeError("Missing required environment variable: DEEPSEEK_API_KEY")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    # 1. Load Data
    chart_chunks = load_chart_data()
    if not chart_chunks:
        print(f"❌ No data found at {INPUT_FILE}. Run 'ingest_charts.py' first.")
        return

    print(f"🔍 Found {len(chart_chunks)} chart descriptions.")

    # 2. Run Distillation
    # Limit to first 20 for demo speed (remove [:20] for full run)
    new_data = distill_charts(client, chart_chunks[:20])
    
    # 3. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in new_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"🎉 Success! Saved {len(new_data)} training samples to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()