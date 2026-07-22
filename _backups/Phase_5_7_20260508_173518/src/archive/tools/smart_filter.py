import json
import sqlite3
import os
from openai import OpenAI

# CONFIG
API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
BASE_URL = "https://api.deepseek.com"
DB_PATH = "src/data/project_a.db"

def update_database_price(product_name, new_price):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET price = ? WHERE name LIKE ?", (new_price, f"%{product_name}%"))
    conn.commit()
    conn.close()
    print(f"   💾 SQL UPDATE: Set '{product_name}' to {new_price}")

def process_feedback(feedback_file):
    print("🧠 Smart Filter: Analyzing Feedback...")
    if not os.path.exists(feedback_file):
        print("   No feedback file found.")
        return []
    if not API_KEY:
        raise RuntimeError("Missing required environment variable: DEEPSEEK_API_KEY")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    training_data = []
    
    with open(feedback_file, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        try:
            entry = json.loads(line)
            prompt = entry['prompt']
            bad_response = entry['rejected']
            user_input = entry['chosen'] # This could be a rewrite OR an instruction
            
            # TEACHER ANALYSIS
            analysis_prompt = f'''
            CONTEXT:
            User asked: "{prompt}"
            AI answered: "{bad_response}"
            User gave feedback: "{user_input}"
            
            TASK:
            1. Is the user's feedback a FACT update (Price/Stock)? -> Output JSON type="FACT"
            2. Is the user's feedback a FULL REWRITE (They wrote exactly what the AI should say)? -> Output JSON type="REWRITE"
            3. Is the user's feedback an INSTRUCTION (e.g., "Too long", "Be polite")? -> Output JSON type="INSTRUCTION"
            
            OUTPUT JSON ONLY: {{ "type": "...", "product": "...", "value": "...", "improved_response": "..." }}
            
            If type is INSTRUCTION, you (Teacher) must rewrite the 'AI answered' text to follow the instruction and put it in 'improved_response'.
            If type is REWRITE, put the user's text in 'improved_response'.
            '''
            
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": analysis_prompt}],
                response_format={ 'type': 'json_object' }
            )
            decision = json.loads(response.choices[0].message.content)
            
            if decision["type"] == "FACT":
                update_database_price(decision.get("product"), decision.get("value"))
            else:
                # Whether it was a Rewrite or an Instruction, the Teacher has now 
                # given us the perfect 'improved_response' string.
                final_good_response = decision["improved_response"]
                
                # Create Training Entry
                train_entry = {
                    "messages": [
                        {"role": "system", "content": "You are Project A, a Retail Assistant."},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": final_good_response}
                    ]
                }
                
                print(f"   📘 Learned Style: {user_input} -> Generated: {final_good_response[:30]}...")
                training_data.append(train_entry)
                
        except Exception as e:
            print(f"   ⚠️ Error processing line: {e}")
            
    # Clear feedback file
    os.remove(feedback_file)
    return training_data