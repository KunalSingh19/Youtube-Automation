import time
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from .utils import log_error

class BatchLimitReached(Exception):
    """Raised when batch upload limit is reached."""
    pass

class QuotaExceededError(Exception):
    """Raised when YouTube API quota is exceeded."""
    pass

def get_authenticated_service(client_secrets_file: str):
    import os
    import google_auth_oauthlib.flow
    import googleapiclient.discovery
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"
    TOKEN_FILE = "token.json"

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=creds)

def initialize_upload(youtube, options, insta_url, uploaded_count=None, batch_size=None, max_retries=3, retry_delay=60):
    body = {
        "snippet": {
            "title": options.title,
            "description": options.description,
            "tags": options.tags if options.tags else None,
            # categoryId removed
        },
        "status": {
            "privacyStatus": options.privacy_status
        }
    }
    # Remove None values from snippet
    body["snippet"] = {k: v for k, v in body["snippet"].items() if v is not None}
    media = MediaFileUpload(options.file, chunksize=-1, resumable=True)

    tries = 0
    while tries < max_retries:
        try:
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"Upload progress: {int(status.progress() * 100)}%")
            print(f"Upload Complete! Video ID: {response['id']}")

            # Batch limit check
            if uploaded_count is not None and batch_size is not None:
                if uploaded_count + 1 >= batch_size:
                    print(f"Batch limit of {batch_size} reached during upload.")
                    raise BatchLimitReached()

            return response['id']

        except googleapiclient.errors.HttpError as e:
            error_content = e.content.decode() if isinstance(e.content, bytes) else str(e.content)
            if 'quotaExceeded' in error_content:
                tries += 1
                print(f"Quota exceeded error detected. Retry {tries}/{max_retries} after {retry_delay} seconds.")
                if tries >= max_retries:
                    print("Max retries reached due to quotaExceeded. Stopping uploads.")
                    raise QuotaExceededError()
                time.sleep(retry_delay)
                continue  # retry
            else:
                log_error(insta_url, f"HTTP error {e.resp.status}: {error_content}")
                raise
        except BatchLimitReached:
            raise
        except QuotaExceededError:
            raise
        except Exception as e:
            log_error(insta_url, f"Unexpected upload error: {e}")
            raise