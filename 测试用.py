import os
import json

history_folder = "history" # 聊天记录存储的文件夹


def get_history():
    try:
        # 获取历史聊天记录的文件列表
        files = os.listdir(history_folder)
        files.sort(reverse=True)  # 按文件名降序排列（最新的文件排前面）

        # 获取最新一个文件
        latest_file = files[0] if files else None
        if latest_file:
            file_path = os.path.join(history_folder, latest_file)
            with open(file_path, "r", encoding="utf-8") as f:
                chat_history = json.load(f)
            return print({"history": chat_history})
        else:
            return print({"error": "没有找到聊天记录"}), 404
    except Exception as e:
        return print({"error": f"读取聊天记录时出错: {str(e)}"}), 500

if __name__ == '__main__':
    get_history()