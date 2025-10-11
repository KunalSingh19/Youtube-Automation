#!/usr/bin/env python3
"""
Main entry point for YouTube upload automation from Instagram JSON.
Supports multiple accounts, one-per-account mode, privacy settings, upscaling.
Cross-platform: Windows, Linux, macOS, Termux.
"""

import argparse
import os
import shutil
import sys
from src import processor, upload, history
from src.config import (
    INSTAGRAM_JSON_FILE, UPLOAD_HISTORY_FILE,
    DEFAULT_CLIENT_SECRETS_FILE, DEFAULT_ACCOUNTS_DIR
)

def parse_args():
    parser = argparse.ArgumentParser(description="Upload Instagram Reels to YouTube Shorts.")
    parser.add_argument('--creds-dir', default='.', help="Directory for credentials (default: .)")
    parser.add_argument('--accounts', nargs='+', help="Account names (e.g., 'ken' or 'ken jill')")
    parser.add_argument('--privacy-status', default='private', choices=['public', 'private', 'unlisted'],
                        help="YouTube privacy status (default: private)")
    parser.add_argument('--one-per-account', action='store_true',
                        help="Upload only one video per account (default: all to round-robin)")
    parser.add_argument('--target', type=int, default=5,
                        help="Target successful uploads (default: 5; ignored in one-per-account)")
    parser.add_argument('--upscale', action='store_true',
                        help="Upscale videos 2x (to ~1080x1920) using FFmpeg before upload (default: off)")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Cross-platform tmp dir setup (creates if needed)
    tmp_dir = os.path.join(os.getcwd(), 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    print(f"Temporary directory: {tmp_dir}")
    
    try:
        # Load accounts (pass target_accounts for single-account focus)
        accounts_dir = os.path.join(args.creds_dir, DEFAULT_ACCOUNTS_DIR)
        client_secrets_file = os.path.join(args.creds_dir, DEFAULT_CLIENT_SECRETS_FILE)
        all_account_services, num_accounts = upload.get_account_services(
            accounts_dir, client_secrets_file, target_accounts=args.accounts
        )
        
        if args.accounts:
            # Filter to specified accounts (case-sensitive match)
            account_services = {
                name: svc for name, svc in all_account_services.items() if name in args.accounts
            }
            if not account_services:
                raise ValueError(f"No accounts found matching: {args.accounts}")
            print(f"Using accounts: {', '.join(args.accounts)} (from {args.creds_dir})")
            num_accounts = len(account_services)
        else:
            account_services = all_account_services
            print(f"Using all accounts from {accounts_dir if os.path.exists(accounts_dir) else args.creds_dir}")
        
        # Authenticate each (already handled in get_account_services, but confirm)
        for acc_name in account_services:
            print(f"Authenticated account '{acc_name}' successfully.")
        
        # Determine target successes
        if args.one_per_account:
            target_successes = num_accounts
            print(f"One-per-account mode: Targeting {target_successes} successful uploads (one per account).")
        else:
            target_successes = args.target
            print(f"Round-robin mode: Targeting {target_successes} successful uploads across {num_accounts} accounts.")
        
        # Load and filter data
        new_items_list, total_available = processor.load_and_filter_data()
        
        # Load history for processing
        upload_history = history.load_upload_history(UPLOAD_HISTORY_FILE)
        
        # Process uploads (pass upscale flag)
        uploaded_count, skipped_count = processor.process_uploads(
            account_services, num_accounts, new_items_list,
            target_successes, args.privacy_status, upload_history,
            upscale=args.upscale
        )
        
        # Summary
        print(f"\n=== SUMMARY ===")
        print(f"Target successes: {target_successes}")
        print(f"Uploaded: {uploaded_count}")
        print(f"Skipped/Failed: {skipped_count}")
        print(f"Total processed: {uploaded_count + skipped_count}/{total_available}")
        if uploaded_count > 0:
            print("Success! Check YouTube for new Shorts.")
        else:
            print("No uploads completed. Check errors.log for details.")
    
    except upload.QuotaExceededError:
        print("\nStopped due to YouTube quota exceeded.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"File error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Value error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cross-platform tmp cleanup (recursive, safe)
        if os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                print(f"Cleaned up temporary directory: {tmp_dir}")
            except Exception as cleanup_err:
                print(f"Warning: Could not fully clean up {tmp_dir}: {cleanup_err}")
                # List remaining files for debug
                remaining = [f for f in os.listdir(tmp_dir) if os.path.isfile(os.path.join(tmp_dir, f))]
                if remaining:
                    print(f"  Remaining files: {remaining}")

if __name__ == "__main__":
    main()