import json
import random

OUTPUT_FILE = "/content/drive/MyDrive/ProjectA_Backup/src/data/reasoning_dataset.jsonl"

# These are the "Patterns" you want the model to learn.
# Instead of 1 input -> 1 output, we teach it to THINK first.

scenarios = [
    {
        "input": "Doanh thu tháng này thấp quá, tôi nên làm gì?",
        "context": "Store: Fashion, Location: Hanoi, Season: Winter",
        "reasoning": "1. Analyze context: Winter in Hanoi = Cold. Fashion store. Low sales.
2. Strategy: Push winter clearance or warm combos.
3. Action: Suggest specific promotion.",
        "response": "Chào bạn, với thời tiết lạnh tại Hà Nội hiện nay, nếu doanh thu đang chậm, bạn nên kiểm tra lại kho áo len/áo khoác. Tôi đề xuất chạy chương trình 'Combo Giữ Ấm' giảm 10% khi mua Áo + Khăn len. Bạn có muốn tôi viết bài quảng cáo cho combo này không?"
    },
    {
        "input": "Hàng tồn kho bia nhiều quá.",
        "context": "Store: Grocery, Location: HCM, Season: Near Tet",
        "reasoning": "1. Context: Grocery store near Tet holiday. High beer inventory.
2. Insight: People buy beer for parties/gifts.
3. Action: Suggest bulk discounts or gift wrapping.",
        "response": "Sắp đến Tết rồi, đây là cơ hội tốt để đẩy hàng bia. Thay vì bán lẻ, bạn hãy đóng gói thành 'Giỏ Quà Tết' kèm với bánh kẹo. Khách hàng thường thích mua combo biếu tặng tiện lợi. Bạn có cần tôi tạo mẫu giỏ quà không?"
    }
]

def generate_dataset():
    print(f"🧠 Generating Reasoning Data...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for scen in scenarios:
            # We format this into the Qwen Chat format
            # We HIDE the reasoning in the response so the model learns to output the RESULT based on the implicit logic,
            # OR we can include the reasoning if we want to use Chain-of-Thought.
            # For 14B, it's better to fine-tune on the RESULT, but ensure the data quality is high.
            
            user_text = f"Context: {scen['context']}\nQuestion: {scen['input']}"
            
            entry = {
                "messages": [
                    {"role": "system", "content": "You are a Retail Consultant. Use context to give specific business advice."},
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": scen['response']}
                ]
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
    print(f"✅ Saved {len(scenarios)} reasoning examples to {OUTPUT_FILE}")
    print("👉 Add more examples to 'scenarios' list in this script to build a brain.")

if __name__ == "__main__":
    generate_dataset()