"""
Core logic for loading data, filtering, and processing uploads with success-based batching.
"""

import json
import os
from . import download, upload, utils, history
from .config import INSTAGRAM_JSON_FILE, UPLOAD_HISTORY_FILE
from .upload import QuotaExceededError

def load_and_filter_data():
    """
    Load Instagram JSON, dedupe, load history, and filter new items.
    
    Returns:
        tuple: (new_items_list: list of (url, data), total_available: int)
    
    Raises:
        FileNotFoundError: If JSON file missing.
        ValueError: If no new items.
    """
    if not os.path.exists(INSTAGRAM_JSON_FILE):
        raise FileNotFoundError(f"Instagram JSON file '{INSTAGRAM_JSON_FILE}' does not exist.")

    with open(INSTAGRAM_JSON_FILE, 'r', encoding='utf-8') as f:
        insta_data = json.load(f)

    # Dedupe
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

    # Load history for filtering (local to this function)
    upload_history = history.load_upload_history(UPLOAD_HISTORY_FILE)
    print(f"History: {len(upload_history)} entries (skipping uploaded/failed).")

    # Filter new items
    new_items = {url: data for url, data in insta_data.items() if url not in upload_history}
    print(f"New videos available: {len(new_items)}")

    if not new_items:
        raise ValueError("No new videos to upload! All done.")

    # Convert to ordered list for iteration (preserves JSON order)
    new_items_list = list(new_items.items())
    return new_items_list, len(new_items_list)

