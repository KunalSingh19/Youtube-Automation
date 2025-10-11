# Youtube-Automation
A full youtube automation with advanced feature error logging and uploading video from instagram. It scrapes user liked reel from instagram and upload them to Youtube shorts


How to copy this specific branch
usage:
```
git clone https://github.com/KunalSingh19/Youtube-Automation/
cd Youtube-Automation/
git checkout -b server origin/server
git pull
```

checkout automation: https://github.com/kanekikun07/automation/blob/main/.github/workflows/blank.yml

# YouTube Shorts Automation from Instagram Reels

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This Python script automates uploading Instagram Reels (videos) to YouTube as **Shorts-only** content. It:
- Downloads videos from Instagram JSON data.
- Filters for Shorts-eligible videos (≤60 seconds, vertical format).
- Optionally upscales low-resolution videos (e.g., 540p to 1080p) using FFmpeg for better quality.
- Uploads to one or multiple YouTube accounts with cleaned titles (adds `#Shorts`), tags, and privacy settings.
- Tracks history to avoid re-uploads and logs errors.
- Supports round-robin distribution across accounts or "one per account" mode.

**Why Use This?**  
Save time posting Reels to YouTube Shorts. Ideal for content creators with multiple channels. Beginner-friendly with step-by-step setup—no coding required beyond running commands.

**Cross-Platform**: Works on **Windows**, **Linux**, **macOS**, and **Termux (Android)**.

**Limitations**:  
- YouTube daily quota (~10-50 uploads/account; stops on exceed).  
- Requires Instagram JSON (generate via scraper like Instaloader or browser extension).  
- Videos must be vertical (9:16) for best Shorts results (script assumes this from Reels).

## Features
- **Shorts Optimization**: Auto-skips >60s videos; adds `#Shorts` to title/tags; uses category "People & Blogs".
- **Multi-Account Support**: Upload to one or many YouTube channels (e.g., 'ken', 'itzken').
- **One-Per-Account Mode**: Limit to 1 upload per account (great for testing).
- **Upscaling**: Optional 2x resolution boost (e.g., 540x960 → 1080x1920) with FFmpeg (Lanczos filter, H.264 encoding).
- **Error Handling**: Skips failures, logs to `errors.log`, cleans up temp files.
- **History Tracking**: JSON-based (`upload_history.json`) to skip uploaded videos.
- **Privacy Options**: Public, private, or unlisted.
- **Cross-Platform Paths**: Handles Windows `\` and Unix `/` seamlessly.

## Prerequisites (Beginner Setup)

### 1. Install Python
- Download Python 3.8+ from [python.org](https://www.python.org/downloads/).
- **Windows**: Check "Add Python to PATH" during install. Restart Command Prompt (CMD).
- Verify: Open CMD and run `python --version` (should show 3.8+).
- **Linux/macOS/Termux**: `sudo apt install python3` (or `pkg install python` in Termux).

### 2. Install Dependencies
Open CMD in your project folder and run:
```
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 requests
```
- If `pip` not found: Run `python -m ensurepip --upgrade` first.
- **Termux**: `pkg install python ffmpeg` (includes FFmpeg).

### 3. Install FFmpeg (For Duration Check & Upscaling)
FFmpeg is required for video processing (optional for basic uploads, but recommended).
- **Windows**:
  1. Download from [ffmpeg.org/download.html#build-windows](https://ffmpeg.org/download.html#build-windows) (e.g., "Windows builds by gyan.dev" → `ffmpeg-release-essentials.zip`).
  2. Extract to `C:\ffmpeg`.
  3. Add to PATH: Search "Environment Variables" in Windows Start → Edit System Variables → Path → Add `C:\ffmpeg\bin` → OK → Restart CMD.
  4. Verify: `ffmpeg -version` and `ffprobe -version` (should print version info).
- **Linux/macOS**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `brew install ffmpeg` (macOS).
- **Termux**: `pkg install ffmpeg`.
- If missing: Script skips upscaling and warns (uploads original).

### 4. Set Up Google YouTube API (Per Account)
For each account (e.g., 'ken'), create OAuth credentials:
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create a new project (or select existing) → Enable "YouTube Data API v3" (search APIs & Services → Library).
3. Go to "Credentials" → "Create Credentials" → "OAuth client ID".
4. App type: **Desktop application** (name it e.g., "YouTube Uploader").
5. Download the JSON file as `client_secrets.json`.
6. Place it in your account folder (see Structure below).
- **Scopes**: The script uses `https://www.googleapis.com/auth/youtube.upload` (upload only).
- **Quotas**: Default 10,000 units/day (enough for ~50 uploads). Request increase if needed.
- Repeat for each account (e.g., separate projects or same project with multiple clients).

