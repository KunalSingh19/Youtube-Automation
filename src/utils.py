"""
Utility functions: Video duration, tag extraction, error logging, FFmpeg helpers.
"""

import os
import re
import subprocess
from datetime import datetime  # For cross-platform timestamp
from .config import ERROR_LOG_FILE

def get_video_duration(video_path):
    """
    Get video duration in seconds using ffprobe (requires ffmpeg).
    
    Args:
        video_path (str): Path to video file.
    
    Returns:
        float: Duration in seconds, or -1 on error.
    """
    if not os.path.exists(video_path):
        return -1
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return -1

def extract_tags_from_caption(caption):
    """
    Extract hashtags from caption as list of strings.
    
    Args:
        caption (str): Instagram caption text.
    
    Returns:
        list: List of tags (e.g., ['#tag1', '#tag2']).
    """
    hashtags = re.findall(r'#\w+', caption)
    return list(set(hashtags))  # Dedupe

def log_error(insta_url, error_msg):
    """
    Log error to errors.log with timestamp (cross-platform).
    
    Args:
        insta_url (str): Instagram URL for reference.
        error_msg (str): Error message.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Python datetime (Windows-friendly)
    log_entry = f"[{timestamp}] {insta_url}: {error_msg}\n"
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:  # Use imported constant
            f.write(log_entry)
    except IOError as e:
        print(f"Warning: Could not write to {ERROR_LOG_FILE}: {e}")

def has_ffmpeg():
    """
    Check if FFmpeg is available in PATH.
    
    Returns:
        bool: True if ffmpeg command exists.
    """
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_video_width(video_path):
    """
    Get video width in pixels using ffprobe.
    
    Args:
        video_path (str): Path to video file.
    
    Returns:
        int: Width, or 0 on error.
    """
    if not os.path.exists(video_path):
        return 0
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
            '-show_entries', 'stream=width', '-of', 'csv=p=0', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        width = int(result.stdout.strip())
        return width
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0

def upscale_video(input_path, output_path):
    """
    Upscale video 2x using FFmpeg (Lanczos, H.264 CRF 23, ultrafast).
    
    Args:
        input_path (str): Input MP4 file.
        output_path (str): Output MP4 file.
    
    Returns:
        bool: True if successful.
    """
    if not has_ffmpeg():
        return False
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', 'scale=iw*2:ih*2:flags=lanczos',  # 2x upscale with Lanczos
        '-c:v', 'libx264', '-crf', '23', '-preset', 'ultrafast',  # Encoding settings
        '-y',  # Overwrite output
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        print(f"  - FFmpeg error: {e.stderr[:100]}")
        return False