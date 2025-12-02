import logging
import asyncio
from aiohttp import web
from pyrogram import Client, idle
from config import API_ID, API_HASH, BOT_TOKEN, PORT
from handlers import setup_handlers

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Suppress unnecessary logs
logging.getLogger('pyrogram').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

# Initialize bot client with ULTRA-OPTIMIZED settings
app = Client(
    "m3u8_ultra_speed_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=16,  # Doubled for parallel processing
    sleep_threshold=120,  # Increased for better connection stability
    max_concurrent_transmissions=10  # More concurrent uploads
)

# Web server for health checks and monitoring
web_app = web.Application()

async def health_check(request):
    return web.Response(
        text="✅ OK - M3U8 Bot ULTRA-SPEED Edition v9.0 Running!",
        content_type="text/plain"
    )

async def stats(request):
    stats_text = """
🚀 M3U8 Downloader Bot - ULTRA-SPEED Edition v9.0

⚡ FEATURES:
- 6-7x Faster Downloads
- Dynamic Worker Management
- Upload Progress Tracking
- Auto File Splitting (>1.9GB)
- YouTube Link Support
- Failed Link Handling
- Enhanced Thumbnails
- Parallel Processing

💪 STATUS: Active and Ready!
    """
    return web.Response(text=stats_text, content_type="text/plain")

async def root(request):
    return web.Response(
        text="🚀 M3U8 Bot ULTRA-SPEED Edition is running!",
        content_type="text/plain"
    )

web_app.router.add_get("/", root)
web_app.router.add_get("/health", health_check)
web_app.router.add_get("/stats", stats)


async def main():
    """Main bot initialization with enhanced error handling"""
    try:
        # Start web server
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"✅ Web server started on port {PORT}")
        logger.info(f"📊 Health check: http://0.0.0.0:{PORT}/health")
        logger.info(f"📈 Stats: http://0.0.0.0:{PORT}/stats")
        
        # Setup bot handlers
        setup_handlers(app)
        logger.info("✅ Bot handlers configured")
        
        # Start bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info("=" * 70)
        logger.info(f"🤖 Bot Started: @{me.username}")
        logger.info(f"📝 Bot Name: {me.first_name}")
        logger.info(f"🆔 Bot ID: {me.id}")
        logger.info("=" * 70)
        logger.info("🚀 ULTRA-SPEED Edition v9.0 - ACTIVE!")
        logger.info("=" * 70)
        logger.info("⚡ FEATURES ENABLED:")
        logger.info("   • 6-7x Faster Downloads")
        logger.info("   • Dynamic Worker Management (8-32 workers)")
        logger.info("   • Upload Progress Tracking")
        logger.info("   • Auto File Splitting (>1.9GB)")
        logger.info("   • YouTube Link Support")
        logger.info("   • Failed Link Handling")
        logger.info("   • Enhanced Thumbnail Generation (6 methods)")
        logger.info("   • Parallel Processing")
        logger.info("   • Adaptive Connection Pooling")
        logger.info("=" * 70)
        
        # Keep bot running
        await idle()
        
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}", exc_info=True)
        raise
    finally:
        try:
            await app.stop()
            logger.info("🛑 Bot stopped gracefully")
        except:
            pass


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("🚀 INITIALIZING M3U8 DOWNLOADER BOT")
    logger.info("⚡ ULTRA-SPEED EDITION v9.0")
    logger.info("=" * 70)
    logger.info("")
    logger.info("💪 PERFORMANCE ENHANCEMENTS:")
    logger.info("   ✓ 6-7x Download Speed Increase")
    logger.info("   ✓ Dynamic Worker Adjustment")
    logger.info("   ✓ Adaptive Connection Pooling")
    logger.info("   ✓ Enhanced Buffer Management")
    logger.info("   ✓ Real-time Progress Tracking")
    logger.info("")
    logger.info("🎯 NEW FEATURES:")
    logger.info("   ✓ Upload Progress Bars")
    logger.info("   ✓ Auto File Splitting")
    logger.info("   ✓ YouTube Link Support")
    logger.info("   ✓ Failed Link Handling")
    logger.info("   ✓ Enhanced Error Recovery")
    logger.info("")
    logger.info("=" * 70)
    
    try:
        app.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
    finally:
        logger.info("=" * 70)
        logger.info("👋 Bot shutdown complete")
        logger.info("=" * 70)