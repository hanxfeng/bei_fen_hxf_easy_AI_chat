"""
用于创建并储存faiss索引，主要目的是通过提前保存好的索引文件，减少发送信息后的等待时间
主要思路是首先使用文本嵌入模型m3e-base将文本转为高维
可以尝试仅搜索问句的数据，然后提取数据时提取包括答句和时间在内的所有数据传递给模型
"""

import json
import faiss
from sentence_transformers import SentenceTransformer

# 打开训练数据并读取
with open("templates/train.json", "r", encoding="utf-8") as f:
    knowledge_data = json.load(f)

# 加载m3e-base模型
embedding_model = SentenceTransformer("models/m3e-base")

# 将数据处理为问题 \n 回答的形式
#加入时间，解决聊天历史数据每次发送新信息后都需要从新将数据转为高维向量然后再加入索引的问题
#后面的问题或许可以用当前的聊天暂时不保存，作为一轮数据存在，之前的聊天作为索引检索
documents = []
for item in knowledge_data:
    instruction = item.get("instruction", "")
    output = item.get("output", "")
    doc = f"问题：{instruction}\n回答：{output}"
    documents.append(doc)

# 将数据通过m3e-base模型转为高维向量
doc_embeddings = embedding_model.encode(documents, show_progress_bar=True)

# 获取转换后高维向量的维数
dimension = doc_embeddings.shape[1]

# 创建faiss索引
index = faiss.IndexFlatL2(dimension)
# 将数据添加至faiss索引中
index.add(doc_embeddings)
# 保存索引
faiss.write_index(index, "templates/index.faiss")