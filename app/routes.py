# app/routes.py
from datetime import datetime, timedelta
failed_attempts = {}
import re
import sqlite3
from flask import Blueprint, render_template, request, session, redirect, url_for
import bcrypt
from functools import wraps  # <-- add this import

main = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                return redirect(url_for('main.login'))
            if session['role'].lower() != required_role.lower():
                return "Access denied ❌ You do not have permission to view this page"
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ----------------------
# REGISTER ROUTE
# ----------------------
@main.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role').capitalize()

        # ----------------------
        # VALIDATIONS
        # ----------------------
        if not username or not email or not password:
            error = "All fields are required"

        elif len(username) < 3:
            error = "Username must be at least 3 characters"

        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = "Invalid email format"

        elif len(password) < 8:
            error = "Password must be at least 8 characters"

        else:
            # ----------------------
            # HASH PASSWORD
            # ----------------------
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # ----------------------
            # STORE IN SQLITE DATABASE
            # ----------------------
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                    (username, email, hashed_password.decode('utf-8'), role)
                )
                conn.commit()
                print("User saved to database")

            except sqlite3.IntegrityError:
                error = "Email already exists"

            finally:
                conn.close()

    return render_template("register.html", error=error)


# ----------------------
# LOGIN ROUTE
# ----------------------
@main.route('/', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, role FROM users WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()

        if result is None:
            error = "User not found"
            return render_template("login.html", error=error)

        # ✅ Everything must be inside this block
        username, stored_hash, role = result
        stored_hash = stored_hash.encode('utf-8')

        # 🔒 TIME-BASED LOCK CHECK
        if email in failed_attempts:
            lock_time = failed_attempts[email].get('lock_time')

            if lock_time and datetime.now() < lock_time:
                remaining = (lock_time - datetime.now()).seconds
                error = f"Account locked. Try again in {remaining} seconds"
                return render_template("login.html", error=error)

            if lock_time and datetime.now() >= lock_time:
                failed_attempts[email] = {"count": 0}

        # 🔐 PASSWORD CHECK
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):

            # ✅ Reset attempts
            if email in failed_attempts:
                del failed_attempts[email]

            session['email'] = email
            session['username'] = username
            session['role'] = role

            if role == 'Admin':
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.user_dashboard'))

        else:
            error = "Incorrect password"

            # ❌ Increase attempts
            if email in failed_attempts:
                failed_attempts[email]['count'] += 1
            else:
                failed_attempts[email] = {"count": 1}

            # 🔒 Lock after 3 attempts
            if failed_attempts[email]['count'] >= 3:
                failed_attempts[email]['lock_time'] = datetime.now() + timedelta(minutes=5)

            # ❗ VERY IMPORTANT
            return render_template("login.html", error=error)

    return render_template("login.html", error=error)

@main.route('/dashboard')
@login_required
def dashboard():
    return f"Welcome {session['username']}!"

@main.route('/logout')
def logout():
    session.clear()
    return "Logged out ✅"

from datetime import datetime

@main.route('/admin/dashboard')
@login_required
@role_required('Admin')
def admin_dashboard():
    # Fetch all users from the database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users")
    users_list = cursor.fetchall()
    conn.close()

    # Prepare failed attempts with remaining time
    attempts_data = {}

    for email, data in failed_attempts.items():
        remaining = None

        if data.get('lock_time'):
            if datetime.now() < data['lock_time']:
                remaining = (data['lock_time'] - datetime.now()).seconds

        attempts_data[email] = {
            "count": data['count'],
            "remaining": remaining
        }

    return render_template(
        "admin_dashboard.html",
        users=users_list,
        attempts_data=attempts_data
    )
    
    # Render a template showing all users
    return render_template("admin_dashboard.html", users=users_list, failed_attempts=failed_attempts)

@main.route('/user/dashboard')
@login_required
@role_required('User')
def user_dashboard():
    return render_template("user_dashboard.html", username=session['username'])