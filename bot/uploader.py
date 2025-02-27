
import os
import time
import logging
import pickle
from instagrapi import Client
from datetime import datetime

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

class InstagramUploader:
    def __init__(self):
        self.client = Client()
        
    def login(self, username, password, use_session=True):
        try:
            session_file = f"session_{username}.pkl"
            if use_session and os.path.exists(session_file):
                logger.info(f"Attempting to login with session settings for {username}...")
                with open(session_file, "rb") as f:
                    settings = pickle.load(f)
                    self.client.set_settings(settings)
                    self.client.login(username, password)
                logger.info("Logged in using session settings")
                return True
            else:
                logger.info(f"Attempting to login with username and password for {username}...")
                self.client.login(username, password)
                # Save session for future use
                with open(session_file, "wb") as f:
                    pickle.dump(self.client.get_settings(), f)
                logger.info("Login successful and session settings saved")
                return True
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    def upload_reel(self, video_path, caption):
        try:
            logger.info(f"Attempting to upload reel: {video_path}")
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
                
            media = self.client.clip_upload(video_path, caption)
            if media:
                logger.info(f"Successfully uploaded reel: {video_path}")
                logger.info(f"Media ID: {media.id}")
                return True
            else:
                logger.error("Upload returned None")
                return False
        except Exception as e:
            logger.error(f"Failed to upload reel: {str(e)}")
            return False

# Main upload function with retry logic
def upload_with_retry(video_path, caption, max_retries=3):
    """Upload with retry mechanism using instagrapi"""
    from app import app
    from models import User
    
    with app.app_context():
        # Get the user credentials
        user = User.query.first()
        if not user or not user.instagram_username:
            logger.error("No user with Instagram credentials found")
            return False
            
        # Decrypt the password - in a real app, you'd use a proper decryption method
        # Here we're assuming the password is stored in plaintext for simplicity
        # YOU SHOULD USE PROPER ENCRYPTION IN PRODUCTION
        from werkzeug.security import check_password_hash
        instagram_password = "PASSWORD_NOT_AVAILABLE"  # This won't work - need actual password
        
        logger.info(f"Starting upload with user: {user.instagram_username}")

        # Create uploader and login
        uploader = InstagramUploader()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Upload attempt {attempt + 1}/{max_retries}")
                
                # Login first
                if not uploader.login(user.instagram_username, instagram_password):
                    logger.error("Failed to login to Instagram")
                    if attempt < max_retries - 1:
                        time.sleep(30)  # Wait before retry
                    continue
                
                # Then upload
                if uploader.upload_reel(video_path, caption):
                    logger.info("Upload successful!")
                    return True
                
            except Exception as e:
                logger.error(f"Upload attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info("Waiting 60 seconds before retry...")
                time.sleep(60)
        
        logger.error(f"All {max_retries} upload attempts failed")
        return False
