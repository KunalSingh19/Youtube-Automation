"""
Handles downloading remote Instagram videos to local tmp/ folder.
Cross-platform (Linux/Windows/macOS).
"""

import os
import hashlib
import requests
import time  # For retry backoff
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # For session retries
from .config import TMP_DIR

def get_unique_filename(insta_url):
    """
    Generate unique local filename based on Instagram URL.
    
    Args:
        insta_url (str): Instagram post URL.
    
    Returns:
        str: Path like tmp/reel_<hash>.mp4 (cross-platform).
    """
    # Sanitize URL to filename (use hash for uniqueness)
    url_hash = hashlib.md5(insta_url.encode()).hexdigest()[:8]
    safe_name = f"reel_{url_hash}.mp4"
    return os.path.join(TMP_DIR, safe_name)  # Handles OS-specific separators

def download_video(remote_url, local_path, insta_url):
    """
    Download video from remote URL to local path with retries and better headers.
    Cross-platform (handles paths and requests identically).
    
    Args:
        remote_url (str): Remote video URL.
        local_path (str): Local file path.
        insta_url (str): For logging.
    
    Raises:
        Exception: On download failure (e.g., HTTP error after retries).
    """
    # Enhanced headers to mimic browser (helps bypass Instagram 400 errors)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # Works on all OSes
        'Accept': 'video/webm,video/mp4,video/ogg,*/*;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': insta_url,  # Refer to the Instagram post URL
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'video',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }
    
    # Session with retries for transient errors (e.g., 400, 429, 5xx) - OS-agnostic
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # Wait 1s, 2s, 4s between retries
        status_forcelist=[400, 429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  - Download attempt {attempt + 1}/{max_retries}...")
            response = session.get(remote_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:  # Cross-platform file handling
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.getsize(local_path) == 0:
                raise ValueError("Downloaded file is empty")
            
            file_size = os.path.getsize(local_path)
            print(f"Downloaded successfully ({file_size} bytes)")
            return  # Success, exit loop
            
        except requests.RequestException as e:
            print(f"  - Download attempt {attempt + 1} failed: {str(e)[:100]}")
            if os.path.exists(local_path):
                os.remove(local_path)  # Clean up partial file
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  - Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"HTTP error after {max_retries} attempts: {e}")
        except Exception as e:
            if os.path.exists(local_path):
                os.remove(local_path)
            raise Exception(f"Download failed: {e}")