import os
import json

history_folder = "history" # 聊天记录存储的文件夹


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

    return [all_history[key] for key in sorted(all_history.keys())]

if __name__ == '__main__':
    print(get_history())