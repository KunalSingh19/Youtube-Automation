"""
Manages upload_history.json for tracking successes/failures.
"""

import json
import os
from .config import UPLOAD_HISTORY_FILE

def load_upload_history(history_file):
    """
    Load upload history from JSON file.
    
    Args:
        history_file (str): Path to history file.
    
    Returns:
        dict: History dict (empty if file missing).
    """
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load history: {e}. Starting fresh.")
    return {}

def save_upload_history(history_file, history_dict):
    """
    Save history dict to JSON file.
    
    Args:
        history_file (str): Path to history file.
        history_dict (dict): History to save.
    """
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_dict, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Warning: Could not save history: {e}")