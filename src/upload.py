"""
YouTube API integration: Authentication and video upload.
"""

import os
import io
import googleapiclient.discovery
import googleapiclient.errors
import google_auth_oauthlib.flow
import google.auth.transport.requests
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from .config import DEFAULT_PRIVACY_STATUS

# Custom exception for quota issues
class QuotaExceededError(Exception):
    pass

# YouTube API constants
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service(client_secrets_file, token_file):
    """
    Authenticate and return YouTube API service (Termux-friendly).
    
    Args:
        client_secrets_file (str): Path to client_secrets.json.
        token_file (str): Path to save/load token.json.
    
    Returns:
        googleapiclient.discovery.Resource: YouTube service.
    
    Raises:
        Exception: On auth failure.
    """
    # Load client secrets
    if not os.path.exists(client_secrets_file):
        raise FileNotFoundError(f"Missing {client_secrets_file}")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, SCOPES)
    credentials = None
    
    # Load existing token if available
    if os.path.exists(token_file):
        try:
            print(f"Loading existing token from {token_file}...")
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
                token_file, SCOPES)
            if credentials and credentials.valid:
                print("Valid token loaded successfully.")
                return googleapiclient.discovery.build(
                    YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
            else:
                print("Token invalid or expired. Re-authenticating...")
                os.remove(token_file)  # Remove invalid token
        except Exception as e:
            print(f"Error loading token: {e}. Re-authenticating...")
    
    # If no valid credentials, run OAuth flow
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired token...")
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            # Try local server first (with manual handling for Termux)
            try:
                print("Starting local OAuth server... (This may take a moment)")
                print("If it hangs, copy the URL below and open in a browser.")
                credentials = flow.run_local_server(
                    port=0,  # Auto-select port
                    open_browser=False,  # Don't auto-open in Termux
                    authorization_prompt_message="Please visit this URL in your browser to authorize: ",
                    success_message="Authorization successful! Token saved."
                )
                print(f"Local server auth completed. Saving token to {token_file}...")
            except Exception as server_error:
                print(f"Local server failed ({server_error}). Falling back to manual redirect method.")
                # Manual redirect fallback for Termux/headless
                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true'
                )
                print(f"\n=== MANUAL AUTHORIZATION INSTRUCTIONS ===")
                print(f"1. Open this URL in a web browser (e.g., Chrome on your phone):")
                print(f"   {auth_url}")
                print(f"2. Sign in with your Google account and authorize the app.")
                print(f"3. After authorization, you'll be redirected to a URL like:")
                print(f"   http://localhost:PORT/?code=ABC123&scope=... (or an error page)")
                print(f"4. Copy the FULL redirect URL from the browser address bar.")
                print(f"5. Paste it here in Termux (press Enter after pasting):")
                
                redirect_response = input("Paste the full redirect URL: ").strip()
                
                # Fetch token from manual redirect
                flow.fetch_token(authorization_response=redirect_response)
                credentials = flow.credentials
                print("Manual auth completed!")
        
        # Save token for future runs (with retry on write error)
        max_save_retries = 3
        for attempt in range(max_save_retries):
            try:
                print(f"Saving token to {token_file} (attempt {attempt + 1})...")
                with open(token_file, 'w', encoding='utf-8') as token:
                    token.write(credentials.to_json())
                print(f"Token saved successfully to {token_file}!")
                # Verify save
                if os.path.exists(token_file) and os.path.getsize(token_file) > 0:
                    print("Token file verified (non-empty).")
                break
            except IOError as save_error:
                print(f"Save failed (attempt {attempt + 1}): {save_error}")
                if attempt < max_save_retries - 1:
                    print("Retrying... Check directory permissions.")
                else:
                    print(f"Failed to save token after {max_save_retries} attempts.")
                    print("You may need to re-auth next run. Continuing with current session...")
                    # Continue anyway (token in memory)
    
    return googleapiclient.discovery.build(
        YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)

def initialize_upload(youtube, options, insta_url):
    """
    Upload video to YouTube (resumable, with retries).
    
    Args:
        youtube: Authenticated YouTube service.
        options: Object with file, title, description, privacy_status, tags.
        insta_url: For logging.
    
    Returns:
        str: YouTube video ID.
    
    Raises:
        QuotaExceededError: On quota exceed.
        Exception: On other upload errors.
    """
    if not os.path.exists(options.file):
        raise FileError(f"Video file not found: {options.file}")
    
    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=options.tags,
            categoryId="22"  # People & Blogs (default for shorts/reels)
        ),
        status=dict(
            privacyStatus=options.privacy_status,
            selfDeclaredMadeForKids=False
        )
    )
    
    # Insert request (resumable)
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )
    
    # Retry logic for quota/transient errors
    max_retries = 3
    tries = 0
    while tries < max_retries:
        try:
            response = insert_request.execute()
            video_id = response['id']
            print(f"Upload complete: https://youtu.be/{video_id}")
            return video_id
        except HttpError as e:
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                raise QuotaExceededError("YouTube API quota exceeded")
            elif e.resp.status >= 500:
                tries += 1
                if tries < max_retries:
                    print(f"Retry {tries}/{max_retries} after error {e.resp.status}")
                    import time
                    time.sleep(60 * tries)  # Exponential backoff
                else:
                    raise Exception(f"Upload failed after {max_retries} retries: {e}")
            else:
                raise Exception(f"Upload error {e.resp.status}: {e}")
        except Exception as e:
            raise Exception(f"Unexpected upload error: {e}")
    
    raise Exception("Upload failed (max retries exceeded)")

class FileError(Exception):
    pass
    