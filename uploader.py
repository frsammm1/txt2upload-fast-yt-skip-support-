import os
import asyncio
import logging
import time
from typing import Optional, List
from pyrogram import Client
from pyrogram.types import Message
from utils import format_size, format_time, create_progress_bar, split_large_file
from config import UPLOAD_CHUNK_SIZE, MAX_FILE_SIZE, UPLOAD_PROGRESS_INTERVAL

logger = logging.getLogger(__name__)


class UploadProgressTracker:
    """Enhanced upload progress tracker with better display"""
    
    def __init__(self, progress_msg: Message, filename: str, part_num: int = 0, total_parts: int = 1):
        self.progress_msg = progress_msg
        self.filename = filename
        self.part_num = part_num
        self.total_parts = total_parts
        self.last_update = 0
        self.start_time = time.time()
        self.last_percent = -1
        self.speeds = []
    
    async def progress_callback(self, current: int, total: int):
        """Callback for upload progress with enhanced display"""
        try:
            now = time.time()
            
            # Update at intervals for performance
            if now - self.last_update < UPLOAD_PROGRESS_INTERVAL:
                return
            
            percent = (current / total) * 100 if total > 0 else 0
            
            # Update if significant change
            if abs(int(percent) - self.last_percent) >= 2:
                self.last_percent = int(percent)
                self.last_update = now
                
                elapsed = now - self.start_time
                speed = current / elapsed if elapsed > 0 else 0
                
                # Track speed history for average
                self.speeds.append(speed)
                if len(self.speeds) > 10:
                    self.speeds.pop(0)
                
                avg_speed = sum(self.speeds) / len(self.speeds)
                eta = int((total - current) / avg_speed) if avg_speed > 0 else 0
                
                bar = create_progress_bar(percent)
                
                part_info = ""
                if self.total_parts > 1:
                    part_info = f"📊 Part {self.part_num}/{self.total_parts}\n"
                
                await self.progress_msg.edit_text(
                    f"📤 **UPLOADING TO TELEGRAM**\n\n"
                    f"{part_info}"
                    f"{bar}\n\n"
                    f"📦 {format_size(current)} / {format_size(total)}\n"
                    f"🚀 Speed: {format_size(int(avg_speed))}/s\n"
                    f"⏱️ ETA: {format_time(eta)}"
                )
        except Exception as e:
            logger.debug(f"Upload progress error: {e}")


async def upload_video(
    client: Client,
    chat_id: int,
    video_path: str,
    caption: str,
    progress_msg: Message,
    thumb_path: Optional[str] = None,
    duration: int = 0,
    width: int = 1280,
    height: int = 720
) -> bool:
    """Upload video with progress tracking and auto-splitting for large files"""
    try:
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        
        # Check if file needs splitting
        if file_size_mb > MAX_FILE_SIZE:
            logger.info(f"File too large ({file_size_mb:.1f}MB), splitting...")
            await progress_msg.edit_text(
                f"📦 **Large File Detected!**\n\n"
                f"Size: {file_size_mb:.1f}MB\n"
                f"Splitting into parts..."
            )
            
            # Split file
            parts = await split_large_file(video_path, MAX_FILE_SIZE)
            
            if not parts:
                logger.error("File splitting failed")
                return False
            
            # Upload all parts
            for i, part_path in enumerate(parts, 1):
                if not os.path.exists(part_path):
                    continue
                
                part_caption = f"{caption}\n\n📦 Part {i}/{len(parts)}"
                tracker = UploadProgressTracker(progress_msg, os.path.basename(part_path), i, len(parts))
                
                try:
                    await client.send_video(
                        chat_id=chat_id,
                        video=part_path,
                        caption=part_caption,
                        supports_streaming=True,
                        duration=duration if i == 1 else 0,
                        width=width if i == 1 else 0,
                        height=height if i == 1 else 0,
                        thumb=thumb_path if i == 1 else None,
                        progress=tracker.progress_callback
                    )
                    
                    logger.info(f"Part {i}/{len(parts)} uploaded successfully")
                except Exception as e:
                    logger.error(f"Part {i} upload failed: {e}")
                    return False
                finally:
                    # Cleanup part file
                    try:
                        os.remove(part_path)
                    except:
                        pass
            
            return True
        
        # Normal upload for files under limit
        tracker = UploadProgressTracker(progress_msg, os.path.basename(video_path))
        
        await client.send_video(
            chat_id=chat_id,
            video=video_path,
            caption=caption,
            supports_streaming=True,
            duration=duration,
            width=width,
            height=height,
            thumb=thumb_path,
            progress=tracker.progress_callback
        )
        
        logger.info(f"Video uploaded: {video_path}")
        return True
        
    except Exception as e:
        logger.error(f"Video upload error: {e}")
        return False


