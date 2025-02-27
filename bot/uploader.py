import logging
import os
import time
import pickle
from instagrapi import Client
from config import (
    INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, 
    MAX_RETRIES, DOWNLOAD_DIR, generate_caption
)

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

    def login(self, use_session=True):
        try:
            if use_session and os.path.exists("session_settings.pkl"):
                logger.info("Attempting to login with session settings...")
                with open("session_settings.pkl", "rb") as f:
                    settings = pickle.load(f)
                    self.client.set_settings(settings)
                logger.info("Logged in using session settings")
                return True
            else:
                logger.info("Attempting to login with username and password...")
                self.client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                with open("session_settings.pkl", "wb") as f:
                    pickle.dump(self.client.get_settings(), f)
                logger.info("Login successful and session settings saved")
                return True
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    def upload_reel(self, video_path: str, caption: str) -> bool:
        try:
            logger.info(f"Attempting to upload reel: {video_path}")
            self.client.clip_upload(video_path, caption)
            logger.info(f"Successfully uploaded reel: {video_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload reel: {str(e)}")
            return False

def upload_with_retry(video_path, caption):
    """Upload with retry mechanism"""
    uploader = InstagramUploader()
    if not uploader.login():
        raise Exception("Failed to login")

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Upload attempt {attempt + 1}/{MAX_RETRIES}")
            if not os.path.exists(video_path):
                logger.error(f"File not found: {video_path}")
                return False
            logger.info(f"Uploading file: {video_path}")
            if uploader.upload_reel(video_path, caption):
                return True
        except Exception as e:
            logger.error(f"Upload attempt {attempt + 1} failed: {str(e)}")
            if "login_required" in str(e).lower() or "403" in str(e):
                logger.info("Re-attempting login with username and password...")
                if not uploader.login(use_session=False):
                    raise Exception("Failed to login with username and password")

        if attempt < MAX_RETRIES - 1:
            logger.info("Waiting 60 seconds before retry...")
            time.sleep(60)

    return False
