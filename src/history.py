import os
import json

def load_upload_history(history_path: str):
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {}

def save_upload_history(history_path: str, history: dict):
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"Upload history saved to {history_path}")
