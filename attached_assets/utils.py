import os
import logging
import time
from config import DOWNLOAD_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('instagram_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def verify_file(file_path):
    """Verify if file exists and is not empty"""
    try:
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error(f"File is empty: {file_path}")
            return False

        if not file_path.lower().endswith(('.mp4', '.mov')):
            logger.error(f"Invalid file type: {file_path}")
            return False

        logger.info(f"Verified file {file_path} (size: {file_size:,} bytes)")
        return True

    except Exception as e:
        logger.error(f"Error verifying file {file_path}: {str(e)}")
        return False

def get_latest_download():
    files = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.mp4')]
    if not files:
        return None
    latest_file = max(files, key=os.path.getctime)
    return latest_file

def cleanup_old_files(max_age_hours=24):
    """Clean up old downloaded files"""
    try:
        if not os.path.exists(DOWNLOAD_DIR):
            logger.warning(f"Download directory {DOWNLOAD_DIR} does not exist")
            return

        current_time = time.time()
        total_removed = 0
        total_size_freed = 0

        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            try:
                if os.path.getctime(file_path) < (current_time - max_age_hours * 3600):
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    total_removed += 1
                    total_size_freed += file_size
                    logger.info(f"Removed old file: {filename}")
            except Exception as e:
                logger.error(f"Error removing file {filename}: {str(e)}")

        if total_removed > 0:
            logger.info(f"Cleanup completed: removed {total_removed} files")
        else:
            logger.info("No files needed cleanup")

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")