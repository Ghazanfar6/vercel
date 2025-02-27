import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
PROCESSED_VIDEO_DIR = BASE_DIR / "processed_videos"

# Create directories if they don't exist
DOWNLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_VIDEO_DIR.mkdir(exist_ok=True)

# Instagram credentials from environment variables
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_2FA_SECRET = os.environ.get("INSTAGRAM_2FA_SECRET")

# Retry configuration
MAX_RETRIES = 3
MIN_INTERVAL = 3600  # 60 minutes
MAX_INTERVAL = 4200  # 70 minutes

def generate_caption():
    """Generate a caption for the reel"""
    return """🎥 Check out this amazing content!
    
#fitness #motivation #gym #workout #fitnessmotivation #training #health 
#fit #lifestyle #sport #healthy #gymlife #fitfam #bodybuilding #exercise
#wellness #crossfit #personaltrainer #strong #weightloss #muscle"""
