"""
Utility functions: error logging, tag extraction, video duration.
"""

import os
import re
import subprocess
from .config import ERROR_LOG_FILE

def log_error(insta_url, error_msg):
    """
    Log error to error_log.txt with timestamp.
    
    Args:
        insta_url (str): Instagram URL for context.
        error_msg (str): Error message.
    """
    timestamp = subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], capture_output=True, text=True).stdout.strip()
    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {insta_url}: {error_msg}\n")
    print(f"Logged error: {error_msg}")

def extract_tags_from_caption(caption):
    """
    Extract hashtags from caption as list.
    
    Args:
        caption (str): Post caption.
    
    Returns:
        list: List of tags (e.g., ['#shorts', '#test']).
    """
    hashtags = re.findall(r'#\w+', caption)
    return [tag.lower() for tag in hashtags]

def get_video_duration(video_path):
    """
    Get video duration in seconds using ffprobe (FFmpeg).
    
    Args:
        video_path (str): Path to video file.
    
    Returns:
        float: Duration in seconds, or -1 if error/unavailable.
    """
    if not os.path.exists(video_path):
        return -1
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass  # ffprobe not found or error
    return -1