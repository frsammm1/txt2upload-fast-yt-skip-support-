import re
import os
import asyncio
import logging
from typing import List, Dict
from pathlib import Path
from config import SUPPORTED_TYPES, SPLIT_FILE_SIZE

logger = logging.getLogger(__name__)


def get_file_type(url: str) -> str:
    """Determine file type from URL with enhanced detection"""
    url_lower = url.lower()
    
    # Check for YouTube links
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'video'
    
    for ftype, extensions in SUPPORTED_TYPES.items():
        if any(ext in url_lower for ext in extensions):
            return ftype
    
    return 'unknown'


def parse_content(text: str) -> List[Dict]:
    """Parse content and identify all supported file types"""
    lines = text.strip().split('\n')
    items = []
    
    for line in lines:
        if ':' in line and ('http://' in line or 'https://' in line):
            parts = line.split(':', 1)
            if len(parts) == 2:
                title = parts[0].strip()
                url = parts[1].strip()
                
                file_type = get_file_type(url)
                
                if file_type != 'unknown':
                    items.append({
                        'title': title, 
                        'url': url, 
                        'type': file_type
                    })
    
    return items


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable size"""
    if bytes_size < 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def format_time(seconds: int) -> str:
    """Format seconds to human readable time"""
    if seconds < 0:
        return "0s"
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def sanitize_filename(filename: str, max_length: int = 50) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    safe = re.sub(r'[^\w\s-]', '', filename)
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    # Truncate if too long
    return safe[:max_length].strip('_')


def create_progress_bar(percent: float, length: int = 20) -> str:
    """Create a visual progress bar with enhanced design"""
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {percent:.1f}%"


async def split_large_file(file_path: str, max_size_mb: int) -> List[str]:
    """Split large file into smaller parts for Telegram upload"""
    try:
        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            return [file_path]
        
        # Calculate number of parts needed
        chunk_size = int(max_size_mb * 1024 * 1024)
        num_parts = (file_size + chunk_size - 1) // chunk_size
        
        logger.info(f"Splitting {file_path} into {num_parts} parts")
        
        base_name = os.path.basename(file_path)
        name, ext = os.path.splitext(base_name)
        dir_path = os.path.dirname(file_path)
        
        parts = []
        
        # Read and split file
        with open(file_path, 'rb') as source:
            for i in range(num_parts):
                part_name = f"{name}_part{i+1:03d}{ext}"
                part_path = os.path.join(dir_path, part_name)
                
                with open(part_path, 'wb') as part:
                    data = source.read(chunk_size)
                    if data:
                        part.write(data)
                        parts.append(part_path)
                        logger.info(f"Created part: {part_name} ({len(data)} bytes)")
        
        logger.info(f"File split into {len(parts)} parts successfully")
        return parts
        
    except Exception as e:
        logger.error(f"File splitting error: {e}")
        return []


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video"""
    youtube_patterns = [
        r'youtube\.com/watch\?v=',
        r'youtu\.be/',
        r'youtube\.com/embed/',
        r'youtube\.com/v/',
    ]
    
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return ""


async def create_failed_link_file(title: str, url: str, serial_num: int, reason: str = "Download failed") -> str:
    """Create a text file with failed link information"""
    try:
        from config import DOWNLOAD_DIR
        
        safe_title = sanitize_filename(title)
        file_name = f"failed_link_{serial_num}_{safe_title}.txt"
        file_path = DOWNLOAD_DIR / file_name
        
        content = f"""
═══════════════════════════════════════
   DOWNLOAD FAILED - LINK INFORMATION
═══════════════════════════════════════

Item Number: #{serial_num}
Title: {title}

Reason: {reason}

Original Link:
{url}

═══════════════════════════════════════
You can copy and open this link manually
to access the content.
═══════════════════════════════════════
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content.strip())
        
        return str(file_path)
        
    except Exception as e:
        logger.error(f"Failed to create link file: {e}")
        return ""


def get_video_extension(url: str) -> str:
    """Get appropriate video extension from URL"""
    url_lower = url.lower()
    
    if '.m3u8' in url_lower or '/m3u8' in url_lower:
        return '.mp4'
    elif '.mpd' in url_lower:
        return '.mp4'
    elif '.mkv' in url_lower:
        return '.mkv'
    elif '.webm' in url_lower:
        return '.webm'
    else:
        return '.mp4'  # Default


def estimate_download_time(file_size_mb: float, speed_mbps: float) -> int:
    """Estimate download time in seconds"""
    if speed_mbps <= 0:
        return 0
    
    # Convert speed from MB/s to Mbps
    time_seconds = (file_size_mb * 8) / speed_mbps
    return int(time_seconds)
