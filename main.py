"""
Entry point for the Instagram to YouTube uploader.
"""

import sys
import argparse
from src import config, accounts, processor, history
from src.config import (
    DEFAULT_BATCH_SIZE, 
    DEFAULT_PRIVACY_STATUS, 
    DEFAULT_CREDS_DIR, 
    UPLOAD_HISTORY_FILE
)
from src.upload import QuotaExceededError

def main():
    parser = argparse.ArgumentParser(
        description="Upload Instagram videos to YouTube (multi-account support). "
                   "Loads videos from reelsData.json, downloads if needed, and uploads "
                   "with history tracking to avoid duplicates. Supports round-robin "
                   "distribution across accounts and success-based batching (skips errors)."
    )
    parser.add_argument(
        "--creds-dir", 
        default=DEFAULT_CREDS_DIR, 
        help="Directory containing subfolders for each account's credentials (e.g., ./creds/account1/client_secrets.json). Default: ./creds"
    )
    parser.add_argument(
        "--accounts", 
        help="Comma-separated list of specific account subfolder names to use (e.g., 'account1,account2'). Skips others in the creds dir."
    )
    parser.add_argument(
        "--all-accounts", 
        action="store_true", 
        help="Automatically discover and use all valid account subfolders in --creds-dir (mutually exclusive with --accounts)."
    )
    parser.add_argument(
        "--privacy-status", 
        default=DEFAULT_PRIVACY_STATUS, 
        choices=["public", "private", "unlisted"], 
        help="Privacy status for uploaded YouTube videos. Options: public (visible to everyone), private (only you), unlisted (link-only). Default: private"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=DEFAULT_BATCH_SIZE, 
        help="Target number of successful uploads to achieve (global across accounts). The script skips errors/failures and continues until this many successes or no more new videos. Default: 5"
    )
    parser.add_argument(
        "--upload-one", 
        action="store_true", 
        help="Special mode: Target exactly 1 successful upload (to the first account). Skips errors and keeps trying new videos until achieved (overrides --batch-size)."
    )
    parser.add_argument(
        "--one-per-account", 
        action="store_true", 
        help="Special mode: Target exactly 1 successful upload per active account (total = number of accounts). Distributes via round-robin, skips errors, and continues until achieved (overrides --batch-size; mutually exclusive with --upload-one)."
    )

    args = parser.parse_args()
    batch_limit = args.batch_size
    upload_one_mode = args.upload_one
    one_per_account_mode = args.one_per_account

    # Mutual exclusivity checks
    if args.accounts and args.all_accounts:
        parser.error("--accounts and --all-accounts are mutually exclusive.")
    if upload_one_mode and one_per_account_mode:
        parser.error("--upload-one and --one-per-account are mutually exclusive.")

    # Load upload history once (for updates in processor)
    upload_history = history.load_upload_history(UPLOAD_HISTORY_FILE)

    # Get list of account names
    try:
        account_names = accounts.get_account_names(args.creds_dir, args.accounts, args.all_accounts)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print(f"Using accounts: {', '.join(account_names)} (from {args.creds_dir})")

    # Load and filter data (new items list)
    try:
        new_items_list, total_available = processor.load_and_filter_data()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Authenticate accounts
    try:
        account_services, num_accounts = accounts.authenticate_accounts(args.creds_dir, account_names)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine target successes based on mode
    if one_per_account_mode:
        target_successes = num_accounts
        print(f"One-per-account mode: Targeting {target_successes} successful uploads (one per account).")
    elif upload_one_mode:
        target_successes = 1
        print("Upload-one mode: Targeting 1 successful upload.")
    else:
        target_successes = batch_limit
        print(f"Batch mode: Targeting {target_successes} successful uploads (skipping errors).")

    # Process uploads (pass the shared upload_history)
    try:
        uploaded_count, skipped_count = processor.process_uploads(
            account_services, num_accounts, new_items_list, 
            target_successes, args.privacy_status, upload_history
        )
    except QuotaExceededError:
        print("\nGlobal quota exceeded - stopping all uploads.")
        sys.exit(1)

    # Summary
    if uploaded_count >= target_successes:
        print(f"\nTarget achieved: {uploaded_count} successful uploads out of {total_available} available new items.")
    else:
        print(f"\nStopped: {uploaded_count} successful uploads (target was {target_successes}), {skipped_count} skipped out of {total_available} available new items.")
    
    if uploaded_count == 0:
        print("No successful uploads! Check error_log.txt for details.")
        sys.exit(1)
    
    print("History saved.")
    sys.exit(0)

if __name__ == "__main__":
    main()