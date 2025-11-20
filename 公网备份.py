import os
from flask import Flask, request, render_template, jsonify, Response
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, StoppingCriteria, \
    StoppingCriteriaList, TextIteratorStreamer
from sentence_transformers import SentenceTransformer
import torch
import faiss
import json
from datetime import datetime
import socketio
import requests
import threading

#数据库位置
data_path = "templates/train.json"

#模型位置
model_path = 'models/Qwen3-17B'

#人设位置
re_she_path = "templates/ren_she.txt"

#RAG模型位置
rag_model_path = "models/m3e-base"

#RAG索引位置
index_path = "templates/index.faiss"

#聊天记录数据位置
ji_lu_path = "templates/ji_lu.json"

#公网服务器ip地址
serve_path = 'http://101.200.161.243:8080'

SECRET_TOKEN = "your-super-secret-token"

#加载数据库
with open(data_path, "r", encoding="utf-8") as f:
    knowledge_data = json.load(f)

#整理数据
documents = [
    f"问题：{item.get('instruction', '')}\n回答：{item.get('output', '')}"
    for item in knowledge_data
]

#加载人设数据
with open(re_she_path, "r", encoding="utf-8") as f:
    re_she = f.read()

# 导入FAISS索引
index = faiss.read_index(index_path)

# 加载模型和分词器
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

model_name = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="auto",
).to("cuda")

tokenizer = AutoTokenizer.from_pretrained(model_path)

embedding_model = SentenceTransformer(rag_model_path)


def chat_completions_model(messages, max_tokens=500, temperature=0.1):
    #加载历史聊天记录
    with open(ji_lu_path, 'r', encoding='utf-8') as file:
        ji_lu = json.load(file)
    #调整数据格式
    documents_ji_lu = [
        f"问题：{item.get('instruction', '')}\n时间：{item.get('time', '')}\n回答：{item.get('output', '')}"
        for item in ji_lu
    ]

    q = messages

    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    #在数据库中检索与问题相关的数据
    user_question = messages[-1]["content"]
    question_embedding = embedding_model.encode([user_question])
    D, I = index.search(question_embedding, k=3)
    related_docs = "\n---\n".join([documents[i] for i in I[0]])

    #在历史聊天记录中检索与问题相关的数据
    question_embedding_jl = embedding_model.encode([user_question])
    D, I = index.search(question_embedding_jl, k=3)
    related_docs_jl = "\n---\n".join([documents_ji_lu[i] for i in I[0]])

    #构建提示词
    rag_prefix = (
        "请你根据以下提供的记录与用户交流。\n"
        "记录如下，如果与用户输入不相关则不需要进行参考：\n"
        f"{related_docs}\n"
        "回答时也可以参考以下历史聊天记录，如不相关也可不参考\n"
        "聊天记录如下，其中instruction是用户的输入，time是用户输入时的时间，output是模型根据用户输入而输出的内容"
        f"{related_docs_jl}\n"
        "回答时请尽量基于上述内容，并避免编造。同时在回答时要与以下人设相符\n"
        "人设如下\n"
        f"{re_she}"
    )
    system_prompt = {
        "role": "system",
        "content": rag_prefix
    }

    full_conversation = [system_prompt] + messages

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    #模板化数据
    formatted_input = tokenizer.apply_chat_template(
        full_conversation,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    inputs = tokenizer(formatted_input, return_tensors='pt').to('cuda')

    input_tokens = inputs.input_ids.shape[1]

    #进行推理
    outputs = model_name.generate(
        inputs.input_ids,
        max_length=input_tokens + max_tokens,
        temperature=temperature,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "</think>" in response:
        response = response.split("</think>")[-1].strip()
    else:
        response = response.strip()

    return response, q


sio = socketio.Client(logger=True, engineio_logger=True)


@sio.event
def connect():
    print("✅ 成功连接到转发服务器")


@sio.event
def disconnect():
    print("⚠️ 与转发服务器断开连接")


# === 接收推理请求 ===
@sio.on("infer_request")
def handle_infer_request(data):
    print("📥 收到推理请求:", data)
    text = data.get("text", "")
    task_id = data.get("task_id")

    # 开新线程执行推理，防止阻塞 Socket.IO 心跳
    thread = threading.Thread(
        target=process_inference,
        args=(task_id, text),
        daemon=True  # 设置为守护线程
    )
    thread.start()

def save_record(new_entry):
    """将新记录保存到 ji_lu.json，保持为标准 JSON 数组"""
    path = "templates/ji_lu.json"
    data = []

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []  # 文件坏掉就重置为空数组

    data.append(new_entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def process_inference(task_id, text):
    """后台执行推理任务并回传结果"""
    try:
        # 调用你的推理函数
        ai_response, _ = chat_completions_model(messages=text, temperature=0.9)

        # 新日志条目
        new_entry = {
            "instruction": text,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "output": ai_response
        }

        # ✅ 用标准 JSON 数组方式保存
        save_record(new_entry)

        # 发送推理结果回转发服务器
        sio.emit("infer_response", {"task_id": task_id, "response": ai_response})
        print(f"任务 {task_id} 推理完成，已发送结果")

    except Exception as e:
        print(f"任务 {task_id} 推理失败: {e}")
        sio.emit("infer_response", {"task_id": task_id, "response": f"推理失败: {str(e)}"})


# === 与转发服务器建立连接 ===
sio.connect(
    serve_path,
    auth={"token": SECRET_TOKEN},   # 携带 token 认证
    wait_timeout=30,
    transports=["websocket", "polling"]  # 优先用 websocket，失败再回退到 polling
)

sio.wait()

