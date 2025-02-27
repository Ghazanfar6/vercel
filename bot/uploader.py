
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
            
            # Configure challenge resolver for 2FA/unusual login
            logger.info("Setting up challenge resolver for login verification...")
            self.client.challenge_code_handler = self._handle_challenge
            
            # Regular username/password login with extended settings
            logger.info(f"Logging in with username and password for {username}...")
            login_via_session = False
            login_via_password = False
            
            # First try login directly 
            try:
                self.client.login(username, password)
                login_via_password = True
            except Exception as e:
                logger.warning(f"Direct login failed: {str(e)}")
            
            # If login failed, try alternative methods
            if not login_via_password:
                # Try to use pre-saved session from attached assets if available
                alternative_session = "attached_assets/session_settings.pkl"
                if os.path.exists(alternative_session):
                    try:
                        logger.info("Trying login with alternative session file...")
                        with open(alternative_session, "rb") as f:
                            cached_settings = pickle.load(f)
                            self.client.set_settings(cached_settings)
                            self.client.account_info()
                            login_via_session = True
                            logger.info("Alternative session login successful")
                    except Exception as e:
                        logger.warning(f"Alternative session login failed: {str(e)}")
                
                # Last resort - full login with new configuration
                if not login_via_session:
                    # Add short delay to avoid rate limiting
                    time.sleep(3)
                    
                    # Set trusted device to potentially bypass security measures
                    self.client.set_trusted_device("ANDROID")
                    
                    # Try with force login which bypasses some checks
                    try:
                        logger.info("Attempting forced login...")
                        self.client.login(username, password, relogin=True)
                        login_via_password = True
                    except Exception as e:
                        logger.error(f"All login attempts failed: {str(e)}")
                        return False
            
            # Save session for future use if any login method worked
            if login_via_password or login_via_session:
                with open(session_file, "wb") as f:
                    pickle.dump(self.client.get_settings(), f)
                logger.info("Login successful and session saved")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
            
    def _handle_challenge(self, username, choice):
        """Handle Instagram verification challenges"""
        try:
            logger.info(f"Received login challenge for {username}. Instagram requires verification.")
            # For automated systems, typically you would choose the option to send code to email
            if choice == 0:
                choice = 1  # Usually option 1 is email
            
            # Log the challenge for manual intervention
            logger.warning(f"MANUAL ACTION REQUIRED: Instagram needs verification for {username}")
            logger.warning("Please log in manually through a browser to verify the account")
            
            # Return None to indicate we can't handle this automatically
            return None
        except Exception as e:
            logger.error(f"Error in challenge handler: {str(e)}")
            return None

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
    from models import User, BotLog
    import os
    
    with app.app_context():
        # Track errors for better debugging
        errors = []
        
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
        
        # Log the attempt to the database for tracking
        try:
            log_entry = BotLog(
                level="INFO",
                message=f"Starting upload process for video: {os.path.basename(video_path)}"
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log to database: {str(e)}")
        
        if not user or not user.instagram_username:
            error_msg = "No user with Instagram credentials found"
            logger.error(error_msg)
            errors.append(error_msg)
            try:
                log_entry = BotLog(level="ERROR", message=error_msg)
                db.session.add(log_entry)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to log to database: {str(e)}")
            return False
        
        # Get password from environment or .env file
        instagram_password = os.environ.get('INSTAGRAM_PASSWORD', "Ghazanfar@1234")
        
        if not instagram_password:
            error_msg = "No Instagram password available"
            logger.error(error_msg)
            errors.append(error_msg)
            try:
                log_entry = BotLog(level="ERROR", message=error_msg)
                db.session.add(log_entry)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to log to database: {str(e)}")
            return False
            
        logger.info(f"Starting upload with user: {user.instagram_username}")
        
        # Create uploader and attempt login/upload with retries
        uploader = InstagramUploader()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Upload attempt {attempt + 1}/{max_retries}")
                
                # Login first (with session if available)
                login_success = uploader.login(user.instagram_username, instagram_password)
                
                if not login_success:
                    error_msg = f"Failed to login to Instagram on attempt {attempt + 1}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    try:
                        log_entry = BotLog(level="ERROR", message=error_msg)
                        db.session.add(log_entry)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Failed to log to database: {str(e)}")
                        
                    if attempt < max_retries - 1:
                        time.sleep(30)  # Wait before retry
                    continue
                
                # Then upload
                current_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                full_caption = f"{caption}\n\nUploaded at {current_timestamp} #repost"
                
                if uploader.upload_reel(video_path, full_caption):
                    success_msg = f"Upload successful for video: {os.path.basename(video_path)}"
                    logger.info(success_msg)
                    try:
                        log_entry = BotLog(level="INFO", message=success_msg)
                        db.session.add(log_entry)
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Failed to log to database: {str(e)}")
                    return True
                else:
                    error_msg = f"Upload failed but no exception was raised on attempt {attempt + 1}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Upload attempt {attempt + 1} failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                try:
                    log_entry = BotLog(level="ERROR", message=error_msg)
                    db.session.add(log_entry)
                    db.session.commit()
                except Exception as log_e:
                    logger.error(f"Failed to log to database: {str(log_e)}")
            
            if attempt < max_retries - 1:
                wait_time = 60 * (attempt + 1)
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)  # Increasing backoff
        
        # Log all errors encountered
        all_errors = "\n".join(errors)
        final_error_msg = f"All {max_retries} upload attempts failed. Errors:\n{all_errors}"
        logger.error(final_error_msg)
        try:
            log_entry = BotLog(level="ERROR", message=final_error_msg[:500])  # Truncate if too long
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log to database: {str(e)}")
            
        return False
