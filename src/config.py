"""
Configuration constants.
Cross-platform paths (relative to script dir).
"""

import os  # For path utilities

# Files and directories (relative paths)
INSTAGRAM_JSON_FILE = 'Data/reelsData.json'
UPLOAD_HISTORY_FILE = 'upload_history.json'
DEFAULT_CLIENT_SECRETS_FILE = 'client_secrets.json'
DEFAULT_ACCOUNTS_DIR = ''  # Subdir for multiple accounts
TMP_DIR = os.path.join(os.getcwd(), 'tmp')  # Full path to tmp dir (cross-platform)
ERROR_LOG_FILE = 'errors.log'  # Error log file (relative path)

# YouTube defaults
DEFAULT_PRIVACY_STATUS = 'public'  # Fallback privacy (public/private/unlisted)