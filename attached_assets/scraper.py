import logging
import os
import instaloader
from config import DOWNLOAD_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class InstagramReelDownloader:
    def __init__(self):
        self.loader = instaloader.Instaloader(download_videos=True, download_comments=False, save_metadata=False, dirname_pattern=DOWNLOAD_DIR)

    def download_reel(self, reel_url):
        try:
            logger.info(f"Downloading reel from URL: {reel_url}")

            # Extract shortcode from URL
            shortcode = reel_url.split('/')[-2]
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            self.loader.download_post(post, target=DOWNLOAD_DIR)
            logger.info(f"Downloaded reel with shortcode: {shortcode}")

            # Verify the actual saved file name
            actual_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.mp4')]
            if actual_files:
                actual_file_path = max([os.path.join(DOWNLOAD_DIR, f) for f in actual_files], key=os.path.getctime)
                logger.info(f"Actual downloaded file path: {actual_file_path}")
                return actual_file_path
            else:
                logger.error("No .mp4 files found in the downloads directory after download")
                return None
        except Exception as e:
            logger.error(f"Failed to download reel: {str(e)}")
            return None

# Example usage
if __name__ == "__main__":
    reel_urls = input("Enter the reel URLs separated by commas: ").split(',')

    downloader = InstagramReelDownloader()
    for reel_url in reel_urls:
        downloader.download_reel(reel_url.strip())