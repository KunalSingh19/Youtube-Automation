"""
Utility functions: error logging, tag extraction, video duration, and upscaling.
Cross-platform (Linux/Windows/macOS).
"""

import os
import re
import subprocess
from datetime import datetime  # Cross-platform timestamps
from .config import ERROR_LOG_FILE

def log_error(insta_url, error_msg):
    """
    Log error to error_log.txt with timestamp.
    
    Args:
        insta_url (str): Instagram URL for context.
        error_msg (str): Error message.
    """
    # Cross-platform timestamp (no subprocess 'date' command)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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

def upscale_video(input_path, output_path, insta_url):
    """
    Upscale video using FFmpeg (double resolution with Lanczos, H.264 re-encode).
    Cross-platform (assumes FFmpeg in PATH).
    
    Args:
        input_path (str): Path to input video file.
        output_path (str): Path to save upscaled video.
        insta_url (str): For logging errors.
    
    Returns:
        bool: True if successful, False otherwise (fallback to original).
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")
    
    # Ensure output dir exists (cross-platform)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # FFmpeg command: Double resolution (iw*2:ih*2) with Lanczos, libx264, CRF 23, ultrafast
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vf', 'scale=iw*2:ih*2:flags=lanczos',
        '-c:v', 'libx264', '-crf', '23', '-preset', 'ultrafast',
        '-y',  # Overwrite output if exists
        output_path
    ]
    
    try:
        print(f"  - Upscaling {os.path.basename(input_path)} to {os.path.basename(output_path)}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5min timeout
        if result.returncode != 0:
            error_msg = f"FFmpeg failed (code {result.returncode}): {result.stderr[:200]}"
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ValueError("Upscaled file is missing or empty")
        
        file_size = os.path.getsize(output_path)
        print(f"  - Upscale successful ({file_size} bytes)")
        return True
        
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        # FFmpeg not found or timeout
        error_msg = f"FFmpeg error: {str(e)} (install FFmpeg and retry)"
        log_error(insta_url, error_msg)
        if os.path.exists(output_path):
            os.remove(output_path)
        return False
    except Exception as e:
        error_msg = f"Upscale failed: {str(e)}"
        log_error(insta_url, error_msg)
        if os.path.exists(output_path):
            os.remove(output_path)
        return False
