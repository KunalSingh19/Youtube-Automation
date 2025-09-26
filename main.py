import os
import sys
import argparse
import json
from src import download, upload, utils, history
from src.upload import QuotaExceededError

INSTAGRAM_JSON_FILE = "Data/reelsData.json"
UPLOAD_HISTORY_FILE = "upload_history.json"
BATCH_SIZE = 5  # Default for batch mode

def main():
    parser = argparse.ArgumentParser(description="Upload Instagram videos to YouTube using local paths or remote URLs in JSON")
    parser.add_argument("--client-secrets", required=True, help="Path to client_secrets.json")
    parser.add_argument("--privacy-status", default="private", choices=["public", "private", "unlisted"], help="YouTube video privacy status")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Max videos to attempt (default 5)")
    parser.add_argument("--upload-one", action="store_true", help="Upload exactly one NEW successful video and stop (skips history)")

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

    # Filter to only new items upfront for efficiency
    new_items = {url: data for url, data in insta_data.items() if url not in upload_history}
    print(f"New videos to process: {len(new_items)}")

    youtube = upload.get_authenticated_service(args.client_secrets)

    uploaded_count = 0
    skipped_count = 0
    effective_batch = 1 if upload_one_mode else batch_limit  # For upload-one, limit to 1

    video_index = 0

    for insta_url, post_data in new_items.items():
        video_index += 1
        if video_index > effective_batch:
            print(f"Reached limit of {effective_batch}. Stopping.")
            break

        print(f"Processing next new video #{video_index}: {insta_url}")

        # Robust JSON parsing with validation
        try:
            media_details = post_data.get('media_details', [])
            if not media_details or len(media_details) == 0:
                raise KeyError("No media_details")
            video_url = media_details[0].get('url', '')  # Could be local path or remote URL
            if not video_url:
                raise KeyError("No url in media_details[0]")
            description = post_data.get('post_info', {}).get('caption', '')
        except Exception as e:
            print(f"  - Skipped (JSON error: {e})")
            utils.log_error(insta_url, f"JSON error: {e}")
            upload_history[insta_url] = {"status": "failed", "reason": "JSON error"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue

        # Determine if local path or remote URL, and get final video_path
        if video_url.startswith(('http://', 'https://')):
            # Remote URL: Download to unique local file if needed
            local_filename = download.get_unique_filename(insta_url)
            if not os.path.exists(local_filename) or os.path.getsize(local_filename) == 0:
                try:
                    print(f"  - Downloading from {video_url} to {local_filename}")
                    download.download_video(video_url, local_filename, insta_url)
                except Exception as e:
                    print(f"  - Download FAILED ({str(e)[:50]})")
                    utils.log_error(insta_url, f"Download error: {e}")
                    upload_history[insta_url] = {"status": "failed", "reason": f"Download failed: {str(e)[:100]}"}
                    history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
                    skipped_count += 1
                    continue
            else:
                print(f"  - Using existing downloaded file: {local_filename}")
            video_path = local_filename
        else:
            # Local path: Use directly if exists
            video_path = video_url
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                reason = "File missing" if not os.path.exists(video_path) else "File empty"
                print(f"  - Skipped ({reason}: {video_path})")
                utils.log_error(insta_url, reason)
                upload_history[insta_url] = {"status": "failed", "reason": reason}
                history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
                skipped_count += 1
                continue
            print(f"  - Using local file: {video_path}")

        # Video file is ready - proceed to upload
        tags = utils.extract_tags_from_caption(description)
        duration = utils.get_video_duration(video_path)
        if duration != -1 and duration <= 60:
            print(f"  - Short video ({duration:.1f}s)")

        class Options:
            pass
        options = Options()
        truncated_title = (description.strip()[:100] or f"#Shorts #YtShorts #InstagramReel_{video_index}")
        options.file = video_path
        options.title = truncated_title
        options.description = description
        options.privacy_status = args.privacy_status
        options.tags = tags

        print(f"  - Uploading (title: '{truncated_title[:50]}...')")
        try:
            video_id = upload.initialize_upload(youtube, options, insta_url)
            print(f"  - SUCCESS! ID: {video_id}")
        except QuotaExceededError:
            print(f"  - FAILED (Quota exceeded - stopping all uploads)")
            utils.log_error(insta_url, "QuotaExceededError")
            upload_history[insta_url] = {"status": "failed", "reason": "Quota exceeded"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            sys.exit(1)
        except Exception as e:
            print(f"  - FAILED ({str(e)[:50]})")
            utils.log_error(insta_url, str(e))
            upload_history[insta_url] = {"status": "failed", "reason": str(e)[:100]}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue

        # Success: Update history (upload-focused, no local_path)
        upload_history[insta_url] = {"status": "success", "youtube_video_id": video_id}
        history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
        uploaded_count += 1

        # In upload-one mode: Stop after exactly one success
        if upload_one_mode:
            print("One new upload complete. Finishing.")
            break

    total_new = len(new_items)
    print(f"\nComplete: Uploaded {uploaded_count}, Skipped {skipped_count}/{total_new} new items")
    if uploaded_count == 0 and total_new > 0:
        print("No successful uploads! Check error_log.txt for details.")
        sys.exit(1)
    elif uploaded_count == 0:
        print("No new videos to upload! All done.")
        sys.exit(0)
    print("History saved.")

if __name__ == "__main__":
    main()