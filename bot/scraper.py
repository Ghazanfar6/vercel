
import os
import logging
import instaloader

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
        self.loader = instaloader.Instaloader(
            download_videos=True, 
            download_comments=False, 
            save_metadata=False, 
            dirname_pattern="downloads"
        )
    
    def download_reel(self, reel_url, username=None, password=None):
        try:
            logger.info(f"Downloading reel from URL: {reel_url}")
            
            # Login if credentials provided
            if username and password:
                try:
                    logger.info(f"Logging in as {username}")
                    self.loader.login(username, password)
                except Exception as e:
                    logger.error(f"Login failed: {str(e)}")
                    # Continue without login

            # Extract shortcode from URL
            shortcode = reel_url.split('/')[-2]
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            self.loader.download_post(post, target="downloads")
            logger.info(f"Downloaded reel with shortcode: {shortcode}")

            # Verify the actual saved file name
            download_dir = "downloads"
            actual_files = [f for f in os.listdir(download_dir) if f.endswith('.mp4')]
            if actual_files:
                actual_file_path = max([os.path.join(download_dir, f) for f in actual_files], key=os.path.getctime)
                logger.info(f"Actual downloaded file path: {actual_file_path}")
                return actual_file_path
            else:
                logger.error("No .mp4 files found in the downloads directory after download")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download reel: {str(e)}")
            return None
