import os
import json
import time
import glob
from pypdf import PdfReader
from openai import OpenAI

# --- CONFIGURATION ---
API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-reasoner" # The R1 model

DOCS_DIR = "/content/drive/MyDrive/ProjectA_Backup/src/data/docs"
OUTPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/distilled_reasoning_deepseek.jsonl"
def extract_content_from_files():
    print(f"📂 Scanning {DOCS_DIR}...")
    docs = []
    
    # 1. Read PDFs
    pdf_files = glob.glob(os.path.join(DOCS_DIR, "*.pdf"))
    for fpath in pdf_files:
        try:
            reader = PdfReader(fpath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            docs.append({"source": os.path.basename(fpath), "text": text})
        except Exception as e:
            print(f"❌ Error reading PDF {fpath}: {e}")

    # 2. Read TXT/MD (Your Policy Files)
    txt_files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for fpath in txt_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                docs.append({"source": os.path.basename(fpath), "text": f.read()})
        except Exception as e:
            print(f"❌ Error reading TXT {fpath}: {e}")

    print(f"✅ Loaded {len(docs)} documents.")
    return docs

def chunk_text(text, chunk_size=2000):
    """Splits long text into manageable chunks for the Teacher."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def generate_synthetic_data(client, chunks):
    dataset = []
    print(f"🧪 Starting Distillation using {MODEL_NAME}...")
    print("   (This takes time because DeepSeek 'Thinks' before answering)")
    
    for i, chunk in enumerate(chunks):
        print(f"   👉 Processing Chunk {i+1}/{len(chunks)}...")
        
        # The Teacher Prompt
        prompt = f'''
        SOURCE DOCUMENT:
        """{chunk}"""
        
        TASK:
        You are an Expert Retail Data Generator. 
        Based on the text above, create a Realistic Scenario for a Vietnamese Store Owner.
        
        1. **User Query:** A specific, natural question a user would ask about this topic (in Vietnamese).
        2. **Reasoning:** Explain HOW to solve it based on the text (Chain of Thought).
        3. **Response:** The final answer to the user (in Vietnamese).
        
        OUTPUT JSON FORMAT:
        {{
            "user_query": "...",
            "thought_process": "...",
            "response": "..."
        }}
        '''
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ 'type': 'json_object' } 
            )
            
            # DeepSeek Reasoner separates 'reasoning_content' (internal) and 'content' (final)
            # But for training data, we want to CAPTURE the reasoning to teach Qwen.
            # Note: The API puts the "Think" trace in a special field sometimes, 
            # but usually 'deepseek-reasoner' outputs the final answer in 'content'.
            # We trust the model to follow the JSON schema we gave it in the prompt.
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Construct Training Entry
            # We wrap the thought in <think> tags so Qwen learns to mimic it
            full_response = f"<think>{data['thought_process']}</think>\n{data['response']}"
            
            entry = {
                "messages": [
                    {"role": "system", "content": "You are Project A, an expert Retail Consultant."},
                    {"role": "user", "content": data['user_query']},
                    {"role": "assistant", "content": full_response}
                ]
            }
            
            dataset.append(entry)
            print(f"      ✅ Generated: {data['user_query'][:50]}...")
            
        except Exception as e:
            print(f"      ⚠️ API Error: {e}")
            
    return dataset

def main():
    if not API_KEY:
        raise RuntimeError("Missing required environment variable: DEEPSEEK_API_KEY")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    # 1. Load Docs
    docs = extract_content_from_files()
    if not docs:
        print("❌ No documents found in src/data/docs")
        return

    # 2. Chunking
    all_chunks = []
    for doc in docs:
        # Limit to first 3 chunks per doc to save API credits for this test
        # Remove [:3] to process the whole file
        file_chunks = chunk_text(doc['text'])[:3] 
        all_chunks.extend(file_chunks)
        
    print(f"📊 Prepared {len(all_chunks)} chunks for distillation.")

    # 3. Distill
    new_data = generate_synthetic_data(client, all_chunks)
    
    # 4. Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for entry in new_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"🎉 Distillation Complete! Saved {len(new_data)} samples.")
    print(f"📁 File: {OUTPUT_FILE}")
    print("👉 Now combine this with your 'training_dataset.jsonl' and Fine-Tune!")

if __name__ == "__main__":
    main()