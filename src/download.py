import os
import re
import urllib.parse
import hashlib
import requests
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
    """
    Download video from remote URL to filename (only called for http/https URLs).
    """
    if not url.startswith(('http://', 'https://')):
        raise ValueError("download_video called with non-remote URL")
    
    print(f"Downloading video from {url} ...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"Download progress: {progress:.1f}%", end='\r')

        if total_size > 0 and downloaded_size < total_size:
            raise Exception(f"Incomplete download: {downloaded_size}/{total_size} bytes")

        file_size = os.path.getsize(filename)
        if file_size == 0:
            raise Exception("Downloaded file is empty")

        print(f"\nVideo downloaded successfully to {filename} ({file_size} bytes)")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network/HTTP error: {e}")
    except Exception as e:
        # Clean up empty/incomplete file
        if os.path.exists(filename) and os.path.getsize(filename) == 0:
            os.remove(filename)
        log_error(insta_url, f"Download error: {e}")
        raise