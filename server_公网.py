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


@sio.on("history_request")
def handle_history_request(data):
    """接收服务器请求历史记录，生成回复后通过Socket.IO回传结果"""
    task_id = data.get("task_id")

    def send_history_response():
        """在子线程中执行，避免阻塞主线程"""
        try:
            print("已收到历史记录请求")
            # 调用函数获取结构化历史记录
            history_data = get_history()

            # 使用新的事件名 "history_response"
            sio.emit("history_response", {
                "task_id": task_id,
                "history_data": history_data  # 发送整个字典
            })
            print(f"任务 {task_id} 历史记录已发送")

        except Exception as e:
            print(f"任务 {task_id} 历史记录发送失败: {e}")
            sio.emit("history_response", {
                "task_id": task_id,
                "history_data": {"error": f"获取历史记录失败: {str(e)}"}
            })

    # 启动子线程处理，避免阻塞 SocketIO 客户端
    thread = threading.Thread(
        target=send_history_response,
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
