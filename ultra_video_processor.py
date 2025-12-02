import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional
from config import THUMBNAIL_TIME, THUMBNAIL_SIZE, THUMBNAIL_QUALITY

logger = logging.getLogger(__name__)


def get_video_info(filepath: str) -> Dict:
    """Get video duration and dimensions with enhanced error handling"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"FFprobe failed: {result.stderr}")
            return {'duration': 0, 'width': 1280, 'height': 720}
        
        data = json.loads(result.stdout)
        
        # Get duration from multiple sources
        duration = 0
        if 'format' in data and 'duration' in data['format']:
            duration = int(float(data['format']['duration']))
        
        # Get video stream
        video_stream = next(
            (s for s in data.get('streams', []) if s.get('codec_type') == 'video'), 
            {}
        )
        
        width = video_stream.get('width', 1280)
        height = video_stream.get('height', 720)
        
        # If no duration from format, try from stream
        if duration == 0 and 'duration' in video_stream:
            duration = int(float(video_stream['duration']))
        
        # Validate dimensions
        if width <= 0 or height <= 0:
            width, height = 1280, 720
        
        # Ensure dimensions are even (required by some codecs)
        width = width - (width % 2)
        height = height - (height % 2)
        
        logger.info(f"Video info: {width}x{height}, {duration}s")
        return {'duration': duration, 'width': width, 'height': height}
        
    except subprocess.TimeoutExpired:
        logger.error("FFprobe timeout")
        return {'duration': 0, 'width': 1280, 'height': 720}
    except json.JSONDecodeError as e:
        logger.error(f"FFprobe JSON error: {e}")
        return {'duration': 0, 'width': 1280, 'height': 720}
    except Exception as e:
        logger.error(f"FFprobe error: {e}")
        return {'duration': 0, 'width': 1280, 'height': 720}


def generate_thumbnail(video_path: str, thumb_path: str, video_duration: int = 0) -> bool:
    """
    Generate high-quality thumbnail from video with MULTIPLE fallback methods
    NEVER returns blank thumbnails!
    """
    try:
        # Determine best time for thumbnail
        if video_duration > 10:
            thumb_time = min(video_duration // 4, 15)  # 1/4 into video or 15s max
        elif video_duration > 5:
            thumb_time = 3
        else:
            thumb_time = 1
        
        # Method 1: Primary extraction at calculated time
        thumb_time_str = f"00:00:{thumb_time:02d}"
        
        cmd = [
            'ffmpeg', '-ss', thumb_time_str,
            '-i', video_path,
            '-vframes', '1',
            '-vf', f'scale={THUMBNAIL_SIZE}:force_original_aspect_ratio=decrease',
            '-q:v', str(THUMBNAIL_QUALITY),
            thumb_path,
            '-y'
        ]
        
        logger.info(f"Thumbnail Method 1: Extracting at {thumb_time_str}")
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
            logger.info(f"✅ Thumbnail Method 1 success: {os.path.getsize(thumb_path)} bytes")
            return True
        
        # Method 2: Try at 0 seconds
        logger.warning("Method 1 failed, trying Method 2 (0 seconds)")
        cmd[1] = '00:00:00'
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
            logger.info("✅ Thumbnail Method 2 success")
            return True
        
        # Method 3: Middle of video
        if video_duration > 5:
            mid_time = video_duration // 2
            mid_str = f"00:00:{mid_time:02d}"
            logger.warning(f"Method 2 failed, trying Method 3 (middle: {mid_str})")
            cmd[1] = mid_str
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
                logger.info("✅ Thumbnail Method 3 success")
                return True
        
        # Method 4: Simple extraction without seeking (most reliable)
        logger.warning("Method 3 failed, trying Method 4 (simple extraction)")
        simple_cmd = [
            'ffmpeg', '-i', video_path,
            '-vframes', '1',
            '-vf', f'scale={THUMBNAIL_SIZE}',
            '-q:v', '2',
            thumb_path,
            '-y'
        ]
        result = subprocess.run(simple_cmd, capture_output=True, timeout=60)
        
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
            logger.info("✅ Thumbnail Method 4 success")
            return True
        
        # Method 5: Extract ANY frame without filters
        logger.warning("Method 4 failed, trying Method 5 (raw extraction)")
        raw_cmd = [
            'ffmpeg', '-i', video_path,
            '-vframes', '1',
            thumb_path,
            '-y'
        ]
        result = subprocess.run(raw_cmd, capture_output=True, timeout=60)
        
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
            logger.info("✅ Thumbnail Method 5 success")
            return True
        
        # Method 6: Last resort - extract from end of video
        if video_duration > 10:
            end_time = max(video_duration - 5, 1)
            end_str = f"00:00:{end_time:02d}"
            logger.warning(f"Method 5 failed, trying Method 6 (end: {end_str})")
            cmd[1] = end_str
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 2048:
                logger.info("✅ Thumbnail Method 6 success")
                return True
        
        logger.error("❌ ALL thumbnail generation methods failed")
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("Thumbnail generation timeout")
        return False
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
        return False


def validate_video_file(filepath: str) -> bool:
    """Validate if video file is playable with enhanced checks"""
    try:
        if not os.path.exists(filepath):
            logger.error(f"File does not exist: {filepath}")
            return False
        
        file_size = os.path.getsize(filepath)
        if file_size < 10240:  # Less than 10KB
            logger.error(f"File too small: {file_size} bytes")
            return False
        
        # Quick validation with ffprobe
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'json',
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=15)
        
        if result.returncode != 0:
            logger.error(f"Video validation failed: {result.stderr.decode()}")
            return False
        
        # Check if video stream exists
        try:
            data = json.loads(result.stdout)
            if 'streams' in data and len(data['streams']) > 0:
                logger.info(f"✅ Video file validated: {filepath}")
                return True
        except:
            pass
        
        logger.error("No valid video stream found")
        return False
        
    except subprocess.TimeoutExpired:
        logger.error("Video validation timeout")
        return False
    except Exception as e:
        logger.error(f"Video validation error: {e}")
        return False


def get_video_codec_info(filepath: str) -> Dict:
    """Get detailed video codec information"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'v:0',
            filepath
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                return {
                    'codec': stream.get('codec_name', 'unknown'),
                    'profile': stream.get('profile', 'unknown'),
                    'bit_rate': stream.get('bit_rate', '0'),
                    'fps': eval(stream.get('r_frame_rate', '0/1'))
                }
        
        return {}
        
    except Exception as e:
        logger.error(f"Codec info error: {e}")
        return {}