"""
不能直接使用一整个文档进行
"""
import json
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime, timedelta
''''# 打开训练数据并读取
with open("templates/聊天记录1.json", "r", encoding="utf-8") as f:
    documents = json.load(f)
for i in range(len(documents)):
    documents[i] = str(documents[i])
# 加载m3e-base模型
embedding_model = SentenceTransformer("models/m3e-base")

# 将数据通过m3e-base模型转为高维向量
doc_embeddings = embedding_model.encode(documents, show_progress_bar=True)
print(doc_embeddings.shape)
# 获取转换后高维向量的维数
dimension = doc_embeddings.shape[1]

# 创建faiss索引
index = faiss.IndexFlatL2(dimension)
# 将数据添加至faiss索引中
index.add(doc_embeddings)
a = embedding_model.encode(["你还记得那天和你聊天的后期干员叫什么名字吗"])
D, I = index.search(a, k=1)
'''

# 打开训练数据并读取
with open("templates/聊天记录1.json", "r", encoding="utf-8") as f:
    documents = json.load(f)

# 提取每条对话的时间戳，并将其转换为字符串类型
for i in range(len(documents)):
    documents[i]["时间"] = str(documents[i]["时间"])

# 加载m3e-base模型
embedding_model = SentenceTransformer("models/m3e-base")

# 将数据通过m3e-base模型转为高维向量
doc_embeddings = embedding_model.encode([str(doc) for doc in documents], show_progress_bar=True)

# 获取转换后高维向量的维数
dimension = doc_embeddings.shape[1]

# 创建faiss索引
index = faiss.IndexFlatL2(dimension)

# 将数据添加至faiss索引中
index.add(doc_embeddings)

# 假设要查询的句子是
query_sentence = "你还记得那天和你聊天的后期干员叫什么名字吗"

# 对查询句子进行编码
query_embedding = embedding_model.encode([query_sentence])

# 查找最接近的句子
D, I = index.search(query_embedding, k=1)

# 获取找到的句子的索引
a = I[0][0]
query_time = documents[a]["时间"]

# 将字符串时间转换为datetime对象
query_time_dt = datetime.strptime(query_time, "%Y-%m-%d %H:%M:%S")

# 计算前后15分钟的时间范围
start_time = query_time_dt - timedelta(minutes=15)
end_time = query_time_dt + timedelta(minutes=15)

# 筛选出在时间范围内的对话
relevant_dialogues = []
for doc in documents:
    doc_time_dt = datetime.strptime(doc["时间"], "%Y-%m-%d %H:%M:%S")
    if start_time <= doc_time_dt <= end_time:
        relevant_dialogues.append(doc)
print(relevant_dialogues[0])

