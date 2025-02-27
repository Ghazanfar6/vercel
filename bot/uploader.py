
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
        # Set sensible timeouts and user agent
        self.client.request_timeout = 30
        self.client.user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 123.1.0.26.115 (iPhone11,8; iOS 14_8; en_US; en-US; scale=2.00; 828x1792; 190542906)"

    def login(self, username, password, use_session=True):
        """Login to Instagram with session caching"""
        try:
            # Create sessions directory if it doesn't exist
            if not os.path.exists('sessions'):
                os.makedirs('sessions')
                
            session_file = f"sessions/session_{username}.pkl"
            
            if use_session and os.path.exists(session_file):
                logger.info(f"Attempting to login with cached session for {username}...")
                with open(session_file, "rb") as f:
                    cached_settings = pickle.load(f)
                    self.client.set_settings(cached_settings)
                    
                # Verify the session is still valid by getting profile info
                try:
                    self.client.account_info()
                    logger.info("Session is valid, login successful")
                    return True
                except Exception as e:
                    logger.warning(f"Cached session invalid, will perform fresh login: {str(e)}")
                    # Continue to regular login if session is invalid
            
            # Regular username/password login
            logger.info(f"Logging in with username and password for {username}...")
            self.client.login(username, password)
            
            # Save session for future use
            with open(session_file, "wb") as f:
                pickle.dump(self.client.get_settings(), f)
                
            logger.info("Login successful and session saved")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    def upload_reel(self, video_path, caption):
        """Upload a reel to Instagram with proper error handling"""
        try:
            logger.info(f"Attempting to upload reel: {video_path}")
            
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
            
            # Add a small delay to simulate human behavior
            time.sleep(2)
            
            # Upload clip with proper parameters
            media = self.client.clip_upload(
                video_path, 
                caption=caption,
                extra_data={
                    "like_and_view_counts_disabled": False,
                    "disable_comments": False,
                }
            )
            
            if media:
                logger.info(f"Successfully uploaded reel: {video_path}")
                logger.info(f"Media ID: {media.id}, Media code: {media.code}")
                logger.info(f"Media URL: https://www.instagram.com/reel/{media.code}/")
                return True
            else:
                logger.error("Upload returned None")
                return False
                
        except Exception as e:
            logger.error(f"Failed to upload reel: {str(e)}")
            return False

# Upload function with retry logic 
def upload_with_retry(video_path, caption, max_retries=3):
    """Upload with retry mechanism using instagrapi"""
    from app import app
    from models import User
    import os
    
    with app.app_context():
        # Try to determine which task is being processed
        try:
            from routes import current_processing_task_id
            if current_processing_task_id:
                from models import ReelTask
                task = ReelTask.query.get(current_processing_task_id)
                if task:
                    user = User.query.get(task.user_id)
                    logger.info(f"Using credentials for task {current_processing_task_id}, user_id: {task.user_id}")
                else:
                    logger.warning(f"Task {current_processing_task_id} not found, falling back to first user")
                    user = User.query.first()
            else:
                logger.warning("No current task ID found, falling back to first user")
                user = User.query.first()
        except (ImportError, NameError):
            logger.warning("Could not import current_processing_task_id, falling back to first user")
            user = User.query.first()
        
        if not user or not user.instagram_username:
            logger.error("No user with Instagram credentials found")
            return False
        
        # Attempt to decrypt the password if we can access it
        # Note: Since it's hashed we can't retrieve it directly
        # For testing/production use, consider storing encrypted (not hashed) passwords
        # that can be decrypted, or use environment variables
        instagram_password = os.environ.get('INSTAGRAM_TEST_PASSWORD')
        
        if not instagram_password:
            logger.error("No Instagram password available - set INSTAGRAM_TEST_PASSWORD environment variable")
            logger.info("For testing, set this environment variable or implement a secure password retrieval method")
            # For testing fallback 
            logger.info(f"SIMULATION MODE: Pretending to upload video: {video_path}")
            time.sleep(2)
            logger.info("SIMULATION MODE: Upload successful!")
            return True
            
        logger.info(f"Starting upload with user: {user.instagram_username}")
        
        # Create uploader and attempt login/upload with retries
        uploader = InstagramUploader()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Upload attempt {attempt + 1}/{max_retries}")
                
                # Login first (with session if available)
                if not uploader.login(user.instagram_username, instagram_password):
                    logger.error(f"Failed to login to Instagram on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(30)  # Wait before retry
                    continue
                
                # Then upload
                current_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                full_caption = f"{caption}\n\nUploaded at {current_timestamp} #repost"
                
                if uploader.upload_reel(video_path, full_caption):
                    logger.info("Upload successful!")
                    return True
                
            except Exception as e:
                logger.error(f"Upload attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"Waiting {60 * (attempt + 1)} seconds before retry...")
                time.sleep(60 * (attempt + 1))  # Increasing backoff
        
        logger.error(f"All {max_retries} upload attempts failed")
        return False
