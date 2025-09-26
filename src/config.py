"""
Configuration constants for the project.
"""

import os

# File paths (relative to project root)
INSTAGRAM_JSON_FILE = os.path.join("Data", "reelsData.json")
UPLOAD_HISTORY_FILE = "upload_history.json"
ERROR_LOG_FILE = "error_log.txt"
TMP_DIR = "tmp"
DEFAULT_CREDS_DIR = "./creds"
DEFAULT_BATCH_SIZE = 3
DEFAULT_PRIVACY_STATUS = "public"

# Ensure tmp dir exists
os.makedirs(TMP_DIR, exist_ok=True)