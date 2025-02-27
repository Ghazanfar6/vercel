from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, vfx
from moviepy.video.fx.all import colorx, lum_contrast
from PIL import ImageEnhance, Image
import numpy as np
import cv2
import os
from config import PROCESSED_VIDEO_DIR

def add_border(input_path, output_path, border_size=10):
    try:
        with VideoFileClip(input_path) as video:
            bordered_video = video.margin(border_size, color=(0, 0, 0))
            bordered_video.write_videofile(output_path, codec='libx264', bitrate='5000k')
    except Exception as e:
        print(f"Error adding border to video: {e}")

def overlay_logo(input_path, output_path, logo_path, alpha=0.5):
    try:
        with VideoFileClip(input_path) as video:
            logo = (ImageClip(logo_path)
                    .set_duration(video.duration)
                    .resize(height=video.size[1] // 15)  # Resize logo to 6.67% of the video height
                    .set_position(("center", "bottom"))
                    .set_opacity(alpha))
            final_video = CompositeVideoClip([video, logo])
            final_video.write_videofile(output_path, codec='libx264', bitrate='5000k')
    except Exception as e:
        print(f"Error overlaying logo on video: {e}")

def upscale_and_smooth(frame, target_size=(1080, 1920), target_fps=60):
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

def add_hdr_filter(input_path, output_path):
    try:
        with VideoFileClip(input_path) as video:
            # Increase FPS for smoother motion
            video = video.set_fps(60)  

            # Apply upscaling, HDR effects, and smoothing
            def process_frame(frame):
                frame = upscale_and_smooth(frame)
                frame = apply_hdr_effect(frame)
                return frame

            # Process frames
            enhanced_video = video.fl_image(process_frame)

            # Export video with improved quality
            enhanced_video.write_videofile(
                output_path,
                codec='libx264',
                bitrate='10M',  # High-quality bitrate
                fps=60,
                preset="slow",  # Better compression and quality
                threads=4
            )

    except Exception as e:
        print(f"Error adding HDR filter to video: {e}")

def process_video(input_video_path, logo_path=None):
    try:
        # Define the output path for the processed video
        bordered_video_path = os.path.join(PROCESSED_VIDEO_DIR, 'bordered_processed_video.mp4')
        hdr_video_path = os.path.join(PROCESSED_VIDEO_DIR, 'hdr_processed_video.mp4')
        final_video_path = os.path.join(PROCESSED_VIDEO_DIR, 'processed_video.mp4')
        
        # Add a border to the video
        add_border(input_video_path, bordered_video_path)
        
        # Add HDR filter to the video
        add_hdr_filter(bordered_video_path, hdr_video_path)
        
        # Overlay logo if logo_path is provided
        if logo_path:
            overlay_logo(hdr_video_path, final_video_path, logo_path)
        else:
            final_video_path = hdr_video_path
        
        return final_video_path
    except Exception as e:
        print(f"Error processing video: {e}")
        return None