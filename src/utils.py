import re
import datetime

ERROR_LOG_FILE = "error_log.txt"

def log_error(insta_url: str, error_message: str):
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] URL: {insta_url}\nError: {error_message}\n\n"
    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def extract_tags_from_caption(caption: str):
    tags = re.findall(r'#(\w+)', caption)
    unique_tags = list(dict.fromkeys(tags))
    return unique_tags[:30]