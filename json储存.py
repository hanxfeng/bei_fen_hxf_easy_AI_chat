import json
from datetime import datetime

with open ('测试.json','r',encoding='utf-8') as f:
    data = json.load(f)

new_entry = {
            "instruction": "text",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output": "ai_response"
        }
data.append(new_entry)
print(data)
with open('测试.json', "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
