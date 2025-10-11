"""
Upload history management: Load/save JSON to track successes/failures.
Prevents re-uploading the same Instagram URLs.
"""

import json
import os
from .config import UPLOAD_HISTORY_FILE

def load_upload_history(history_file):
    """
    Load upload history from JSON file.
    
    Args:
        history_file (str): Path to history JSON.
    
    Returns:
        dict: {insta_url: {"status": "success/failed", "youtube_video_id": str (if success), "account": str, "reason": str (if failed)}}
    """
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Invalid history file '{history_file}': {e}. Starting fresh.")
            return {}
    else:
        print(f"No history file found at '{history_file}'. Starting fresh.")
        return {}

def save_upload_history(history_file, history_dict):
    """
    Save upload history to JSON file (with backup on write error).
    
    Args:
        history_file (str): Path to history JSON.
        history_dict (dict): History data to save.
    
    Returns:
        bool: True if saved successfully.
    """
    try:
        # Backup existing if present
        if os.path.exists(history_file):
            backup_file = history_file + '.backup'
            os.replace(history_file, backup_file)
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_dict, f, indent=2, ensure_ascii=False)
        
        # Verify save
        if os.path.exists(history_file) and os.path.getsize(history_file) > 0:
            print(f"History saved: {len(history_dict)} entries")
            return True
        else:
            raise IOError("Saved file is empty or missing")
    except Exception as e:
        print(f"Warning: Could not save history: {e}")
        # Restore backup if exists
        backup_file = history_file + '.backup'
        if os.path.exists(backup_file):
            os.replace(backup_file, history_file)
            print("Restored from backup.")
        return False