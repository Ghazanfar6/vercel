# Instagram Reel Bot

A bot that automatically downloads and reposts reels from Instagram based on provided URLs at random intervals between 60 to 70 minutes.

## Files Structure

- `main.py` - The entry point that orchestrates the automation cycle
- `scraper.py` - Handles downloading reels from Instagram using `instaloader`
- `uploader.py` - Manages reel uploading using `instagrapi`
- `config.py` - Contains all configuration settings
- `utils.py` - Helper functions for file management and logging
- `video_processor.py` - Processes downloaded videos (e.g., adding borders, overlaying logos, applying HDR filter)
- `requirements.txt` - Lists all the required Python packages
- `.env` - Contains environment variables for Instagram credentials and other settings

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/InstagramReelBot.git
cd InstagramReelBot
```

### 2. Create a `.env` File

Create a `.env` file in the root directory with your Instagram credentials and other settings:

```properties
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
INSTAGRAM_ACCESS_TOKEN=your_access_token
INSTAGRAM_2FA_SECRET=your_2fa_secret
BROWSER_SETTINGS__EXPLICIT_WAIT=20
BROWSER_SETTINGS__PAGE_LOAD_TIMEOUT=30
MIN_WAIT=3
MAX_WAIT=5
```

### 3. Install Required Packages

Install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

### 4. Update Configuration

Edit the `config.py` file to update any necessary settings, such as directories for downloads and processed videos, default captions, and timing configurations.

### 5. Run the Bot

Run the bot using the following command:

```bash
python main.py
```

## Configuration

The bot is configured to:
- Download reels from provided Instagram URLs
- Post at random intervals (between 60-70 minutes)
- Use default viral hashtags (configurable in `config.py`)
- Store downloads in the "downloads" directory
- Log activities to "instagram_bot.log"

### Key Configuration Variables

- `INSTAGRAM_USERNAME`: Your Instagram username
- `INSTAGRAM_PASSWORD`: Your Instagram password
- `INSTAGRAM_ACCESS_TOKEN`: Your Instagram access token
- `INSTAGRAM_2FA_SECRET`: Your Instagram 2FA secret
- `DOWNLOAD_DIR`: Directory to store downloaded reels
- `PROCESSED_VIDEO_DIR`: Directory to store processed videos
- `DEFAULT_CAPTION`: Default caption template for reposts
- `MIN_INTERVAL`: Minimum interval between posts (in seconds)
- `MAX_INTERVAL`: Maximum interval between posts (in seconds)
- `MAX_RETRIES`: Maximum number of retries for operations
- `USER_AGENT`: User agent for web scraping

## Key Features

### 1. Automated Reel Download

- Uses `instaloader` for downloading reels
- Downloads reels in MP4 format
- Handles video extraction

### 2. Automated Posting

- Uses `instagrapi` for reliable uploads
- Includes retry mechanism
- Maintains random intervals

### 3. Error Handling

- Comprehensive logging
- Multiple retry attempts
- Graceful failure recovery

### 4. File Management

- Automatic cleanup of old downloads
- Download verification
- Organized file structure

## Video Processing

The `video_processor.py` file contains functions to process downloaded videos, such as adding borders, overlaying logos, and applying HDR filter.

### Example Usage

```python
from video_processor import process_video

input_video_path = "downloads/reel.mp4"
logo_path = "llr.png"
processed_video_path = process_video(input_video_path, logo_path)
```

## Running Tests

The `test_scraper.py` file contains unit tests for the scraper. Run the tests using the following command:

```bash
python -m unittest test_scraper.py
```

## Additional Notes

- Ensure that the `chromedriver.exe` file is in the root directory.
- Update the `logo_path` in `main.py` to point to your logo file.
- Customize the `DEFAULT_CAPTION` in `config.py` to suit your needs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## Contact

For any questions or support, please contact [your_email@example.com](mailto:your_email@example.com).