def process_uploads(account_services, num_accounts, new_items_list, target_successes, privacy_status, upload_history, upscale=False):
    """
    Process uploads in a loop until target successes, skipping errors.
    
    Args:
        account_services (dict): {account_name: youtube_service}
        num_accounts (int): Number of active accounts.
        new_items_list (list): List of (insta_url, post_data) tuples.
        target_successes (int): Target number of successful uploads.
        privacy_status (str): YouTube privacy status.
        upload_history (dict): Current history dict (updated in-place).
        upscale (bool): Whether to upscale low-res videos.
    
    Returns:
        tuple: (uploaded_count: int, skipped_count: int)
    
    Raises:
        QuotaExceededError: If quota exceeded (global stop).
    """
    uploaded_count = 0
    skipped_count = 0
    video_index = 0  # Attempt index
    account_index = 0  # For round-robin

    # Loop until target successes or no more new videos
    while uploaded_count < target_successes and video_index < len(new_items_list):
        insta_url, post_data = new_items_list[video_index]
        video_index += 1  # Increment attempt

        # Pick next account (round-robin)
        acc_name = list(account_services.keys())[account_index % num_accounts]
        account_index += 1
        youtube = account_services[acc_name]
        print(f"Attempt #{video_index} for success #{uploaded_count + 1}/{target_successes} to account '{acc_name}': {insta_url}")

        # Robust JSON parsing with validation (adapted to provided structure)
        try:
            media_details = post_data.get('media_details', [])
            if not media_details or len(media_details) == 0:
                raise KeyError("No media_details")
            first_media = media_details[0]
            if not isinstance(first_media, dict) or first_media.get('type') != 'video':
                raise KeyError("First media is not a video (carousel/image?)")
            video_url = first_media.get('url', '')  # Local relative path, e.g., "videos/reel.mp4"
            if not video_url:
                raise KeyError("No url in media_details[0]")
            # Resolve relative path to absolute (relative to project root)
            video_path = os.path.abspath(os.path.join(os.getcwd(), video_url))
            description = post_data.get('post_info', {}).get('caption', '')
            # Optional: Log dimensions from JSON
            dimensions = first_media.get('dimensions', {})
            dim_str = f" ({dimensions.get('width', 'N/A')}x{dimensions.get('height', 'N/A')})" if dimensions else ""
            print(f"  - Parsed: Caption='{description[:50]}...', Video path={video_path}{dim_str}")
            # Optional: Warn if url_list mismatches (redundant field)
            url_list = post_data.get('url_list', [])
            if url_list and video_url not in url_list:
                print(f"  - Warning: media_details url not in url_list")
        except Exception as e:
            print(f"  - Skipped (JSON error: {e})")
            utils.log_error(insta_url, f"JSON error: {e}")
            upload_history[insta_url] = {"status": "failed", "reason": "JSON error"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue  # Skip error, continue to next video

        # Determine if local path or remote URL, and get final video_path
        if video_url.startswith(('http://', 'https://')):
            # Remote URL: Download to unique local file if needed
            local_filename = download.get_unique_filename(insta_url)
            if not os.path.exists(local_filename) or os.path.getsize(local_filename) == 0:
                try:
                    print(f"  - Downloading from {video_url} to {local_filename}")
                    download.download_video(video_url, local_filename, insta_url)
                except Exception as e:
                    print(f"  - Download FAILED ({str(e)[:50]}) - Skipping to next video")
                    utils.log_error(insta_url, f"Download error: {e}")
                    upload_history[insta_url] = {"status": "failed", "reason": f"Download failed: {str(e)[:100]}"}
                    history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
                    skipped_count += 1
                    continue  # Skip error, continue to next video
            else:
                print(f"  - Using existing downloaded file: {local_filename}")
            video_path = local_filename
        else:
            # Local path: Use directly if exists (updated for relative paths)
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                reason = "File missing" if not os.path.exists(video_path) else "File empty"
                print(f"  - Skipped ({reason}: {video_path}) - Continuing to next video")
                utils.log_error(insta_url, reason)
                upload_history[insta_url] = {"status": "failed", "reason": reason}
                history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
                skipped_count += 1
                continue  # Skip error, continue to next video
            print(f"  - Using local file: {video_path}")

        # Video file is ready - check duration for Shorts eligibility
        duration = utils.get_video_duration(video_path)
        if duration == -1:
            print(f"  - Skipped (duration unavailable: {video_path}) - Continuing to next video")
            utils.log_error(insta_url, "Duration check failed")
            upload_history[insta_url] = {"status": "failed", "reason": "Duration unavailable"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue
        if duration > 60:
            print(f"  - Skipped (too long for Shorts: {duration:.1f}s) - Continuing to next video")
            utils.log_error(insta_url, f"Duration too long: {duration}s")
            upload_history[insta_url] = {"status": "failed", "reason": f"Too long for Shorts ({duration}s)"}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue
        print(f"  - Valid Shorts video ({duration:.1f}s)")

        # Optional: Upscale if enabled and resolution is low (check width <1080)
        processed_path = video_path
        if upscale:
            width = utils.get_video_width(video_path)
            if width < 1080 and utils.has_ffmpeg():
                upscaled_filename = video_path.replace('.mp4', '_upscaled.mp4')
                print(f"  - Upscaling low-res video ({width}px width) to 2x...")
                try:
                    success = utils.upscale_video(video_path, upscaled_filename)
                    if success:
                        processed_path = upscaled_filename
                        # Delete original temp after successful upscale
                        if video_path.startswith(os.path.join(os.getcwd(), 'tmp')):
                            os.remove(video_path)
                            print(f"  - Deleted original temp: {video_path}")
                        print(f"  - Upscale complete: {processed_path}")
                    else:
                        print(f"  - Upscale failed; using original: {video_path}")
                except Exception as upscale_err:
                    print(f"  - Upscale error ({str(upscale_err)[:50]}); using original")
            else:
                if width >= 1080:
                    print(f"  - Skipping upscale (already high-res: {width}px width)")
                else:
                    print(f"  - Skipping upscale (FFmpeg not available)")
        else:
            print(f"  - Upscaling disabled")

        # Proceed to upload
        tags = utils.extract_tags_from_caption(description)
        class Options:
            pass
        options = Options()
        # Clean title: Replace newlines with spaces, collapse whitespace, truncate to 100 chars
        cleaned_desc = description.replace('\n', ' ').strip()
        base_title = ' '.join(cleaned_desc.split())[:100]  # Collapse multiple spaces
        if not base_title or len(base_title) < 3:  # Fallback if empty/short after cleaning
            base_title = f"#Shorts #InstagramReel_{video_index}"
        # Enforce #Shorts in title for Shorts eligibility
        if not base_title.lower().startswith('#shorts'):
            truncated_title = f"#Shorts {base_title}"
            truncated_title = truncated_title[:100]  # Ensure <=100 after prepend
        else:
            truncated_title = base_title[:100]
        options.file = processed_path  # Use processed (upscaled) file
        options.title = truncated_title
        options.description = description  # Keep original description (newlines OK there)
        options.privacy_status = privacy_status
        options.tags = tags + ['#Shorts', '#YouTubeShorts']  # Reinforce tags

        print(f"  - Uploading to '{acc_name}' as Short (title: '{truncated_title[:50]}...')")
        try:
            video_id = upload.initialize_upload(youtube, options, insta_url)
            print(f"  - SUCCESS on '{acc_name}'! ID: {video_id}")
            # Success: Update history (with account)
            upload_history[insta_url] = {"status": "success", "youtube_video_id": video_id, "account": acc_name}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            # Auto-delete temp file after success (if in tmp/, including upscaled)
            if processed_path.startswith(os.path.join(os.getcwd(), 'tmp')):
                try:
                    os.remove(processed_path)
                    print(f"  - Deleted temp file: {processed_path}")
                except OSError as del_err:
                    print(f"  - Warning: Could not delete {processed_path}: {del_err}")
            uploaded_count += 1
            print(f"  - Success #{uploaded_count}/{target_successes} achieved - Continuing for target...")
            if uploaded_count >= target_successes:
                print(f"Target of {target_successes} successful uploads reached!")
                return uploaded_count, skipped_count
        except QuotaExceededError:
            print(f"  - FAILED on '{acc_name}' (Quota exceeded - stopping all uploads)")
            utils.log_error(insta_url, "QuotaExceededError")
            upload_history[insta_url] = {"status": "failed", "reason": "Quota exceeded", "account": acc_name}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            raise  # Re-raise to stop globally
        except Exception as e:
            print(f"  - FAILED on '{acc_name}' ({str(e)[:50]}) - Skipping to next video")
            utils.log_error(insta_url, str(e))
            upload_history[insta_url] = {"status": "failed", "reason": str(e)[:100], "account": acc_name}
            history.save_upload_history(UPLOAD_HISTORY_FILE, upload_history)
            skipped_count += 1
            continue  # Skip error, continue to next video

    return uploaded_count, skipped_count