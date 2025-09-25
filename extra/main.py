import os
import sys
import argparse
import json
from src import download, upload, utils, history
from src.upload import BatchLimitReached, QuotaExceededError

INSTAGRAM_JSON_FILE = "Data/reelsData.json"
UPLOAD_HISTORY_FILE = "upload_history.json"
BATCH_SIZE = 5  # Default for batch mode

def main():
    parser = argparse.ArgumentParser(description="Upload pre-downloaded Instagram videos to YouTube using local paths in JSON")
    parser.add_argument("--client-secrets", required=True, help="Path to client_secrets.json")
    parser.add_argument("--privacy-status", default="private", choices=["public", "private", "unlisted"], help="YouTube video privacy status")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Max videos to attempt (default 5)")
    parser.add_argument("--upload-one", action="store_true", help="Upload exactly one NEW successful video and stop (skips history)")
    # Removed category-id argument

    args = parser.parse_args()
    batch_limit = args.batch_size
    upload_one_mode = args.upload_one

    if not os.path.exists(INSTAGRAM_JSON_FILE):
        print(f"Error: Instagram JSON file '{INSTAGRAM_JSON_FILE}' does not exist.")
        sys.exit(1)

    if not os.path.exists(args.client_secrets):
        print(f"Error: Client secrets file '{args.client_secrets}' does not exist.")
        sys.exit(1)

    with open(INSTAGRAM_JSON_FILE, 'r', encoding='utf-8') as f:
        insta_data = json.load(f)

    # Dedupe if any duplicates
    seen = set()
    unique_data = {}
    duplicates = 0
    for url, data in insta_data.items():
        if url in seen:
            duplicates += 1
        else:
            seen.add(url)
            unique_data[url] = data
    if duplicates > 0:
        print(f"Warning: Removed {duplicates} duplicate URLs.")
    insta_data = unique_data
    print(f"Loaded {len(insta_data)} unique videos.")

    upload_history = history.load_upload_history(UPLOAD_HISTORY_FILE)
    print(f"History: {len(upload_history)} entries (skipping uploaded/failed).")

    youtube = upload.get_authenticated_service(args.client_secrets)

    uploaded_count = 0
    skipped_count = 0
    effective_batch = len(insta_data) if upload_one_mode else batch_limit  # Full list for one-mode to find next new

    video_index = 0  # Track position for "next new"

    for insta_url, post_data in insta_data.items():
        video_index += 1
        if uploaded_count >= effective_batch:
            print(f"Reached limit of {effective_batch}. Stopping.")
            break

        # ALWAYS skip history (success or failed) - prevents re-uploads
        if insta_url in upload_history:
            status = upload_history[insta_url].get("status", "success")
            if status == "success":
                print(f"Skipped (already uploaded): {insta_url}")
            else:
                print(f"Skipped (failed before): {insta_url}")
            skipped_count += 1
            continue

        print(f"Processing next new video #{video_index}: {insta_url}")

        try:
            video_path = post_data['media_details'][0]['url']
            description = post_data['post_info'].get('caption', '')
        except Exception as e:
            print(f"  - Skipped (JSON error: {e})")
            utils.log_error(insta_url, f"JSON error: {e}")
            upload_history[insta_url] = {"status": "failed", "reason": "JSON error"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue

        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            reason = "File missing" if not os.path.exists(video_path) else "File empty"
            print(f"  - Skipped ({reason}: {video_path})")
            utils.log_error(insta_url, reason)
            upload_history[insta_url] = {"status": "failed", "reason": reason}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue

        tags = utils.extract_tags_from_caption(description)
        duration = download.get_video_duration(video_path)
        if duration != -1 and duration <= 60:
            print(f"  - Short video ({duration:.1f}s)")

        class Options:
            pass
        options = Options()
        truncated_title = description.strip()[:100] or "#Shorts #YtShorts #Instagram #Reel"
        options.file = video_path
        options.title = truncated_title
        options.description = description
        options.privacy_status = args.privacy_status
        options.tags = tags

        print(f"  - Uploading (title: '{truncated_title[:50]}...')")
        try:
            video_id = upload.initialize_upload(youtube, options, insta_url, uploaded_count, effective_batch)
            print(f"  - SUCCESS! ID: {video_id}")
        except Exception as e:
            print(f"  - FAILED ({str(e)[:50]})")
            utils.log_error(insta_url, str(e))
            upload_history[insta_url] = {"status": "failed", "reason": str(e)[:100]}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue

        # Success: Update history
        upload_history[insta_url] = {"status": "success", "youtube_video_id": video_id}
        history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
        print("Upload history saved to upload_history.json")
        uploaded_count += 1

        # In upload-one mode: Stop after exactly one success
        if upload_one_mode:
            print("One new upload complete. Finishing.")
            break

    print(f"\nComplete: Uploaded {uploaded_count}, Skipped {skipped_count}/{len(insta_data)}")
    if uploaded_count == 0:
        print("No new videos to upload! All done or check error_log.txt.")
        sys.exit(0 if len(upload_history) >= len(insta_data) else 1)  # Graceful if all uploaded
    print("History saved.")

if __name__ == "__main__":
    main()
