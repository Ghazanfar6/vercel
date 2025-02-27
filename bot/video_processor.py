from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import ImageEnhance, Image
import numpy as np
import cv2
import os
from config import PROCESSED_VIDEO_DIR

def upscale_and_smooth(frame, target_size=(1080, 1920)):
    """Upscales, smooths, and enhances video frames."""
    # Resize frame to 1080x1920 (Reels resolution)
    frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_CUBIC)
    
    # Apply Gaussian Blur to reduce noise (optional)
    frame = cv2.GaussianBlur(frame, (3, 3), 0)
    return frame

def apply_hdr_effect(frame):
    """Applies HDR-like color adjustments using PIL."""
    image = Image.fromarray(frame)

    # Apply brightness, contrast, sharpness, and saturation enhancements
    image = ImageEnhance.Brightness(image).enhance(1.1)  # +10% Brightness
    image = ImageEnhance.Contrast(image).enhance(1.3)  # +30% Contrast
    image = ImageEnhance.Sharpness(image).enhance(1.4)  # +40% Sharpness
    image = ImageEnhance.Color(image).enhance(1.25)  # +25% Color Vibrance

    return np.array(image)

def process_video(input_video_path, logo_path=None):
    try:
        # Define the output path for the processed video
        bordered_video_path = os.path.join(PROCESSED_VIDEO_DIR, 'bordered_processed_video.mp4')
        final_video_path = os.path.join(PROCESSED_VIDEO_DIR, 'processed_video.mp4')
        
        with VideoFileClip(input_video_path) as video:
            # Add HDR effect and process frames
            def process_frame(frame):
                frame = upscale_and_smooth(frame)
                frame = apply_hdr_effect(frame)
                return frame

            # Process video
            processed_video = video.fl_image(process_frame)

            # Add logo if provided
            if logo_path:
                logo = (ImageClip(logo_path)
                        .set_duration(video.duration)
                        .resize(height=video.size[1] // 15)  # Resize logo to 6.67% of video height
                        .set_position(("center", "bottom"))
                        .set_opacity(0.5))
                final_video = CompositeVideoClip([processed_video, logo])
            else:
                final_video = processed_video

            # Export video with improved quality
            final_video.write_videofile(
                final_video_path,
                codec='libx264',
                bitrate='10M',
                fps=60,
                preset="slow",
                threads=4
            )
        
        return final_video_path
    except Exception as e:
        print(f"Error processing video: {e}")
        return None
