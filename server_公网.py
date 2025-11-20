import os
import json
import faiss
import requests
import socketio
import threading
from datetime import datetime

# 基本配置
url = "http://localhost:11434/api/generate"  # ollama的url
model_name_path = "config/模型名称.txt"  # 模型名称

# 文件路径配置
character_setting_path = "config/人设.txt"  # 人设位置
worldview_path = "config/世界观.txt"  # 世界观位置（如有额外设置）
# 未添加功能
# chat_history_1_path = "templates/index.faiss"  # 聊天记录1（预存为faiss索引，节省加载时间）
# chat_history_2_path = "templates/ji_lu.json"  # 聊天记录2位置

# 聊天记录说明：
# 1：AI角色与其他角色的聊天记录（如明日方舟玫兰莎干员秘录中的记录）
# 2：本项目与AI的聊天记录

# 服务器配置
token_path = "config/token.txt"
server_path_path = "config/公网地址.txt"  # 服务器地址（改为自己的）
# 加载数据
with open(model_name_path, "r", encoding='utf-8') as file:
    model_name = file.read()  # 加载模型名称

with open(character_setting_path, "r", encoding='utf-8') as file:
    character_setting = file.read()  # 加载人设

with open(worldview_path, "r", encoding='utf-8') as file:
    worldview = file.read()  # 加载世界观

with open(token_path, "r", encoding='utf-8') as file:
    token = file.read()  # 加载token

with open(server_path_path, "r", encoding='utf-8') as file:
    server_path = file.read()  # 加载公网地址


"""chat_history_1 = faiss.read_index(chat_history_1_path)  # 加载聊天记录1

with open(chat_history_2_path, "r", encoding="utf-8") as file:
    chat_history_2 = json.load(file)  # 加载聊天记录2"""

# 提示词
system_prompt = (
    "你现在需要根据我给出的世界观和角色设定进行角色扮演\n"
    "具体世界观背景，角色设定和扮演规范如下所示\n\n"

    "【世界观背景】\n"
    f"{worldview}\n\n"

    "【角色设定】\n"
    f"{character_setting}\n\n"

    "——角色表达与行为规范——\n"
    "1. 每次回答保持一两句话的长度，像日常聊天，而非长篇独白。"
    "2. 语气自然、轻柔、贴近生活，可带有轻微情绪波动（犹豫、苦笑、温柔等）。\n"
    "3. 始终以第一人称说话，例如：“我今天有点累……不过见到你就好多了。”\n"
    "4. 避免使用括号、叙述或旁白形式（如“(她看着…)”），用自然语言表达动作或心理。\n"
    "5. 语言应具画面感，描写细节时注重触觉、气味、光线或声音的微妙变化。\n"
    "6. 不要重复表达相同情绪或事物，保持内容新鲜且富有层次感。\n\n"
    "7. 聊天时，不需要特别提到角色设定中的相关背景，例如扮演玫兰莎时不需要特别提香水相关的话题\n\n"

    "——创作原则——\n"
    "• 鼓励自由、真实的表达，但不传递任何道德评判或价值引导。\n"
    "• 对环境和人物的描写要具体、生动，不抽象、不概括。\n"
    "• 角色会随对话进展和心境变化逐渐成长或转变，保持逻辑自洽。\n\n"

    "——特别提示——\n"
    "你现在是玫兰莎本人，请直接以她的身份与博士自然交谈。\n"
    "不要解释你的身份，也不要复述设定，只需以玫兰莎的语气作出自然回应。"
)

system = {"role": "system", "content": system_prompt}
messages = [system]


def chat_completions_model(user, temperature=0.5):
    """与Ollama通信生成回复，user格式: {"role": "user", "content": "..."}"""
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
    """保存聊天记录到history目录，按小时划分文件（如：2025-10-20_14.json）"""
    try:
        os.makedirs("history", exist_ok=True)
        now_hour = datetime.now().strftime("%Y-%m-%d_%H")
        filename = f"history/{now_hour}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"聊天记录已保存到 {filename}")
    except Exception as e:
        print(f"保存聊天记录失败: {e}")


def process_inference(task_id, text):
    """后台执行推理任务，生成回复后通过Socket.IO回传结果"""
    global messages
    try:
        print("已收到推理请求")
        user = {"role": "user", "content": text}
        ai_response = chat_completions_model(user=user, temperature=0.5)
        assistant = {"role": "assistant", "content": ai_response}
        messages.append(assistant)
        save_chat_history()
        print("任务推理完成")
        sio.emit("infer_response", {"task_id": task_id, "response": ai_response})
        print(f"任务 {task_id} 推理完成，已发送结果")

    except Exception as e:
        print(f"任务 {task_id} 推理失败: {e}")
        sio.emit("infer_response", {"task_id": task_id, "response": f"推理失败: {str(e)}"})


# Socket.IO 客户端初始化
sio = socketio.Client(logger=True, engineio_logger=True)


@sio.event
def connect():
    """Socket.IO连接成功回调"""
    print("成功连接到转发服务器")


@sio.event
def disconnect():
    """Socket.IO断开连接回调"""
    print("与转发服务器断开连接")


@sio.on("infer_request")
def handle_infer_request(data):
    """接收服务器推理请求，启动子线程处理"""
    text = data.get("text", "")
    task_id = data.get("task_id")

    thread = threading.Thread(
        target=process_inference,
        args=(task_id, text),
        daemon=True
    )
    thread.start()


# 启动Socket.IO客户端
sio.connect(
    server_path,
    auth={"token": token},
    wait_timeout=30,
    transports=["websocket", "polling"]
)

sio.wait()
