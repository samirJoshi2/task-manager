from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = '3104'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ---------------------------
# Models
# ---------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(50), nullable=False)  # e.g., Work, Personal, Study, Urgent
    priority = db.Column(db.String(20), default='Medium')
    deadline = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def calculate_hours(start, end):
    """Return total hours between start and end time."""
    if start and end:
        return round((end - start).total_seconds() / 3600, 2)
    return 0

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def home():
    """
    Dashboard with optional search (by task title).
    Bulk actions handled on the front-end (index.html).
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '').strip()
    if search_query: 
        tasks = Task.query.filter(
            Task.user_id == session['user_id'],
            Task.title.ilike(f"%{search_query}%")
        ).all()
    else:
        tasks = Task.query.filter_by(user_id=session['user_id']).all()
    
    return render_template('index.html', tasks=tasks, search_query=search_query)

@app.route('/chart')
def chart_page():
    """
    Separate page to display the daily & weekly summary chart
    and a daily progress bar for hours. Also includes toggles for
    daily vs. weekly and hours vs. tasks completed.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chart.html')

@app.route('/report/weekly')
def weekly_report():
    """
    Weekly Work Report page showing:
    - Total tasks completed in the last 7 days
    - Total hours worked in the last 7 days
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    tasks = Task.query.filter(
        Task.user_id == session['user_id'],
        Task.start_time >= seven_days_ago
    ).all()
    
    # Completed tasks in last 7 days
    total_completed = sum(1 for t in tasks if t.completed)
    # Hours worked in last 7 days
    total_hours = sum(calculate_hours(t.start_time, t.end_time) for t in tasks)

    return render_template('weekly_report.html',
                           total_completed=total_completed,
                           total_hours=total_hours)

# ---------------------------
# User Authentication
# ---------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup route for new users."""
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('signup'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for existing users."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the current user."""
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# ---------------------------
# Task CRUD
# ---------------------------
@app.route('/task/create', methods=['GET', 'POST'])
def create_task():
    """Create a new task."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description')
        category = request.form['category']
        priority = request.form['priority']
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None

        new_task = Task(
            user_id=session['user_id'],
            title=title,
            description=description,
            category=category,
            priority=priority,
            deadline=deadline
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task created successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('create_task.html')

@app.route('/task/<int:task_id>/update', methods=['GET', 'POST'])
def update_task(task_id):
    """Update an existing task."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form.get('description')
        task.category = request.form['category']
        task.priority = request.form['priority']
        deadline_str = request.form.get('deadline')
        task.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None

        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('update_task.html', task=task)

@app.route('/task/<int:task_id>/delete')
def delete_task(task_id):
    """Delete a task."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'danger')
    return redirect(url_for('home'))

# ---------------------------
# Bulk Actions
# ---------------------------
@app.route('/task/<int:task_id>/start')
def start_task(task_id):
    """Mark task's start_time as now."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    task.start_time = datetime.utcnow()
    db.session.commit()
    flash('Task started!', 'info')
    return redirect(url_for('home'))

@app.route('/task/<int:task_id>/end')
def end_task(task_id):
    """Mark task's end_time as now."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    task.end_time = datetime.utcnow()
    db.session.commit()
    flash('Task ended!', 'info')
    return redirect(url_for('home'))

@app.route('/task/<int:task_id>/complete')
def complete_task(task_id):
    """Mark a task as completed."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    task = Task.query.get_or_404(task_id)
    task.completed = True
    db.session.commit()
    flash('Task marked as completed!', 'success')
    return redirect(url_for('home'))

# ---------------------------
# Summaries for HOURS
# ---------------------------
@app.route('/summary/daily')
def daily_summary():
    """Total hours worked TODAY (returns JSON)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    today = datetime.utcnow().date()
    tasks = Task.query.filter(Task.user_id == session['user_id'], Task.start_time >= today).all()
    total_hours = sum(calculate_hours(t.start_time, t.end_time) for t in tasks)
    return jsonify({'date': str(today), 'total_hours': total_hours})

@app.route('/summary/weekly')
def weekly_summary():
    """Total hours worked THIS WEEK (returns JSON)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    today = datetime.utcnow().date()
    start_week = today - timedelta(days=today.weekday())
    tasks = Task.query.filter(Task.user_id == session['user_id'], Task.start_time >= start_week).all()
    total_hours = sum(calculate_hours(t.start_time, t.end_time) for t in tasks)
    return jsonify({'week_start': str(start_week), 'total_hours': total_hours})

# ---------------------------
# NEW Summaries for TASKS COMPLETED
# ---------------------------
@app.route('/summary/daily_tasks')
def daily_tasks_summary():
    """Number of tasks COMPLETED today (returns JSON)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    today = datetime.utcnow().date()
    # Filter tasks that are completed and ended (end_time) today
    tasks = Task.query.filter(
        Task.user_id == session['user_id'],
        Task.completed == True,
        Task.end_time >= today
    ).all()
    total_tasks = len(tasks)
    return jsonify({'date': str(today), 'total_tasks': total_tasks})

@app.route('/summary/weekly_tasks')
def weekly_tasks_summary():
    """Number of tasks COMPLETED this week (returns JSON)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    today = datetime.utcnow().date()
    start_week = today - timedelta(days=today.weekday())
    tasks = Task.query.filter(
        Task.user_id == session['user_id'],
        Task.completed == True,
        Task.end_time >= start_week
    ).all()
    total_tasks = len(tasks)
    return jsonify({'week_start': str(start_week), 'total_tasks': total_tasks})

# ---------------------------
# API Endpoints
# ---------------------------
@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """Fetch all tasks for the logged-in user as JSON."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    tasks = Task.query.filter_by(user_id=session['user_id']).all()
    tasks_data = []
    for t in tasks:
        tasks_data.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'category': t.category,
            'priority': t.priority,
            'deadline': t.deadline.isoformat() if t.deadline else None,
            'start_time': t.start_time.isoformat() if t.start_time else None,
            'end_time': t.end_time.isoformat() if t.end_time else None,
            'completed': t.completed,
            'progress': t.progress,
            'created_at': t.created_at.isoformat()
        })
    return jsonify(tasks_data)

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def api_update_task(task_id):
    """Update a specific task using JSON (PUT method)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    task = Task.query.get_or_404(task_id)
    if task.user_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No input data provided'}), 400

    # Update fields if present
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'category' in data:
        task.category = data['category']
    if 'priority' in data:
        task.priority = data['priority']
    if 'deadline' in data:
        deadline_str = data['deadline']
        if deadline_str:
            try:
                task.deadline = datetime.fromisoformat(deadline_str)
            except ValueError:
                return jsonify({'error': 'Invalid deadline format. Use ISO format.'}), 400
        else:
            task.deadline = None
    if 'completed' in data:
        task.completed = bool(data['completed'])
    if 'progress' in data:
        task.progress = int(data['progress'])
    if 'start_time' in data:
        start_str = data['start_time']
        if start_str:
            try:
                task.start_time = datetime.fromisoformat(start_str)
            except ValueError:
                return jsonify({'error': 'Invalid start_time format. Use ISO format.'}), 400
        else:
            task.start_time = None
    if 'end_time' in data:
        end_str = data['end_time']
        if end_str:
            try:
                task.end_time = datetime.fromisoformat(end_str)
            except ValueError:
                return jsonify({'error': 'Invalid end_time format. Use ISO format.'}), 400
        else:
            task.end_time = None

    db.session.commit()
    return jsonify({'message': 'Task updated successfully via API.'})

# ---------------------------
# Main
# ---------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
