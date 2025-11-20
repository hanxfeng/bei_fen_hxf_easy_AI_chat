import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
import threading
import logging
import dns

# 启用协程支持

# 基本配置
app = Flask(__name__)
token_path = "server_config/token.txt"  # 替换为自定义token
with open(token_path, "r", encoding='utf-8') as file:
    SECRET_TOKEN = file.read()  # 加载token
# SocketIO配置
socketio = SocketIO(
    app,
    async_mode='eventlet',
    cors_allowed_origins="*",
    ping_interval=25,  # 心跳包发送间隔
    ping_timeout=120  # 超时时间（适应模型推理耗时）
)

# 请求速率限制
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["5 per minute"]
)

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forward_server")

# （存储待处理的推理任务）
pending_tasks = {}


# WebSocket事件处理
@socketio.on("connect")
def handle_connect(auth):
    """验证模型服务器连接的token"""
    token = auth.get("token") if auth else None
    if token != SECRET_TOKEN:
        logger.warning(f"非法模型服务器连接，IP: {request.remote_addr}")
        disconnect()
        return
    logger.info("模型服务器连接成功，token验证通过")


@socketio.on("disconnect")
def handle_disconnect():
    """处理模型服务器断开连接事件"""
    logger.info("模型服务器已断开连接")


@socketio.on("infer_response")
def handle_response(data):
    """接收模型服务器的推理结果并通知等待的请求"""
    task_id = data.get("task_id")
    if task_id in pending_tasks:
        pending_tasks[task_id]["result"] = data["response"]
        pending_tasks[task_id]["event"].set()  # 触发事件通知
        logger.info(f"任务 {task_id} 收到模型响应")
    else:
        logger.warning(f"收到未知任务 {task_id} 的响应")


# HTTP请求安全校验
@app.before_request
def verify_token():
    """验证所有HTTP请求的token"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != SECRET_TOKEN:
        logger.warning(f"拒绝非法HTTP请求，IP: {request.remote_addr}")
        return jsonify({"error": "Unauthorized"}), 401


# 推理请求接口
@app.route("/chat", methods=["POST"])
@limiter.limit("5/minute")  # 限制每分钟最多5次请求
def infer():
    """接收客户端推理请求，转发给模型服务器并返回结果"""
    try:
        data = request.json or {}
        # 提取输入文本（支持text或messages字段）
        text = (data.get("text") or data.get("messages") or "").strip()
        if not text:
            return jsonify({"error": "Invalid input"}), 400

        # 生成唯一任务ID并创建事件
        task_id = str(uuid.uuid4())
        event = threading.Event()
        pending_tasks[task_id] = {"event": event, "result": None}

        # 转发请求到模型服务器
        socketio.emit("infer_request", {"text": text, "task_id": task_id})
        logger.info(f"任务 {task_id} 已发送至模型服务器，等待响应...")

        # 等待响应（超时90秒）
        if event.wait(timeout=90):
            result = pending_tasks[task_id]["result"]
            del pending_tasks[task_id]  # 清理任务缓存
            return jsonify({"response": result})
        else:
            del pending_tasks[task_id]
            logger.error(f"任务 {task_id} 超时无响应")
            return jsonify({"error": "模型服务器无响应"}), 504

    except Exception as e:
        logger.exception("处理请求时发生错误")
        return jsonify({"error": "Internal server error"}), 500


# 启动服务
if __name__ == "__main__":
    with app.app_context():
        logger.info("转发服务器启动，监听 0.0.0.0:8080")
        socketio.run(app, host="0.0.0.0", port=8080)

    # pyinstaller --onefile --clean --hidden-import=engineio.async_drivers.eventlet --hidden-import=engineio.async_drivers.gevent --hidden-import=engineio.async_drivers.threading --additional-hooks-dir=./hooks --add-data "server_config;server_config" --icon=1icon.ico server.py
