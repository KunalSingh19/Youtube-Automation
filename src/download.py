"""
Handles downloading remote Instagram videos to local tmp/ folder.
"""

import os
import hashlib
import requests
from urllib.parse import urlparse
from .config import TMP_DIR

def get_unique_filename(insta_url):
    """
    Generate unique local filename based on Instagram URL.
    
    Args:
        insta_url (str): Instagram post URL.
    
    Returns:
        str: Path like tmp/reel_<hash>.mp4
    """
    # Sanitize URL to filename (use hash for uniqueness)
    url_hash = hashlib.md5(insta_url.encode()).hexdigest()[:8]
    safe_name = f"reel_{url_hash}.mp4"
    return os.path.join(TMP_DIR, safe_name)

def download_video(remote_url, local_path, insta_url):
    """
    Download video from remote URL to local path.
    
    Args:
        remote_url (str): Remote video URL.
        local_path (str): Local file path.
        insta_url (str): For logging.
    
    Raises:
        Exception: On download failure (e.g., HTTP error).
    """
    headers = {'User -Agent': 'Mozilla/5.0 (compatible; InstagramUploader/1.0)'}
    try:
        response = requests.get(remote_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if os.path.getsize(local_path) == 0:
            raise ValueError("Downloaded file is empty")
        print(f"Downloaded successfully ({os.path.getsize(local_path)} bytes)")
    except requests.RequestException as e:
        os.remove(local_path) if os.path.exists(local_path) else None
        raise Exception(f"HTTP error: {e}")
    except Exception as e:
        os.remove(local_path) if os.path.exists(local_path) else None
        raise Exception(f"Download failed: {e}")