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
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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

    # Parse scheduling information
    scheduled_for = request.form.get('scheduled_for')
    repeat_interval = request.form.get('repeat_interval')

    try:
        task = ReelTask(
            url=url,
            scheduled_for=datetime.fromisoformat(scheduled_for.replace('Z', '+00:00')) if scheduled_for else datetime.utcnow(),
            repeat_interval=int(repeat_interval) if repeat_interval else None,
            status='pending'
        )

        db.session.add(task)
        db.session.commit()

        # Log task creation
        log = BotLog(level='INFO', message=f'New task created for URL: {url}')
        db.session.add(log)
        db.session.commit()

        # Start processing in background if no specific schedule
        if not scheduled_for:
            thread = threading.Thread(target=process_reel_task, args=(task.id,))
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
    with app.app_context():
        try:
            task = ReelTask.query.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # Check if it's time to process this task
            if task.scheduled_for and task.scheduled_for > datetime.utcnow():
                logger.info(f"Task {task_id} scheduled for later: {task.scheduled_for}")
                return

            logger.info(f"Processing task {task_id} for URL: {task.url}")
            task.status = 'processing'
            db.session.commit()

            # Add log entry for status change
            log = BotLog(level='INFO', message=f'Started processing task {task_id}')
            db.session.add(log)
            db.session.commit()

            # Download reel
            downloader = InstagramReelDownloader()
            video_path = downloader.download_reel(task.url)

            if not video_path:
                raise Exception("Failed to download reel")

            # Process video
            processed_video_path = process_video(video_path)
            if not processed_video_path:
                raise Exception("Failed to process video")

            # Upload processed video
            caption = "Processed by Instagram Reel Bot"
            if not upload_with_retry(processed_video_path, caption):
                raise Exception("Failed to upload video")

            task.status = 'completed'
            task.completed_at = datetime.utcnow()

            # Schedule next run if repeat interval is set
            if task.repeat_interval:
                next_task = ReelTask(
                    url=task.url,
                    scheduled_for=datetime.utcnow() + timedelta(minutes=task.repeat_interval),
                    repeat_interval=task.repeat_interval,
                    status='pending'
                )
                db.session.add(next_task)
                logger.info(f"Created next scheduled task for {task.url}")

            # Log success
            log = BotLog(level='INFO', message=f'Successfully processed task {task_id}')
            db.session.add(log)
            db.session.commit()

        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            logger.error(f"Task {task_id} failed: {str(e)}")

            # Log error
            log = BotLog(level='ERROR', message=f'Task {task_id} failed: {str(e)}')
            db.session.add(log)
            db.session.commit()

        finally:
            task.last_check = datetime.utcnow()
            db.session.commit()

def check_scheduled_tasks():
    """Background thread to process scheduled tasks"""
    logger.info("Starting scheduled tasks checker")
    while True:
        with app.app_context():
            try:
                # Find tasks that are scheduled and ready to process
                now = datetime.utcnow()
                tasks = ReelTask.query.filter(
                    ReelTask.status == 'pending',
                    ReelTask.scheduled_for <= now
                ).all()

                if tasks:
                    logger.info(f"Found {len(tasks)} tasks ready for processing")
                    for task in tasks:
                        logger.info(f"Starting scheduled task {task.id}")
                        # Create a new thread for each task
                        thread = threading.Thread(target=process_reel_task, args=(task.id,))
                        thread.daemon = True  # Make thread daemon so it doesn't block shutdown
                        thread.start()

            except Exception as e:
                logger.error(f"Error checking scheduled tasks: {str(e)}")
                # Add to bot logs for UI visibility
                with app.app_context():
                    log = BotLog(level='ERROR', message=f'Scheduler error: {str(e)}')
                    db.session.add(log)
                    db.session.commit()

            # Sleep for a shorter interval to be more responsive
            time.sleep(30)  # Check every 30 seconds

# Start the scheduler thread when the application starts
scheduler_thread = threading.Thread(target=check_scheduled_tasks, daemon=True)
scheduler_thread.start()
logger.info("Started scheduler thread")

@app.route('/stream_logs')
@login_required
def stream_logs():
    def generate():
        last_id = 0  # Start from the beginning
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

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))

        # Create new user
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Log the user in
        login_user(user)
        return redirect(url_for('dashboard'))

    return render_template('signup.html')