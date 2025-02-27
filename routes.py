from flask import render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, ReelTask, BotLog
import json
from datetime import datetime, timedelta
import time
from bot import InstagramReelDownloader, process_video, upload_with_retry
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('instagram_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    tasks = ReelTask.query.order_by(ReelTask.created_at.desc()).limit(10).all()
    logs = BotLog.query.order_by(BotLog.timestamp.desc()).limit(50).all()
    return render_template('dashboard.html', tasks=tasks, logs=logs)

@app.route('/add_reel', methods=['POST'])
@login_required
def add_reel():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        # Check if Instagram credentials are set
        if not current_user.instagram_username:
            return jsonify({'error': 'Please set your Instagram credentials in Settings'}), 400

        # Parse scheduling information
        scheduled_for = request.form.get('scheduled_for')
        repeat_interval = request.form.get('repeat_interval')

        scheduled_time = None
        if scheduled_for:
            scheduled_time = datetime.fromisoformat(scheduled_for.replace('Z', '+00:00'))
        else:
            scheduled_time = datetime.utcnow()

        # Create new task with user_id
        task = ReelTask(
            url=url,
            scheduled_for=scheduled_time,
            repeat_interval=int(repeat_interval) if repeat_interval else None,
            status='pending',
            user_id=current_user.id
        )

        db.session.add(task)
        db.session.commit()

        logger.info(f"Created new task {task.id} for URL: {url}")

        # Start processing if scheduled for now
        if not scheduled_for:
            thread = threading.Thread(target=process_reel_task, args=(task.id,))
            thread.daemon = True
            thread.start()

        return jsonify({
            'message': 'Task added successfully',
            'task_id': task.id,
            'url': task.url,
            'scheduled_for': task.scheduled_for.isoformat() if task.scheduled_for else None,
            'repeat_interval': task.repeat_interval
        })

    except Exception as e:
        logger.error(f"Error adding reel task: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_reel_task(task_id):
    """Process a single reel task"""
    with app.app_context():
        try:
            task = ReelTask.query.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # Get the user's Instagram credentials
            user = User.query.get(task.user_id)
            if not user or not user.instagram_username:
                raise Exception("Instagram credentials not set")

            # Update status to processing
            task.status = 'processing'
            db.session.commit()
            logger.info(f"Processing task {task_id}")

            # Download reel using user's credentials
            downloader = InstagramReelDownloader()
            video_path = downloader.download_reel(task.url, user.instagram_username, user.instagram_password)
            if not video_path:
                raise Exception(f"Failed to download reel for task {task_id}")

            # Process video (simplified for now)
            processed_video_path = process_video(video_path)
            if not processed_video_path:
                raise Exception(f"Failed to process video for task {task_id}")

            # Upload video
            caption = "Check out this amazing content! #fitness #motivation"
            if not upload_with_retry(processed_video_path, caption):
                raise Exception(f"Failed to upload video for task {task_id}")

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Successfully completed task {task_id}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                db.session.commit()

def check_scheduled_tasks():
    """Check for and process scheduled tasks"""
    logger.info("Starting scheduled task checker")

    while True:
        try:
            with app.app_context():
                # Find pending tasks that are due
                now = datetime.utcnow()
                tasks = ReelTask.query.filter(
                    ReelTask.status == 'pending',
                    ReelTask.scheduled_for <= now
                ).all()

                for task in tasks:
                    logger.info(f"Found scheduled task {task.id} ready for processing")
                    thread = threading.Thread(target=process_reel_task, args=(task.id,))
                    thread.daemon = True
                    thread.start()

        except Exception as e:
            logger.error(f"Error in task checker: {str(e)}")

        time.sleep(15)  # Check every 15 seconds

# Start the scheduler thread
scheduler_thread = threading.Thread(target=check_scheduled_tasks, daemon=True)
scheduler_thread.start()

@app.route('/stream_logs')
@login_required
def stream_logs():
    def generate():
        last_id = 0
        while True:
            with app.app_context():
                try:
                    logs = BotLog.query.filter(BotLog.id > last_id).order_by(BotLog.id.asc()).all()
                    if logs:
                        last_id = logs[-1].id
                        data = json.dumps([{
                            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            'level': log.level,
                            'message': log.message
                        } for log in logs])
                        yield f"data: {data}\n\n"
                except Exception as e:
                    logger.error(f"Error in stream_logs: {str(e)}")
            time.sleep(1)

    return Response(generate(), mimetype='text/event-stream')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        instagram_username = request.form.get('instagram_username')
        instagram_password = request.form.get('instagram_password')

        if instagram_username and instagram_password:
            current_user.instagram_username = instagram_username
            current_user.set_instagram_password(instagram_password)
            db.session.commit()
            logger.info(f"Instagram credentials updated for user: {current_user.username}")
            flash('Instagram settings updated successfully')
            return redirect(url_for('dashboard'))
        else:
            flash('Both Instagram username and password are required')

    return render_template('settings.html')