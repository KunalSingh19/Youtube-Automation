import re
import datetime
import subprocess

ERROR_LOG_FILE = "error_log.txt"

def log_error(insta_url: str, error_message: str):
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] URL: {insta_url}\nError: {error_message}\n\n"
    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def extract_tags_from_caption(caption: str):
    tags = re.findall(r'#(\w+)', caption)
    unique_tags = list(dict.fromkeys(tags))
    return unique_tags[:30]

def get_video_duration(filename: str) -> float:
    """Get video duration using ffprobe (requires FFmpeg installed)."""
    try:
        # Check if ffprobe is available
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: ffprobe not found (install FFmpeg). Skipping duration check.")
        return -1
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=duration', '-of',
             'default=noprint_wrappers=1:nokey=1', filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True
        )
        duration_str = result.stdout.decode().strip()
        return float(duration_str)
    except Exception as e:
        print(f"Warning: Could not determine video duration: {e}")
        return -1