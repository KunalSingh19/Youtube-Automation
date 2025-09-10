import os
import sys
import argparse
import json
from src import download, upload, utils, history

INSTAGRAM_JSON_FILE = "Data/reelsData.json"
UPLOAD_HISTORY_FILE = "upload_history.json"
BATCH_SIZE = 3

def main():
    parser = argparse.ArgumentParser(description="Download Instagram videos and upload to YouTube")
    parser.add_argument("--client-secrets", required=True, help="Path to client_secrets.json")
    parser.add_argument("--privacy-status", default="private", choices=["public", "private", "unlisted"], help="YouTube video privacy status")
    parser.add_argument("--category-id", default="20", help="YouTube video category ID (default: 20 = Gaming)")

    args = parser.parse_args()

    if not os.path.exists(INSTAGRAM_JSON_FILE):
        print(f"Error: Instagram JSON file '{INSTAGRAM_JSON_FILE}' does not exist.")
        sys.exit(1)

    if not os.path.exists(args.client_secrets):
        print(f"Error: Client secrets file '{args.client_secrets}' does not exist.")
        sys.exit(1)

    insta_data = None
    with open(INSTAGRAM_JSON_FILE, 'r', encoding='utf-8') as f:
        insta_data = f.read()
    insta_data = json.loads(insta_data)

    upload_history = history.load_upload_history(UPLOAD_HISTORY_FILE)
    youtube = upload.get_authenticated_service(args.client_secrets)

    uploaded_count = 0

    for insta_url, post_data in insta_data.items():
        if uploaded_count >= BATCH_SIZE:
            print(f"Reached batch limit of {BATCH_SIZE} videos. Stopping.")
            break

        if insta_url in upload_history:
            print(f"Skipping already uploaded Instagram URL: {insta_url}")
            continue

        try:
            video_url = post_data['media_details'][0]['url']
            description = post_data['post_info'].get('caption', '')
        except (KeyError, IndexError) as e:
            error_msg = f"Error parsing Instagram JSON: {e}"
            print(error_msg)
            utils.log_error(insta_url, error_msg)
            continue

        tags = utils.extract_tags_from_caption(description)
        print(f"Extracted tags from caption: {tags}")

        video_filename = download.get_unique_filename(insta_url)

        try:
            download.download_video(video_url, video_filename, insta_url)
        except Exception as e:
            print(f"Error downloading video for {insta_url}: {e}")
            continue

        duration = download.get_video_duration(video_filename)
        if duration != -1:
            print(f"Video duration: {duration:.2f} seconds")
            if duration <= 60:
                print("Warning: This video is 60 seconds or less and will likely be uploaded as a YouTube Short.")

        class Options:
            pass

        options = Options()
        truncated_title = description.strip()[:100]
        if not truncated_title:
            truncated_title = "#Shorts #YtShorts #Instagram #Reel"
        options.file = video_filename
        options.title = truncated_title
        options.description = description
        options.privacy_status = args.privacy_status
        options.tags = tags
        options.category_id = args.category_id

        try:
            video_id = upload.initialize_upload(youtube, options, insta_url)
        except Exception as e:
            print(f"Upload failed for {insta_url}: {e}")
            if os.path.exists(video_filename):
                try:
                    os.remove(video_filename)
                except PermissionError:
                    print(f"Could not delete {video_filename} because it is in use.")
            continue

        upload_history[insta_url] = {
            "youtube_video_id": video_id
        }
        history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)

        if os.path.exists(video_filename):
            try:
                os.remove(video_filename)
                print(f"Deleted temporary video file {video_filename}")
            except PermissionError:
                print(f"Could not delete {video_filename} because it is in use.")

        uploaded_count += 1

if __name__ == "__main__":
    main()