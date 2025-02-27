
import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('function_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import our bot modules
from bot.scraper import InstagramReelDownloader
from bot.uploader import upload_with_retry

def test_instagram_login():
    """Test if we can login to Instagram"""
    logger.info("======= TESTING INSTAGRAM LOGIN =======")
    try:
        downloader = InstagramReelDownloader()
        # Test with a sample URL
        test_url = "https://www.instagram.com/reels/DBy6mQMoF13/"
        
        # Get credentials from the database - for testing only
        from app import app
        from models import User
        
        with app.app_context():
            # Get the first user
            user = User.query.first()
            if user and user.instagram_username:
                logger.info(f"Testing login with username: {user.instagram_username}")
                
                # Get the password (this would be the decrypted password in production)
                password = "test_password"  # You would need the actual password here
                
                # Test login by attempting to download a reel
                logger.info(f"Testing download with URL: {test_url}")
                video_path = downloader.download_reel(test_url)
                
                if video_path:
                    logger.info(f"Login successful! Downloaded file to: {video_path}")
                    return True, video_path
                else:
                    logger.error("Login failed or download failed")
                    return False, None
            else:
                logger.error("No user with Instagram credentials found in database")
                return False, None
    except Exception as e:
        logger.error(f"Error during login test: {str(e)}")
        return False, None

def test_video_processing(video_path):
    """Test video processing"""
    logger.info("======= TESTING VIDEO PROCESSING =======")
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False, None
            
        from bot.video_processor import process_video
        
        processed_path = process_video(video_path)
        if processed_path:
            logger.info(f"Processing successful! Processed file at: {processed_path}")
            return True, processed_path
        else:
            logger.error("Processing failed")
            return False, None
    except Exception as e:
        logger.error(f"Error during video processing test: {str(e)}")
        return False, None

def test_upload(processed_path):
    """Test video upload"""
    logger.info("======= TESTING VIDEO UPLOAD =======")
    try:
        if not os.path.exists(processed_path):
            logger.error(f"Processed video file not found: {processed_path}")
            return False
            
        caption = f"Test upload at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} #test"
        success = upload_with_retry(processed_path, caption)
        
        if success:
            logger.info("Upload successful!")
            return True
        else:
            logger.error("Upload failed")
            return False
    except Exception as e:
        logger.error(f"Error during upload test: {str(e)}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    logger.info("Starting complete function test")
    
    # Test login and download
    login_success, video_path = test_instagram_login()
    if not login_success:
        logger.error("Login/Download test failed. Aborting further tests.")
        return False
        
    # Test video processing
    processing_success, processed_path = test_video_processing(video_path)
    if not processing_success:
        logger.error("Video processing test failed. Aborting upload test.")
        return False
        
    # Test upload
    upload_success = test_upload(processed_path)
    
    overall_success = login_success and processing_success and upload_success
    logger.info(f"Test results: Login/Download: {login_success}, Processing: {processing_success}, Upload: {upload_success}")
    logger.info(f"Overall test {'successful' if overall_success else 'failed'}")
    
    return overall_success

if __name__ == "__main__":
    run_all_tests()
