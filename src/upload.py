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

# Custom exceptions
class QuotaExceededError(Exception):
    pass

class FileError(Exception):
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
                os.chmod(token_file, 0o600)  # Restrictive permissions
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
    
    # Ensure #Shorts is in tags for Shorts eligibility
    if 'shorts' not in [tag.lower() for tag in options.tags]:
        options.tags.append('#Shorts')
    
    body = dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=options.tags,
            categoryId="22"  # People & Blogs (default for shorts/reels)
        ),
        status=dict(
            privacyStatus=options.privacy_status or DEFAULT_PRIVACY_STATUS,
            selfDeclaredMadeForKids=False
        )
    )
    
    # Insert request (resumable upload initiation)
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(
            options.file,
            chunksize=-1,  # Full file upload (adjust for large files if needed)
            resumable=True
        )
    )
    
    # Execute upload with retries (exponential backoff)
    max_retries = 3
    retry_delay = 1  # seconds
    for attempt in range(max_retries):
        try:
            print(f"  - Uploading... (attempt {attempt + 1}/{max_retries})")
            response = insert_request.execute()
            video_id = response.get('id')
            if not video_id:
                raise ValueError("No video ID in response")
            print(f"  - Upload completed! Video ID: {video_id}")
            return video_id
        except HttpError as err:
            error_reason = err.resp.status if hasattr(err, 'resp') else str(err)
            if error_reason == 403 and "quotaExceeded" in err._get_reason():
                print(f"  - Quota exceeded (HTTP 403). Stopping.")
                raise QuotaExceededError(f"Quota exceeded during upload: {err}")
            elif error_reason == 500 or error_reason == 503:
                # Server error: Retry
                if attempt < max_retries - 1:
                    print(f"  - Server error (HTTP {error_reason}). Retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise  # No more retries
            else:
                # Other errors: Fail
                print(f"  - Upload failed (HTTP {error_reason}): {err}")
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  - Unexpected error: {e}. Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            else:
                print(f"  - Upload failed after {max_retries} attempts: {e}")
                raise

def get_account_services(accounts_dir, client_secrets_file, target_accounts=None):
    """
    Load YouTube accounts from directory (one client_secrets per account).
    If target_accounts provided (e.g., ['ken']), only load those (no scanning others).
    Accounts are subdirs directly under accounts_dir (e.g., ./creds/ken/client_secrets.json).
    
    Args:
        accounts_dir (str): Directory with account subdirs (e.g., './creds').
        client_secrets_file (str): Fallback single client_secrets path (if no accounts_dir).
        target_accounts (list): Specific account names to load (e.g., ['ken']); if None, load all.
    
    Returns:
        dict: {account_name: youtube_service}
    
    Raises:
        ValueError: If no valid accounts.
    """
    account_services = {}
    if os.path.exists(accounts_dir) and os.path.isdir(accounts_dir):
        if target_accounts:
            # Single-account mode: Only load specified accounts (no full scan)
            print(f"Loading specified account(s): {', '.join(target_accounts)} from '{accounts_dir}'...")
            for acc_name in target_accounts:
                acc_path = os.path.join(accounts_dir, acc_name)
                if not os.path.isdir(acc_path):
                    print(f"  - Warning: Account dir '{acc_path}' not found")
                    continue
                secrets_path = os.path.join(acc_path, 'client_secrets.json')
                token_path = os.path.join(acc_path, 'token.json')
                if os.path.exists(secrets_path):
                    try:
                        youtube = get_authenticated_service(secrets_path, token_path)
                        account_services[acc_name] = youtube
                        print(f"  - Loaded account '{acc_name}'")
                    except Exception as e:
                        print(f"  - Failed to load account '{acc_name}': {e}")
                else:
                    print(f"  - Skipping '{acc_name}': No client_secrets.json in {acc_path}")
        else:
            # Multi-account mode: Load all valid subdirs
            print(f"Loading all accounts from '{accounts_dir}' (direct subdirs)...")
            for acc_name in sorted(os.listdir(accounts_dir)):
                acc_path = os.path.join(accounts_dir, acc_name)
                if not os.path.isdir(acc_path):
                    continue
                secrets_path = os.path.join(acc_path, 'client_secrets.json')
                token_path = os.path.join(acc_path, 'token.json')
                if os.path.exists(secrets_path):
                    try:
                        youtube = get_authenticated_service(secrets_path, token_path)
                        account_services[acc_name] = youtube
                        print(f"  - Loaded account '{acc_name}'")
                    except Exception as e:
                        print(f"  - Failed to load account '{acc_name}': {e}")
                else:
                    print(f"  - Skipping '{acc_name}': No client_secrets.json")
    else:
        # Fallback to single account
        print(f"No accounts dir found. Using single account with '{client_secrets_file}'...")
        token_file = 'token.json'  # Single token in root
        try:
            youtube = get_authenticated_service(client_secrets_file, token_file)
            account_services['default'] = youtube
            print("  - Loaded single 'default' account")
        except Exception as e:
            raise ValueError(f"Failed to load single account: {e}")
    
    if not account_services:
        raise ValueError("No valid YouTube accounts loaded!")
    
    num_accounts = len(account_services)
    print(f"Total active accounts: {num_accounts}")
    return account_services, num_accounts