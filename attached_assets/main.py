import logging
import os
import time
import random
from datetime import datetime
from scraper import InstagramReelDownloader
from uploader import upload_with_retry
from config import PROCESSED_VIDEO_DIR, DOWNLOAD_DIR, generate_caption
from video_processor import process_video

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_latest_file_in_directory(directory: str) -> str:
    """Get the latest file in the specified directory"""
    files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    latest_file = max(files, key=os.path.getctime)
    return latest_file

def clean_downloads_folder(directory: str):
    """Delete all files in the specified directory"""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")

def process_single_reel(reel_url: str) -> bool:
    """Process a single reel: download and repost"""
    try:
        logger.info(f"Downloading reel from URL: {reel_url}")
        downloader = InstagramReelDownloader()
        video_path = downloader.download_reel(reel_url.strip())
        if not video_path:
            logger.error("Failed to download reel")
            return False

        # Process the downloaded video
        logo_path = "C:/Users/Ghazanfar/Desktop/InstagramReelSync/llr.png"  # Update this path to your logo file
        processed_video_path = process_video(video_path, logo_path)

        if not processed_video_path:
            logger.error("Failed to process video")
            return False

        # Generate a new caption
        caption = generate_caption()

        logger.info(f"Uploading file: {processed_video_path} with caption: {caption}")
        success = upload_with_retry(processed_video_path, caption)
        logger.info("Completed" if success else "Failed")
        
        # Clean the downloads folder after uploading
        clean_downloads_folder(DOWNLOAD_DIR)
        
        return success

    except Exception as e:
        logger.error(f"Error processing reel: {str(e)}")
        return False

def run_bot():
    """Main bot execution function"""
    logger.info("Starting Instagram Reel Bot")

    reel_urls = []
    print("Enter the reel URLs separated by newlines (press Enter twice to finish):")
    while True:
        url = input()
        if url == "":
            break
        reel_urls.append(url)

    while reel_urls:
        try:
            logger.info(f"Starting automation cycle at {datetime.now()}")

            current_url = reel_urls.pop(0)
            success = process_single_reel(current_url)

            status = "Successfully" if success else "Failed to"
            logger.info(f"{status} complete automation cycle")

            # Calculate next run time (random interval within 60 to 70 minutes)
            delay = random.randint(3600, 4800)  # 60 to 70 minutes in seconds
            next_run = datetime.fromtimestamp(time.time() + delay)
            logger.info(f"Next run scheduled for: {next_run}")

            # Sleep until next run
            time.sleep(delay)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Critical error in main loop: {str(e)}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == "__main__":
    run_bot()