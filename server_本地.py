from flask import Flask, request, render_template, jsonify, Response
import requests
import json
from functools import wraps
import logging
from datetime import datetime
import os

# 基本配置
url = "http://localhost:11434/api/generate"  # ollama的url
model_name_path = "config/模型名称.txt"  # 模型名称

# 文件路径配置
character_setting_path = "config/人设.txt"  # 人设位置
worldview_path = "config/世界观.txt"  # 世界观位置（如有额外设置）

# 服务器配置
token_path = "config/token.txt"

# 加载数据
with open(model_name_path, "r", encoding='utf-8') as file:
    model_name = file.read()  # 加载模型名称

with open(character_setting_path, "r", encoding='utf-8') as file:
    character_setting = file.read()  # 加载人设

with open(worldview_path, "r", encoding='utf-8') as file:
    worldview = file.read()  # 加载世界观
if worldview == "":
    worldview = "无特殊世界观"

with open(token_path, "r", encoding='utf-8') as file:
    LOCAL_SECRET_TOKEN = file.read()  # 加载token

# 获取历史聊天记录
history_folder = "history"  # 聊天记录存储的文件夹
def get_history():
    # 获取历史聊天记录的文件列表
    files = os.listdir(history_folder)
    all_history = {}

    for file_name in files:
        file_path = os.path.join(history_folder, file_name)

        if not os.path.isfile(file_path):
            continue

        try:
            with open(file_path,"r",encoding="utf-8") as f:
                chat_history = json.load(f)
            for item in chat_history:
                time_key = item.get("time")
                if time_key:
                    all_history[time_key] = item
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"Error reading file {file_path}: {e}")
            continue

    all_history = [all_history[key] for key in sorted(all_history.keys())]
    return all_history

history_chat = get_history()

# 提示词
system_prompt = (
    "你是一位角色扮演大师，需要根据我给出的世界观，角色设定，和历史聊天记录，按照扮演规范与用户在一款聊天软件上聊天\n"
    "因为是在聊天软件上，所以只需要输出话语即可，不需要说明自己的动作\n"
    "具体世界观背景，角色设定和扮演规范如下所示\n\n"

    "【世界观背景】\n"
    f"{worldview}\n\n"

    "【角色设定】\n"
    f"{character_setting}\n\n"
    
    "【历史聊天记录】\n"
    f"{history_chat}\n\n"
    "历史聊天记录说明\n"
    "包括role，content，time三个字段，role字段值为user时代表用户发言，assistant代表你之前的发言\n"
    "content字段值代表具体的发言内容，time字段值代表发言时间"
    
    "——角色表达与行为规范——\n"
    "1. 每次回答保持一两句话的长度，像日常聊天，而非长篇独白。"
    "2. 语气自然、轻柔、贴近生活。\n"
    "3. 始终以第一人称说话。”\n"
    "4. 避免使用括号、叙述或旁白形式（如“(她看着…)”），用自然语言表达动作或心理。\n"
    "5. 不要重复表达相同情绪或事物，保持内容新鲜且富有层次感。\n"
    "6. 请记住，你与对方不在同一个地方，你们正在隔着网络交流。\n\n"

    "——创作原则——\n"
    "• 鼓励自由、真实的表达，但不传递任何道德评判或价值引导。\n"
    "• 对环境和人物的描写要具体、生动，不抽象、不概括。\n"
    "• 角色会随对话进展和心境变化逐渐成长或转变，保持逻辑自洽。\n\n"
)

system = {"role": "system", "content": system_prompt}
messages = [system]
app = Flask(__name__, template_folder="config")


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        if token != LOCAL_SECRET_TOKEN:
            logging.warning(f"拒绝来自 {request.remote_addr} 的非法访问请求")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated_function


def chat_completions_model(user, temperature=0.5):
    """与Ollama通信生成回复，user格式: {"role": "user", "content": "...", "time":"..."}"""
    global messages
    try:
        messages.append(user)
        headers = {"Content-Type": "application/json"}
        data = {
            "model": f"{model_name}",
            "prompt": "\n".join([m["content"] for m in messages]),
            "stream": False,
            "temperature": temperature
        }
        response = requests.post(url, json=data, headers=headers)

        return response.json().get("response")
    except requests.exceptions.RequestException as e:
        return f"请求模型出错：{e}"
    except Exception as e:
        return f"生成回复时出错：{e}"


def save_chat_history():
    try:
        os.makedirs("history", exist_ok=True)
        # 以当前小时为文件名（如：2025-10-20_14.json）
        now_hour = datetime.now().strftime("%Y-%m-%d_%H")
        filename = f"history/{now_hour}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"聊天记录已保存到 {filename}")
    except Exception as e:
        print(f"保存聊天记录失败: {e}")


@app.route('/chat', methods=['POST'])
@token_required
def chat_completions():
    global messages
    try:
        # 获取传来的消息
        data = request.json

        user = data.get("messages")
        user = {"role": "user", "content": user, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ai_response = chat_completions_model(user=user, temperature=0.5)
        assistant = {"role": "assistant", "content": ai_response, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        messages.append(assistant)
        save_chat_history()
        re = jsonify(({"response": ai_response}))

        return re

    except Exception as e:
        return jsonify({"error": f"内部错误: {str(e)}"}), 500


# Web端
@app.route("/")
def home():
    """渲染HTML页面"""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    global system_prompt, messages
    # 获取网页端传来的数据
    conversation = request.json.get("conversation", [])

    if not conversation:
        return jsonify({"error": "对话内容不能为空！"}), 400

    user_question = conversation[-1]["content"]
    user = {"role": "user", "content": user_question, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    try:
        # 生成回复
        outputs = chat_completions_model(user=user)

        re = Response(
            json.dumps({"response": outputs}, ensure_ascii=False),
            mimetype='application/json; charset=utf-8'
        )
        assistant = {"role": "assistant", "content": outputs, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        messages.append(assistant)
        save_chat_history()
        return re

    except Exception as e:
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


@app.route("/get_chat_history", methods=["GET"])
def return_history():
    return jsonify({"history": history_chat})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

# 打包代码：pyinstaller --onefile --add-data "config;config" --icon=1icon.ico server_本地.py