### 5. Prepare Instagram Data
- The script reads `instagram_data.json` (root folder).
- **Format** (example for one video):
  ```json
  {
    "https://www.instagram.com/reel/DItyPnhzhJ4/": {
      "media_details": [
        {
          "type": "video",
          "url": "https://instagram.fdel11-1.fna.fbcdn.net/...mp4",
          "dimensions": {
            "width": 1080,
            "height": 1920
          }
        }
      ],
      "post_info": {
        "caption": "👀\n\n#sidhumoosewala #karanaujla #punjabisongs"
      },
      "url_list": ["https://instagram.fdel11-1.fna.fbcdn.net/...mp4"]
    }
  }
  ```
- **How to Generate** (Beginner Options):
  - Use [Instaloader](https://instaloader.github.io/) (Python tool): `pip install instaloader` → `instaloader --login=your_username --no-videos --no-pictures --stories --highlights profile_name` (exports JSON).
  - Browser Extension: "Instagram Downloader" or "Reels Downloader" (export JSON manually).
  - Online Tools: Search "Instagram JSON exporter" (avoid sharing login).
  - Place the JSON in the project root as `instagram_data.json`. Deduping is automatic.

## Project Structure
Create this folder setup (copy files from this repo):
```
Youtube-Automation/
├── README.md                  # This file
├── main.py                    # Run this
├── instagram_data.json        # Your Instagram videos (generate as above)
├── upload_history.json        # Auto-generated (tracks uploads)
├── errors.log                 # Auto-generated (errors)
├── tmp/                       # Auto-created/deleted (downloads)
├── creds/                     # Credentials folder
│   ├── ken/                   # Account 'ken'
│   │   ├── client_secrets.json  # From Google Cloud (per account)
│   │   └── token.json         # Auto-generated after auth
│   ├── itzken/                # Other accounts (same structure)
│   ├── kunikazu/
│   └── naman/
└── src/                       # Script modules (don't edit unless advanced)
    ├── __init__.py            # Empty (package file)
    ├── config.py
    ├── processor.py
    ├── upload.py
    ├── download.py
    ├── utils.py
    └── history.py
```

- **Download the Code**: Copy all files from previous responses (or clone if repo exists). Ensure `src/__init__.py` is empty.

## Usage

### Basic Run (Single Account, One Upload)
Open CMD in the project folder (`cd C:\Users\kunal\Desktop\Codes\python\test\Youtube-Automation`):
```
python main.py --creds-dir ./creds --accounts ken --privacy-status public --one-per-account --upscale
```
- **What Happens**:
  1. Loads only 'ken' account (auth if first time).
  2. Reads `instagram_data.json` (loads 14 videos, skips 1 from history → 13 new).
  3. Downloads first new Reel to `tmp/` (e.g., 10.1s video).
  4. Checks duration (≤60s for Shorts) and upscales if low-res (skips if 1080p).
  5. Cleans title (e.g., "#Shorts 👀 #sidhumoosewala #karanaujla...").
  6. Uploads as public Short to 'ken' channel.
  7. Deletes temp file and cleans `tmp/` at end.
  8. Updates `upload_history.json` (skips next run).
- **Output Example**:
  ```
  Temporary directory: C:\...\tmp
  Loading specified account(s): ken from './creds'...
    - Loaded account 'ken'
  Using accounts: ken (from ./creds)
  Authenticated account 'ken' successfully.
  One-per-account mode: Targeting 1 successful uploads (one per account).
  Loaded 14 unique videos.
  New videos available: 13
  Attempt #1 for success #1/1 to account 'ken': https://www.instagram.com/reel/DItyPnhzhJ4/
    - Parsed: Caption='👀\n\n#sidhumoosewala...', Video path=... (1080x1920)
    - Downloading from https://... to tmp\reel_a5390289.mp4
    - Downloaded successfully (281236 bytes)
    - Valid Shorts video (10.1s)
    - Skipping upscale (already high-res: 1080px width)
    - Uploading to 'ken' as Short (title: '#Shorts 👀 #sidhumoosewala...')
    - Uploading... (attempt 1/3)
    - Upload completed! Video ID: [abc123]
    - SUCCESS on 'ken'! ID: [abc123]
    - Deleted temp file: tmp\reel_a5390289.mp4
  Target of 1 successful uploads reached!

  === SUMMARY ===
  Uploaded: 1
  Skipped/Failed: 0
  Success! Check YouTube for new Shorts.
  Cleaned up temporary directory: C:\...\tmp
  ```
- Check: Go to YouTube Studio → Content → New Short (title with #Shorts, vertical video).

### Advanced Usage
- **Multiple Specific Accounts (One Each)**:
  ```
  python main.py --creds-dir ./creds --accounts ken naman --privacy-status public --one-per-account --upscale
  ```
  - Uploads 1 to 'ken', 1 to 'naman' (round-robin if more videos).

- **All Accounts (Round-Robin, Target 5 Total)**:
  ```
  python main.py --creds-dir ./creds --privacy-status public --target 5 --upscale
  ```
  - No `--accounts`: Loads all valid (e.g., 'ken', 'naman'). Distributes 5 uploads across them.

- **Private/Unlisted Uploads**:
  ```
  python main.py --creds-dir ./creds --accounts ken --privacy-status unlisted --one-per-account
  ```
  - `--privacy-status`: 'public' (default: private), 'private', 'unlisted'.

- **No Upscaling (Faster)**:
  ```
  python main.py --creds-dir ./creds --accounts ken --one-per-account  # Omit --upscale
  ```
  - Skips FFmpeg; uses original video.

- **Custom Target**:
  ```
  python main.py --creds-dir ./creds --accounts ken --target 3 --upscale
  ```
  - 3 uploads to 'ken' (ignores --one-per-account).

### Arguments Reference
Run `python main.py --help` for details:
- `--creds-dir ./creds`: Path to credentials (default: current dir).
- `--accounts ken`: Specific accounts (space-separated; default: all).
- `--privacy-status public`: Video visibility (public/private/unlisted; default: private).
- `--one-per-account`: 1 upload per account (default: false).
- `--target 5`: Total successful uploads (default: 5; ignored with --one-per-account).
- `--upscale`: Enable 2x upscaling (default: off).

## Authentication (First-Time Setup)
1. Run the script (it detects missing token).
2. **Local Server Mode** (Preferred on Windows with GUI):
   - Prints: "Starting local OAuth server...".
   - Browser auto-opens (or copy URL).
   - Sign in → Authorize → Redirects automatically.
3. **Manual Mode** (If hangs/headless/Termux):
   - Prints manual URL: Copy → Open in browser → Sign in → Authorize.
   - Copy FULL redirect URL (e.g., `urn:ietf:wg:oauth:2.0:oob?code=4/0AX4...` or `http://localhost...?code=ABC123`).
   - Paste in terminal: "Paste the full redirect URL: ".
4. Token saves to `./creds/ken/token.json` (future runs auto-refresh).
- **Tips**: Use the exact Google account for the YouTube channel. If error "access denied", recreate `client_secrets.json`. Delete `token.json` to re-auth.

## Generating Instagram JSON (Beginner Guide)
1. **Option 1: Instaloader (Recommended, Free)**:
   - `pip install instaloader`.
   - Run: `instaloader --login=your_instagram_username your_profile --no-videos --no-pictures --json-only`.
   - Outputs JSON files; merge into `instagram_data.json` (use online JSON merger or Python script).
2. **Option 2: Browser Tools**:
   - Install "Instagram Reels Downloader" Chrome extension.
   - Download Reels → Export metadata as JSON (or manual copy-paste).
3. **Option 3: Manual** (For Testing):
   - Create `instagram_data.json` with 1-2 videos (use example above).
   - Get video URL: Right-click Reel → "Copy video URL" (direct MP4 link).
- **Script Handles**: Deduping, relative/absolute paths, caption extraction.

## Troubleshooting
- **"No accounts found matching: ken"**: Ensure `./creds/ken/client_secrets.json` exists. Check spelling (case-sensitive).
- **"Missing ./creds\client_secrets.json"**: Fixed by config (direct subdirs). If fallback, place single JSON in `./creds/`.
- **Auth Hangs/Errors**: Firewall blocks local server? Use manual mode. "Invalid client": Recreate `client_secrets.json` (Desktop app type).
- **"FileNotFoundError: instagram_data.json"**: Create/place JSON in root.
- **"Download FAILED"**: Instagram URL expired? Regenerate JSON. Install `requests` if missing.
- **"Duration unavailable" / FFmpeg Error**: Install FFmpeg (see Prerequisites). Script skips upscaling but uploads.
- **"HTTP 400 invalidTitle"**: Fixed (cleans newlines). If persists, check caption in JSON.
- **"Quota exceeded"**: YouTube limit hit. Wait 24h or request quota increase in Google Cloud.
- **Windows Paths**: Uses `\` automatically. If issues, run as admin.
- **No Uploads**: Check `errors.log` (e.g., "Too long for Shorts"). Ensure videos ≤60s.
- **Token Invalid**: Delete `./creds/ken/token.json` → Re-run for re-auth.

**Debug Mode**: Add `print` statements in `src/processor.py` (advanced). Run with `--target 1` for testing.

## Customization (Advanced)
- **Upscale Settings** (`src/utils.py`): Edit CRF (23=good quality; lower=better but larger), preset ('ultrafast'=fast; 'slow'=better compression).
- **Title Length**: Change `[:100]` in `processor.py` (YouTube max 100 chars).
- **Category**: Edit `categoryId="22"` in `upload.py` (22=People & Blogs; see YouTube docs).
- **JSON Structure**: Adapt parsing in `processor.py` if your JSON differs.
- **No FFmpeg**: Set `upscale=False` in `main.py` call.

## Contributing & License
- **Issues**: Open GitHub issue (or comment here).
- **License**: MIT (free to use/modify). Credit if forked.
- **Author**: Based on your setup; extend as needed.

**First Run Tips**: Start with `--one-per-account --target 1` (safe). Verify upload in YouTube app/Studio. Happy automating! 🚀

If stuck, share error logs/output for help.
