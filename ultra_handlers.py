import os
import asyncio
import aiofiles
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import DOWNLOAD_DIR, QUALITY_MAP
from utils import parse_content, sanitize_filename, is_youtube_url, create_failed_link_file
from video_processor import get_video_info, generate_thumbnail, validate_video_file
from downloader import download_video, download_file
from uploader import upload_video, upload_photo, upload_document, send_failed_link

logger = logging.getLogger(__name__)

# Global state
user_data = {}
active_downloads = {}
download_progress = {}


def setup_handlers(app: Client):
    """Setup all bot handlers"""
    
    @app.on_message(filters.command("start"))
    async def start_cmd(client: Client, message: Message):
        await message.reply_text(
            "🚀 **M3U8 Downloader Bot - ULTRA SPEED Edition v9.0**\n\n"
            "⚡ **SUPERCHARGED Features:**\n"
            "🔥 6-7x Faster Downloads (Dynamic Workers)\n"
            "📊 Real-time Upload Progress Bars\n"
            "📦 Auto File Splitting (>1.9GB files)\n"
            "🎯 Smart Range Selection\n"
            "🔢 Auto Serial Numbering\n"
            "💪 Parallel Processing (Up to 32 workers)\n"
            "🎬 YouTube Link Support\n"
            "❌ Failed Link Handling\n\n"
            "🎥 **Supported Formats:**\n"
            "• Videos: M3U8, MPD, MP4, MKV, AVI, MOV, FLV, WEBM, TS\n"
            "• Images: PNG, JPG, GIF, WEBP, BMP, SVG\n"
            "• Documents: PDF, DOC, DOCX, TXT, ZIP, RAR\n\n"
            "🖼️ **Enhanced Features:**\n"
            "• Never Blank Thumbnails (4 fallback methods)\n"
            "• Accurate Duration Tracking\n"
            "• Live Speed Monitoring\n"
            "• Dynamic Worker Adjustment\n"
            "• Robust Error Recovery\n\n"
            "📝 **Send TXT/HTML file to begin!**\n"
            "🚀 Powered by ULTRA-SPEED Engine!"
        )
    
    
    @app.on_message(filters.document)
    async def handle_doc(client: Client, message: Message):
        user_id = message.from_user.id
        file_name = message.document.file_name
        
        if not (file_name.endswith('.txt') or file_name.endswith('.html')):
            await message.reply_text("❌ Please send TXT or HTML file only!")
            return
        
        status = await message.reply_text("📥 Processing your file...")
        
        try:
            file_path = await message.download(file_name=f"{DOWNLOAD_DIR}/{user_id}_{file_name}")
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            items = parse_content(content)
            
            if not items:
                await status.edit_text("❌ No supported links found in file!")
                os.remove(file_path)
                return
            
            # Count by type
            type_counts = {}
            for item in items:
                ftype = item['type']
                type_counts[ftype] = type_counts.get(ftype, 0) + 1
            
            user_data[user_id] = {'items': items, 'file_path': file_path}
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Select Range", callback_data="select_range")],
                [InlineKeyboardButton("⬇️ Download All", callback_data="download_all")]
            ])
            
            type_info = "\n".join([
                f"{'🎬' if t == 'video' else '🖼️' if t == 'image' else '📄'} {t.title()}s: {c}" 
                for t, c in type_counts.items()
            ])
            
            await status.edit_text(
                f"✅ **Content Detected Successfully!**\n\n"
                f"{type_info}\n"
                f"📦 Total Items: {len(items)}\n\n"
                f"🚀 ULTRA-SPEED Engine Ready!\n"
                f"Choose your action:",
                reply_markup=kb
            )
            
        except Exception as e:
            logger.error(f"Document processing error: {e}")
            await status.edit_text(f"❌ Error processing file: {str(e)[:100]}")
    
    
    @app.on_callback_query(filters.regex(r"^(select_range|download_all)$"))
    async def range_select(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        action = callback.data
        
        if user_id not in user_data:
            await callback.answer("❌ Session expired! Send file again.", show_alert=True)
            return
        
        items = user_data[user_id]['items']
        
        if action == "download_all":
            user_data[user_id]['range'] = (1, len(items))
            
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("360p", callback_data="q_360p"),
                    InlineKeyboardButton("480p", callback_data="q_480p")
                ],
                [
                    InlineKeyboardButton("720p ⭐", callback_data="q_720p"),
                    InlineKeyboardButton("1080p 🔥", callback_data="q_1080p")
                ]
            ])
            
            await callback.message.edit_text(
                f"📦 **Downloading All {len(items)} Items**\n\n"
                f"🎬 Select video quality:\n"
                f"(Images & documents process automatically)\n\n"
                f"⚡ ULTRA-SPEED mode activated!",
                reply_markup=kb
            )
        else:
            await callback.message.edit_text(
                f"📊 **Range Selection Mode**\n\n"
                f"Total available: {len(items)} items\n\n"
                f"📝 Send range in format:\n"
                f"• `start-end` (e.g., `1-10`)\n"
                f"• `number` (e.g., `5` for single item)\n\n"
                f"**Examples:**\n"
                f"✓ `1-50` → Items 1 to 50\n"
                f"✓ `10-20` → Items 10 to 20\n"
                f"✓ `15` → Only item 15\n\n"
                f"⏳ Waiting for your input..."
            )
    
    
    @app.on_message(filters.text & filters.private)
    async def handle_range(client: Client, message: Message):
        user_id = message.from_user.id
        
        if user_id not in user_data or 'range' in user_data[user_id]:
            return
        
        text = message.text.strip()
        items = user_data[user_id]['items']
        
        try:
            if '-' in text:
                start, end = map(int, text.split('-'))
            else:
                start = end = int(text)
            
            if start < 1 or end > len(items) or start > end:
                await message.reply_text(
                    f"❌ **Invalid Range!**\n\n"
                    f"Valid: 1-{len(items)}\n"
                    f"Please send correct range."
                )
                return
            
            user_data[user_id]['range'] = (start, end)
            
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("360p", callback_data="q_360p"),
                    InlineKeyboardButton("480p", callback_data="q_480p")
                ],
                [
                    InlineKeyboardButton("720p ⭐", callback_data="q_720p"),
                    InlineKeyboardButton("1080p 🔥", callback_data="q_1080p")
                ]
            ])
            
            count = end - start + 1
            await message.reply_text(
                f"✅ **Range Confirmed!**\n\n"
                f"📊 Range: {start}-{end}\n"
                f"📦 Total: {count} item(s)\n\n"
                f"🎬 Select video quality:\n"
                f"⚡ ULTRA-SPEED ready!",
                reply_markup=kb
            )
            
        except Exception as e:
            await message.reply_text(
                f"❌ **Invalid Format!**\n\n"
                f"Use:\n"
                f"• `start-end` (e.g., `1-10`)\n"
                f"• `number` (e.g., `5`)"
            )
    
    
    @app.on_callback_query(filters.regex(r"^q_"))
    async def quality_cb(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        quality = callback.data.split("_")[1]
        
        if user_id not in user_data or 'range' not in user_data[user_id]:
            await callback.answer("❌ Session expired!", show_alert=True)
            return
        
        items = user_data[user_id]['items']
        file_path = user_data[user_id]['file_path']
        start, end = user_data[user_id]['range']
        
        selected_items = items[start-1:end]
        active_downloads[user_id] = True
        
        stop_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("⛔ Stop All", callback_data="stop")
        ]])
        
        await callback.message.edit_text(
            f"🚀 **ULTRA-SPEED Batch Download Started!**\n\n"
            f"⚡ Quality: {quality}\n"
            f"📊 Range: {start}-{end}\n"
            f"📦 Total: {len(selected_items)} items\n"
            f"💪 Dynamic Workers: Active\n"
            f"📈 Auto File Splitting: Enabled\n\n"
            f"⏳ Processing at maximum speed...",
            reply_markup=stop_kb
        )
        
        # Process batch
        await process_batch(
            client, callback.message, selected_items, 
            quality, start, end, user_id
        )
        
        # Cleanup
        cleanup_user_data(user_id, file_path)
    
    
    @app.on_callback_query(filters.regex("^stop$"))
    async def stop_cb(client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        active_downloads[user_id] = False
        await callback.answer("⛔ Stopping all downloads...", show_alert=True)
    
    
    @app.on_message(filters.command("cancel"))
    async def cancel_cmd(client: Client, message: Message):
        user_id = message.from_user.id
        active_downloads[user_id] = False
        await message.reply_text("⛔ All downloads cancelled!")


async def process_batch(
    client: Client,
    message: Message,
    items: list,
    quality: str,
    start: int,
    end: int,
    user_id: int
):
    """Process batch of downloads with ULTRA-ENHANCED speed and error handling"""
    success = 0
    failed = 0
    youtube_links = 0
    
    for idx, item in enumerate(items, start):
        if not active_downloads.get(user_id, False):
            await message.reply_text("⛔ **Download stopped by user!**")
            break
        
        prog = await message.reply_text(
            f"📦 **Processing Item {idx}/{end}**\n"
            f"📝 {item['title'][:60]}...\n"
            f"🚀 ULTRA-SPEED mode active"
        )
        
        try:
            serial_caption = f"{idx}. {item['title']}"
            
            # Check if YouTube link
            if is_youtube_url(item['url']):
                logger.info(f"YouTube link detected: {item['url']}")
                await prog.edit_text(
                    f"🎬 YouTube video detected!\n"
                    f"Sending link for manual access..."
                )
                
                # Send as failed link with caption
                await send_failed_link(
                    client, message.chat.id, item['title'], 
                    item['url'], idx, "YouTube video - Open link manually"
                )
                youtube_links += 1
                await prog.delete()
                continue
            
            if item['type'] == 'video':
                result = await process_video(
                    client, message, item, quality, 
                    serial_caption, idx, prog, user_id
                )
                if result == 'UNSUPPORTED':
                    # Send failed link
                    await send_failed_link(
                        client, message.chat.id, item['title'],
                        item['url'], idx, "Unsupported video format"
                    )
                    failed += 1
                elif result:
                    success += 1
                else:
                    failed += 1
                    
            elif item['type'] == 'image':
                result = await process_image(
                    client, message, item, 
                    serial_caption, idx, prog, user_id
                )
                if result:
                    success += 1
                else:
                    # Send failed link
                    await send_failed_link(
                        client, message.chat.id, item['title'],
                        item['url'], idx, "Image download failed"
                    )
                    failed += 1
                    
            elif item['type'] == 'document':
                result = await process_document(
                    client, message, item,
                    serial_caption, idx, prog, user_id
                )
                if result:
                    success += 1
                else:
                    # Send failed link
                    await send_failed_link(
                        client, message.chat.id, item['title'],
                        item['url'], idx, "Document download failed"
                    )
                    failed += 1
        
        except Exception as e:
            logger.error(f"Item {idx} error: {e}")
            try:
                await prog.delete()
                # Send failed link on exception
                await send_failed_link(
                    client, message.chat.id, item['title'],
                    item['url'], idx, f"Error: {str(e)[:50]}"
                )
            except:
                pass
            failed += 1
        
        await asyncio.sleep(0.3)  # Reduced delay for faster processing
    
    # Final summary
    summary_msg = (
        f"✅ **ULTRA-SPEED Batch Complete!**\n\n"
        f"✔️ Success: {success}\n"
        f"❌ Failed: {failed}\n"
    )
    
    if youtube_links > 0:
        summary_msg += f"🎬 YouTube Links: {youtube_links}\n"
    
    summary_msg += (
        f"📊 Total: {len(items)}\n"
        f"📍 Range: {start}-{end}\n\n"
        f"🚀 Powered by ULTRA-SPEED Engine!\n"
        f"💪 Dynamic workers delivered maximum performance!"
    )
    
    await message.reply_text(summary_msg)


async def process_video(
    client: Client,
    message: Message,
    item: dict,
    quality: str,
    caption: str,
    idx: int,
    prog: Message,
    user_id: int
) -> bool:
    """Process video download and upload with enhanced error handling"""
    try:
        q_val = QUALITY_MAP[quality]
        safe = sanitize_filename(item['title'])
        fname = f"{safe}_{idx}.mp4"
        
        vpath = await download_video(
            item['url'], q_val, fname, prog, 
            user_id, active_downloads, download_progress
        )
        
        # Check for unsupported video
        if vpath == 'UNSUPPORTED':
            logger.warning(f"Unsupported video format: {item['url']}")
            await prog.delete()
            return 'UNSUPPORTED'
        
        if not vpath or not active_downloads.get(user_id, False):
            await prog.delete()
            return False
        
        if not os.path.exists(vpath) or not validate_video_file(vpath):
            await prog.delete()
            return False
        
        # Get video info
        await prog.edit_text("🎬 Analyzing video...")
        video_info = get_video_info(vpath)
        
        # Generate thumbnail with multiple attempts
        thumb_path = str(DOWNLOAD_DIR / f"thumb_{user_id}_{idx}.jpg")
        has_thumb = generate_thumbnail(vpath, thumb_path, video_info['duration'])
        
        if not has_thumb:
            logger.warning(f"Thumbnail generation failed for {vpath}, retrying...")
            await asyncio.sleep(1)
            has_thumb = generate_thumbnail(vpath, thumb_path, video_info['duration'])
        
        # Upload
        fsize = os.path.getsize(vpath) / (1024 * 1024)
        upload_caption = f"🎬 {caption}\n⚡ {quality} | 💾 {fsize:.1f}MB"
        
        if fsize > 1990:
            upload_caption += f"\n📦 Large file - Will be split automatically"
        
        await prog.edit_text("📤 Starting upload with progress tracking...")
        
        upload_success = await upload_video(
            client, message.chat.id, vpath, upload_caption,
            prog, thumb_path if has_thumb else None,
            video_info['duration'], video_info['width'], video_info['height']
        )
        
        # Cleanup
        try:
            os.remove(vpath)
            if has_thumb and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except:
            pass
        
        await prog.delete()
        return upload_success
        
    except Exception as e:
        logger.error(f"Video processing error: {e}")
        return False


async def process_image(
    client: Client,
    message: Message,
    item: dict,
    caption: str,
    idx: int,
    prog: Message,
    user_id: int
) -> bool:
    """Process image download and upload"""
    try:
        safe = sanitize_filename(item['title'])
        ext = os.path.splitext(item['url'])[1] or '.jpg'
        fname = f"{safe}_{idx}{ext}"
        
        ipath = await download_file(item['url'], fname, prog, user_id, active_downloads)
        
        if not ipath or not active_downloads.get(user_id, False):
            await prog.delete()
            return False
        
        if not os.path.exists(ipath):
            await prog.delete()
            return False
        
        await prog.edit_text("📤 Uploading image with progress...")
        
        upload_success = await upload_photo(
            client, message.chat.id, ipath, 
            f"🖼️ {caption}", prog
        )
        
        try:
            os.remove(ipath)
        except:
            pass
        
        await prog.delete()
        return upload_success
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return False


async def process_document(
    client: Client,
    message: Message,
    item: dict,
    caption: str,
    idx: int,
    prog: Message,
    user_id: int
) -> bool:
    """Process document download and upload"""
    try:
        safe = sanitize_filename(item['title'])
        ext = os.path.splitext(item['url'])[1] or '.pdf'
        fname = f"{safe}_{idx}{ext}"
        
        dpath = await download_file(item['url'], fname, prog, user_id, active_downloads)
        
        if not dpath or not active_downloads.get(user_id, False):
            await prog.delete()
            return False
        
        if not os.path.exists(dpath):
            await prog.delete()
            return False
        
        await prog.edit_text("📤 Uploading document with progress...")
        
        upload_success = await upload_document(
            client, message.chat.id, dpath,
            f"📄 {caption}", prog
        )
        
        try:
            os.remove(dpath)
        except:
            pass
        
        await prog.delete()
        return upload_success
        
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        return False


def cleanup_user_data(user_id: int, file_path: str):
    """Cleanup user data and temp files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass
    
    # Remove temp files
    for pattern in [f"temp_{user_id}_*", f"thumb_{user_id}_*", f"*_part*"]:
        for tf in DOWNLOAD_DIR.glob(pattern):
            try:
                os.remove(tf)
            except:
                pass
    
    # Clear user data
    if user_id in user_data:
        del user_data[user_id]
    if user_id in active_downloads:
        del active_downloads[user_id]
    if user_id in download_progress:
        del download_progress[user_id]