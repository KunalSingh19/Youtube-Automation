"""
Download utilities for Instagram videos.
"""

import os
import re
import hashlib
from urllib.parse import urlparse
import requests  # pip install requests
from .config import TMP_DIR

def get_unique_filename(insta_url):
    """
    Generate unique filename for download based on Instagram URL.
    
    Args:
        insta_url (str): Instagram reel URL.
    
    Returns:
        str: Path like 'tmp/reel_<hash>.mp4'.
    """
    # Ensure tmp dir exists (redundant but safe)
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # Hash URL for uniqueness (shortened)
    url_hash = hashlib.md5(insta_url.encode()).hexdigest()[:8]
    # Clean filename from URL (e.g., extract reel ID)
    reel_id = re.search(r'/reel/([A-Za-z0-9_-]+)', insta_url)
    if reel_id:
        base_name = f"reel_{reel_id.group(1)}"
    else:
        base_name = f"reel_{url_hash}"
    return os.path.join(TMP_DIR, f"{base_name}.mp4")

def download_video(video_url, local_filename, insta_url):
    """
    Download video from URL to local file with retries.
    
    Args:
        video_url (str): Direct video URL from Instagram JSON.
        local_filename (str): Local path to save.
        insta_url (str): For logging/errors.
    
    Raises:
        Exception: On download failure.
    """
    # Ensure dir exists
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  - Download attempt {attempt + 1}/{max_retries}...")
            response = requests.get(video_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(local_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(local_filename)
            if file_size > 0:
                print(f"Downloaded successfully ({file_size} bytes)")
                return
            else:
                raise ValueError("Downloaded file is empty")
        except Exception as e:
            print(f"  - Download attempt {attempt + 1} failed: {str(e)[:50]}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise Exception(f"Download failed after {max_retries} attempts: {e}")