async def upload_photo(
    client: Client,
    chat_id: int,
    photo_path: str,
    caption: str,
    progress_msg: Message
) -> bool:
    """Upload photo with progress tracking"""
    try:
        tracker = UploadProgressTracker(progress_msg, os.path.basename(photo_path))
        
        await client.send_photo(
            chat_id=chat_id,
            photo=photo_path,
            caption=caption,
            progress=tracker.progress_callback
        )
        
        logger.info(f"Photo uploaded: {photo_path}")
        return True
        
    except Exception as e:
        logger.error(f"Photo upload error: {e}")
        return False


async def upload_document(
    client: Client,
    chat_id: int,
    document_path: str,
    caption: str,
    progress_msg: Message
) -> bool:
    """Upload document with progress tracking and auto-splitting"""
    try:
        file_size_mb = os.path.getsize(document_path) / (1024 * 1024)
        
        # Check if file needs splitting
        if file_size_mb > MAX_FILE_SIZE:
            logger.info(f"Document too large ({file_size_mb:.1f}MB), splitting...")
            await progress_msg.edit_text(
                f"📦 **Large Document Detected!**\n\n"
                f"Size: {file_size_mb:.1f}MB\n"
                f"Splitting into parts..."
            )
            
            # Split file
            parts = await split_large_file(document_path, MAX_FILE_SIZE)
            
            if not parts:
                logger.error("Document splitting failed")
                return False
            
            # Upload all parts
            for i, part_path in enumerate(parts, 1):
                if not os.path.exists(part_path):
                    continue
                
                part_caption = f"{caption}\n\n📦 Part {i}/{len(parts)}"
                tracker = UploadProgressTracker(progress_msg, os.path.basename(part_path), i, len(parts))
                
                try:
                    await client.send_document(
                        chat_id=chat_id,
                        document=part_path,
                        caption=part_caption,
                        progress=tracker.progress_callback
                    )
                    
                    logger.info(f"Document part {i}/{len(parts)} uploaded successfully")
                except Exception as e:
                    logger.error(f"Document part {i} upload failed: {e}")
                    return False
                finally:
                    # Cleanup part file
                    try:
                        os.remove(part_path)
                    except:
                        pass
            
            return True
        
        # Normal upload for files under limit
        tracker = UploadProgressTracker(progress_msg, os.path.basename(document_path))
        
        await client.send_document(
            chat_id=chat_id,
            document=document_path,
            caption=caption,
            progress=tracker.progress_callback
        )
        
        logger.info(f"Document uploaded: {document_path}")
        return True
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        return False


async def send_failed_link(
    client: Client,
    chat_id: int,
    title: str,
    url: str,
    serial_num: int,
    reason: str = "Download failed"
) -> bool:
    """Send failed link information to user"""
    try:
        message = (
            f"❌ **{reason}**\n\n"
            f"📝 Item #{serial_num}\n"
            f"🏷️ Title: {title}\n\n"
            f"🔗 **Link:**\n{url}\n\n"
            f"💡 You can open this link manually to check the content."
        )
        
        await client.send_message(
            chat_id=chat_id,
            text=message,
            disable_web_page_preview=False
        )
        
        logger.info(f"Failed link sent for item #{serial_num}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send link info: {e}")
        return False
