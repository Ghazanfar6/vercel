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
        # Parse scheduling information
        scheduled_for = request.form.get('scheduled_for')
        repeat_interval = request.form.get('repeat_interval')

        scheduled_time = None
        if scheduled_for:
            scheduled_time = datetime.fromisoformat(scheduled_for.replace('Z', '+00:00'))
        else:
            scheduled_time = datetime.utcnow()

        task = ReelTask(
            url=url,
            scheduled_for=scheduled_time,
            repeat_interval=int(repeat_interval) if repeat_interval else None,
            status='pending'
        )

        db.session.add(task)

        # Add log entry
        log = BotLog(
            level='INFO',
            message=f'Task created: URL={url}, Scheduled={scheduled_time}, Repeat={repeat_interval}'
        )
        db.session.add(log)
        db.session.commit()

        logger.info(f"Created new task {task.id} for URL: {url}")

        # Start immediate processing if no specific schedule
        if not scheduled_for:
            thread = threading.Thread(target=process_reel_task, args=(task.id,))
            thread.daemon = True
            thread.start()
            logger.info(f"Started immediate processing for task {task.id}")

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
    logger.info(f"Starting to process task {task_id}")

    with app.app_context():
        try:
            task = ReelTask.query.get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # Update status to processing
            task.status = 'processing'
            db.session.add(BotLog(level='INFO', message=f'Processing task {task_id}'))
            db.session.commit()
            logger.info(f"Updated task {task_id} status to processing")

            # Download reel
            downloader = InstagramReelDownloader()
            video_path = downloader.download_reel(task.url)
            if not video_path:
                raise Exception(f"Failed to download reel for task {task_id}")

            logger.info(f"Downloaded video for task {task_id}: {video_path}")

            # Process video
            processed_video_path = process_video(video_path)
            if not processed_video_path:
                raise Exception(f"Failed to process video for task {task_id}")

            logger.info(f"Processed video for task {task_id}: {processed_video_path}")

            # Upload processed video
            caption = "Check out this amazing content! #fitness #motivation"
            if not upload_with_retry(processed_video_path, caption):
                raise Exception(f"Failed to upload video for task {task_id}")

            logger.info(f"Successfully uploaded video for task {task_id}")

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()

            # Create next task if repeat interval is set
            if task.repeat_interval:
                next_run_time = datetime.utcnow() + timedelta(minutes=task.repeat_interval)
                next_task = ReelTask(
                    url=task.url,
                    scheduled_for=next_run_time,
                    repeat_interval=task.repeat_interval,
                    status='pending'
                )
                db.session.add(next_task)
                logger.info(f"Created next scheduled task for {task.url} at {next_run_time}")

            db.session.add(BotLog(level='INFO', message=f'Completed task {task_id}'))
            db.session.commit()

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            if task:
                task.status = 'failed'
                task.error_message = str(e)
                db.session.add(BotLog(level='ERROR', message=f'Task {task_id} failed: {str(e)}'))
                db.session.commit()

def check_scheduled_tasks():
    """Background thread to check and process scheduled tasks"""
    logger.info("Starting scheduled tasks checker")

    while True:
        try:
            with app.app_context():
                now = datetime.utcnow()
                # Find pending tasks that are due
                tasks = ReelTask.query.filter(
                    ReelTask.status == 'pending',
                    ReelTask.scheduled_for <= now
                ).all()

                if tasks:
                    logger.info(f"Found {len(tasks)} tasks ready for processing")
                    for task in tasks:
                        logger.info(f"Processing scheduled task {task.id}")
                        thread = threading.Thread(target=process_reel_task, args=(task.id,))
                        thread.daemon = True
                        thread.start()

        except Exception as e:
            logger.error(f"Error in scheduled task checker: {str(e)}")
            try:
                with app.app_context():
                    db.session.add(BotLog(level='ERROR', message=f'Scheduler error: {str(e)}'))
                    db.session.commit()
            except Exception as inner_e:
                logger.error(f"Error logging scheduler error: {str(inner_e)}")

        time.sleep(15)  # Check every 15 seconds

# Start the scheduler thread
scheduler_thread = threading.Thread(target=check_scheduled_tasks, daemon=True)
scheduler_thread.start()
logger.info("Started scheduler thread")

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