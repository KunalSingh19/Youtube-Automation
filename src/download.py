import os
import re
import urllib.parse
import hashlib
import requests
import subprocess
from .utils import log_error

TMP_FOLDER = "tmp"

def sanitize_filename(name: str, max_length=100) -> str:
    parsed = urllib.parse.urlparse(name)
    path = parsed.path + ("_" + parsed.query if parsed.query else "")
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', path)
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length]
    if not safe_name.lower().endswith('.mp4'):
        safe_name += '.mp4'
    return safe_name

def get_unique_filename(insta_url: str) -> str:
    if not os.path.exists(TMP_FOLDER):
        os.makedirs(TMP_FOLDER)
    base_name = sanitize_filename(insta_url)
    full_path = os.path.join(TMP_FOLDER, base_name)
    if os.path.exists(full_path):
        hash_suffix = hashlib.md5(insta_url.encode('utf-8')).hexdigest()[:6]
        name, ext = os.path.splitext(base_name)
        full_path = os.path.join(TMP_FOLDER, f"{name}_{hash_suffix}{ext}")
    return full_path

def download_video(url: str, filename: str, insta_url: str):
    print(f"Downloading video from {url} ...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Status code {response.status_code}")
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Video downloaded to {filename}")
    except Exception as e:
        log_error(insta_url, f"Download error: {e}")
        raise

def get_video_duration(filename: str) -> float:
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
