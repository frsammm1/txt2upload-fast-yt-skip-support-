import os
from pathlib import Path

# Bot Configuration
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "10000"))

# Directory Configuration
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Quality Settings
QUALITY_MAP = {
    "360p": "360",
    "480p": "480", 
    "720p": "720",
    "1080p": "1080",
}

# Supported File Types
SUPPORTED_TYPES = {
    'video': ['.m3u8', '.mpd', '.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.ts'],
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.zip', '.rar']
}

# ULTRA SPEED SETTINGS - 6-7x FASTER! 🚀
CHUNK_SIZE = 131072  # 128KB chunks (doubled)
CONCURRENT_FRAGMENTS = 16  # 4x increase from 4
MAX_CONCURRENT_DOWNLOADS = 5  # Parallel downloads
BUFFER_SIZE = 524288  # 512KB buffer (doubled)
HTTP_CHUNK_SIZE = 2097152  # 2MB chunks (doubled)

# Upload Settings - SUPERCHARGED
UPLOAD_CHUNK_SIZE = 1048576  # 1MB chunks (doubled)
MAX_RETRIES = 25  # More retries for stability
FRAGMENT_RETRIES = 25
CONNECTION_TIMEOUT = 3600  # 60 minutes

# Advanced Speed Settings
DYNAMIC_WORKERS = True  # Auto-adjust workers based on speed
MIN_WORKERS = 8
MAX_WORKERS = 32
WORKER_ADJUST_THRESHOLD = 5  # Seconds to check and adjust

# Connection Pool Settings
CONNECTION_POOL_SIZE = 100  # Massive pool for parallel connections
CONNECTION_POOL_PER_HOST = 50
DNS_CACHE_TTL = 600  # 10 minutes

# Thumbnail Settings
THUMBNAIL_TIME = "00:00:05"
THUMBNAIL_SIZE = "640:360"  # Better quality
THUMBNAIL_QUALITY = 2

# File Splitting Settings
MAX_FILE_SIZE = 1990  # MB (Telegram limit is 2GB, keep buffer)
SPLIT_FILE_SIZE = 1900  # MB per part

# YouTube Support
YOUTUBE_DLP_OPTS = {
    'format': 'best[height<=1080]',
    'no_warnings': True,
    'ignoreerrors': True,
    'extract_flat': False,
}

# Progress Update Settings
PROGRESS_UPDATE_INTERVAL = 0.5  # Seconds (faster updates)
UPLOAD_PROGRESS_INTERVAL = 2  # Seconds