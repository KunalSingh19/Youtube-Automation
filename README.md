# Youtube-Automation
A full youtube automation with advanced feature error logging and uploading video from instagram. It scrapes user liked reel from instagram and upload them to Youtube shorts


How to copy this specific branch
usage:
```
git clone https://github.com/KunalSingh19/Youtube-Automation/
cd Youtube-Automation/
rm -rf Data  LICENSE  README.md  extra  main.py  src  tmp  upload_history.json
ls
git checkout -b server origin/server
git pull
```

# Instagram Reels to YouTube Uploader

[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This Python project automates the process of downloading Instagram Reels (videos) from a JSON file (containing either remote URLs or local paths) and uploading them to YouTube. It supports multiple YouTube accounts for distributed uploads, batch processing, deduplication, error handling, and history tracking to avoid re-uploading failed or successful videos.

The script is modular, efficient for small-to-medium batches, and handles OAuth authentication for YouTube. It's designed for content creators who want to repurpose Instagram content as YouTube Shorts or videos.

## Features
- **Flexible Input**: JSON file with Instagram post data (supports remote video URLs for auto-download or pre-existing local paths).
- **Auto-Download**: Downloads remote videos only if not already present (saves to `tmp/` folder with unique filenames).
- **Multi-Account Support**: Upload to multiple YouTube channels/accounts via a credentials directory (round-robin distribution to balance load).
- **Batch Processing**: Limit uploads to a specified number (global across accounts).
- **History Tracking**: Uses `upload_history.json` to skip previously uploaded or failed videos.
- **Error Logging**: Logs issues to `error_log.txt` (e.g., download failures, API errors).
- **YouTube Integration**: Resumable uploads, quota retry logic, privacy settings, tag extraction from captions.
- **Shorts Optimization**: Detects short videos (<60s) and suggests titles/tags.
- **Modes**: `--upload-one` for incremental runs; deduplication for clean JSON.

## Requirements
- **Python**: 3.7 or higher.
- **Dependencies**:
  - `google-api-python-client` (for YouTube API)
  - `google-auth-oauthlib` (for OAuth)
  - `google-auth` (transport)
  - `requests` (for downloading videos)
  - `ffmpeg` (system install required for video duration checks via `ffprobe`; optional but recommended).
- **System Tools**: `ffprobe` (from FFmpeg) for video duration. Install via:
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: Download from [FFmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

Install Python dependencies:
```bash
pip install google-api-python-client google-auth-oauthlib google-auth requests
```

## Installation and Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/instagram-to-youtube-uploader.git
cd instagram-to-youtube-uploader
```

### 2. Google Cloud Setup for YouTube API
For each YouTube account/channel:
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or use existing).
3. Enable the **YouTube Data API v3**.
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Desktop application**.
   - Download the `client_secrets.json` file.
5. Add the scope: `https://www.googleapis.com/auth/youtube.upload` (for uploads).
6. **Important**: Each account needs its own Google Cloud project/credentials if you want separate quotas. For multi-account, create one per channel.

### 3. Directory Structure
Organize your files as follows:
```
project-root/
├── main.py                  # Main script
├── src/                     # Source modules
│   ├── __init__.py
│   ├── download.py          # Download logic
│   ├── upload.py            # YouTube upload
│   ├── utils.py             # Utilities (logging, tags, duration)
│   └── history.py           # History management
├── Data/                    # Input data
│   └── reelsData.json       # Instagram JSON (see format below)
├── creds/                   # Multi-account credentials (default)
│   ├── account1/            # Subfolder per account
│   │   ├── client_secrets.json  # From Google Cloud
│   │   └── token.json       # Generated on first run (OAuth token)
│   └── account2/
│       ├── client_secrets.json
│       └── token.json
├── tmp/                     # Auto-created: Downloaded videos
├── upload_history.json      # Auto-generated: Tracks uploads/failures
└── error_log.txt            # Auto-generated: Error logs
```

- **creds/**: Default path (change with `--creds-dir`). Each subfolder is an account. `token.json` is created automatically on first authentication (browser opens for OAuth consent).
- **tmp/**: Auto-created for remote downloads. Files are named based on Instagram URL (sanitized + hash if duplicate).

### 4. Input JSON Format (`Data/reelsData.json`)
The JSON is a dictionary where keys are Instagram post URLs, and values are post data. Example:
```json
{
  "https://www.instagram.com/reel/ABC123/": {
    "media_details": [
      {
        "url": "https://scontent.cdninstagram.com/video.mp4"  // Remote URL (auto-download) OR local path (e.g., "./videos/reel1.mp4")
      }
    ],
    "post_info": {
      "caption": "Cool reel! #shorts #instagram"
    }
  },
  "https://www.instagram.com/reel/DEF456/": {
    "media_details": [
      {
        "url": "./local_videos/reel2.mp4"  // Local path (used directly if exists)
      }
    ],
    "post_info": {
      "caption": "Another video #tags"
    }
  }
}
```
- **media_details[0].url**: Either remote (http/https) for download or local path (relative/absolute).
- **post_info.caption**: Used for title (truncated to 100 chars), description, and tag extraction (#hashtags).
- Generate this JSON via an Instagram scraper (not included—use tools like Instaloader or custom script).

## Usage

Run the script with Python:
```bash
python main.py [arguments]
```

### CLI Arguments
- `--creds-dir <path>`: Directory with account subfolders (default: `./creds`).
- `--accounts <comma-separated>`: Specific accounts (e.g., `account1,account2`). Skips others.
- `--all-accounts`: Use all valid subfolders in `--creds-dir` (mutually exclusive with `--accounts`).
- `--privacy-status <status>`: Video privacy (default: `private`; options: `public`, `private`, `unlisted`).
- `--batch-size <int>`: Max new videos to process (default: 5). Global limit across accounts (round-robin distribution).
- `--upload-one`: Process exactly one new video (to first account) and stop.

If no `--accounts` or `--all-accounts`, uses the first valid subfolder (single-account mode).

### Examples
1. **Single Account Upload (Batch of 5)**:
   ```bash
   python main.py --creds-dir ./creds --batch-size 5 --privacy-status unlisted
   ```
   - Uses first account (e.g., `creds/account1/`).
   - Attempts up to 5 new videos.

2. **Multi-Account (Specific Accounts, Batch 10)**:
   ```bash
   python main.py --creds-dir ./creds --accounts account1,account2 --batch-size 10
   ```
   - Distributes 10 videos: ~5 per account (round-robin).
   - If 2 accounts: account1 gets videos 1,3,5,7,9; account2 gets 2,4,6,8,10.

3. **All Accounts (Batch 6)**:
   ```bash
   python main.py --creds-dir ./creds --all-accounts --batch-size 6 --privacy-status public
   ```
   - Uses all subfolders with `client_secrets.json`.
   - Distributes across all (e.g., 3 accounts: ~2 per account).

4. **Upload One Video**:
   ```bash
   python main.py --creds-dir ./creds --accounts account1 --upload-one
   ```
   - Uploads exactly one new video to `account1` and stops.

5. **First Run (OAuth)**:
   - On first use per account, a browser opens for Google login/consent. Approve YouTube upload access.
   - `token.json` is saved in the account subfolder for future runs.

### Output
- Console: Progress (downloads, uploads, skips), account assignments.
- Files:
  - `upload_history.json`: Tracks status (`"success"`/`"failed"`), YouTube ID, and account.
  - `error_log.txt`: Timestamped errors (e.g., "Download failed: HTTP 404").
  - `tmp/*.mp4`: Downloaded videos (not deleted after upload—manual cleanup).

## Batch Size and Distribution
- `--batch-size N` limits **total attempts** (new videos processed) across all accounts.
- Videos are assigned round-robin: Video 1 → account1, Video 2 → account2, etc.
- Example with `--batch-size 5` and 2 accounts (all succeed):
  - Total: 5 uploads.
  - account1: 3 videos.
  - account2: 2 videos.
- Failures/skips don't count toward the limit—the script continues until N attempts or no more new videos.
- For even per-account distribution, run separate commands per account.

## File Structure After Run
- `tmp/`: Downloaded MP4s (unique names like `reel_ABC123.mp4`).
- `upload_history.json`: Example entry:
  ```json
  {
    "https://www.instagram.com/reel/ABC123/": {
      "status": "success",
      "youtube_video_id": "abcDEF123",
      "account": "account1"
    }
  }
  ```
- Videos on YouTube: Titles from captions (or fallback `#Shorts...`), descriptions with full caption, tags from hashtags.

## Troubleshooting
- **OAuth Browser Not Opening**: Ensure `port=0` in code; check firewall. Delete `token.json` to re-authenticate.
- **Quota Exceeded**: YouTube API has daily limits (10,000 units/project). Script retries 3x with 60s delay. Distribute across accounts/projects.
- **Download Fails**: Check Instagram URL validity (direct MP4 links). Network issues? Increase timeout in `download.py`.
- **ffprobe Not Found**: Install FFmpeg. Duration check skips otherwise (no impact on upload).
- **JSON Errors**: Ensure `media_details[0].url` and `post_info.caption` exist. Script skips invalid entries.
- **No New Videos**: All processed? Check `upload_history.json`. Empty JSON? Regenerate.
- **Multi-Account Issues**: Verify subfolders have `client_secrets.json`. Invalid accounts are skipped.
- **Permissions**: YouTube channel must allow uploads (verify in YouTube Studio).
- **Logs**: Always check `error_log.txt` for details.

## Contributing
Fork the repo, make changes, and submit a PR. Issues welcome!

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. (Add your own if needed.)

## Disclaimer
- Respect Instagram/YouTube terms: Don't violate copyrights or spam.
- API usage: Follow Google's quotas and policies.
- Not affiliated with Instagram or YouTube.

For support, open an issue on GitHub!
