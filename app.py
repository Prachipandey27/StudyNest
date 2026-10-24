import os
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db, close_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'local-development-only-change-before-deployment'
app.teardown_appcontext(close_db)
init_db()
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped


@app.before_request
def protect_forms():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(24)
    if request.method == 'POST' and not secrets.compare_digest(
        session['csrf'], request.form.get('csrf', '')
    ):
        abort(400, 'Invalid form token. Reload the page and try again.')


@app.context_processor
def inject_common():
    return {'csrf': session.get('csrf', ''), 'days': DAYS}


@app.route('/')
def home():
    return redirect(url_for('dashboard')) if session.get('user_id') else render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not (1 <= len(name) <= 60 and '@' in email and len(email) <= 120 and len(password) >= 6):
            flash('Enter a name, valid email and password of at least 6 characters.', 'error')
        else:
            try:
                db = get_db()
                cur = db.execute('INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)',
                                 (name, email, generate_password_hash(password)))
                db.commit()
                session.clear()
                session['user_id'] = cur.lastrowid
                session['user_name'] = name
                flash('Welcome to StudyNest!', 'success')
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                flash('That email is already registered.', 'error')
    return render_template('auth.html', mode='register')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = get_db().execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        flash('Incorrect email or password.', 'error')
    return render_template('auth.html', mode='login')


@app.post('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    uid = session['user_id']
    studies = db.execute('SELECT * FROM sessions WHERE user_id = ? ORDER BY study_date DESC, id DESC LIMIT 30', (uid,)).fetchall()
    weekly = db.execute('SELECT * FROM timetable WHERE user_id = ? ORDER BY day, start_time', (uid,)).fetchall()
    total = db.execute('SELECT COALESCE(SUM(minutes),0) FROM sessions WHERE user_id = ?', (uid,)).fetchone()[0]
    count = db.execute('SELECT COUNT(*) FROM sessions WHERE user_id = ?', (uid,)).fetchone()[0]
    return render_template('dashboard.html', studies=studies, weekly=weekly, total=total, count=count,
                           today=date.today().isoformat())


@app.post('/sessions/add')
@login_required
def add_session():
    subject = request.form.get('subject', '').strip()
    day = request.form.get('study_date', '')
    note = request.form.get('note', '').strip()[:150]
    try:
        minutes = int(request.form.get('minutes', ''))
        datetime.strptime(day, '%Y-%m-%d')
        valid = 1 <= minutes <= 1440 and 1 <= len(subject) <= 60
    except (ValueError, TypeError):
        valid = False
    if not valid:
        flash('Enter a subject, valid date and duration between 1 and 1440 minutes.', 'error')
    else:
        db = get_db()
        db.execute('INSERT INTO sessions(user_id,subject,study_date,minutes,note) VALUES (?,?,?,?,?)',
                   (session['user_id'], subject, day, minutes, note))
        db.commit()
        flash('Study session added.', 'success')
    return redirect(url_for('dashboard') + '#sessions')


@app.post('/sessions/<int:item_id>/delete')
@login_required
def delete_session(item_id):
    db = get_db()
    db.execute('DELETE FROM sessions WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.commit()
    return redirect(url_for('dashboard') + '#sessions')


@app.post('/timetable/add')
@login_required
def add_timetable():
    subject = request.form.get('subject', '').strip()
    start = request.form.get('start_time', '')
    end = request.form.get('end_time', '')
    try:
        day = int(request.form.get('day', ''))
        datetime.strptime(start, '%H:%M')
        datetime.strptime(end, '%H:%M')
        valid = 0 <= day <= 6 and 1 <= len(subject) <= 60 and start < end
    except (TypeError, ValueError):
        valid = False
    if not valid:
        flash('Enter a valid subject, weekday and time range.', 'error')
    else:
        db = get_db()
        db.execute('INSERT INTO timetable(user_id,day,subject,start_time,end_time) VALUES (?,?,?,?,?)',
                   (session['user_id'], day, subject, start, end))
        db.commit()
        flash('Timetable slot added.', 'success')
    return redirect(url_for('dashboard') + '#timetable')


@app.post('/timetable/<int:item_id>/delete')
@login_required
def delete_timetable(item_id):
    db = get_db()
    db.execute('DELETE FROM timetable WHERE id = ? AND user_id = ?', (item_id, session['user_id']))
    db.commit()
    return redirect(url_for('dashboard') + '#timetable')


if __name__ == '__main__':
    app.run(debug=True)
