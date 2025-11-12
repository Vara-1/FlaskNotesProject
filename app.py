from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import timedelta

# Flask App Initialization
app = Flask(__name__)
app.secret_key = "myverysecretkey"
app.permanent_session_lifetime = timedelta(seconds=10)  # Default session timeout

# Serializer for generating secure tokens
serializer = URLSafeTimedSerializer(app.secret_key)

# Email Config
SENDER_EMAIL = "devivaraprasad67@gmail.com"
SENDER_PASSWORD = "ydud eeez zvzm nguv"  # Use Gmail App Password

# Database Connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="flaskdb"
    )

# -------------------- ROUTES --------------------

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Contact Page
@app.route('/contact')
def contact():
    return render_template('contact.html')

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash("Please fill all fields.", "danger")
            return redirect('/register')

        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM students WHERE email=%s", (email,))
        if cur.fetchone():
            flash("Email already registered.", "warning")
            cur.close()
            conn.close()
            return redirect('/register')

        cur.execute("INSERT INTO students (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_pw))
        conn.commit()
        cur.close()
        conn.close()
        flash("Registration successful! Please log in.", "success")
        return redirect('/login')

    return render_template('register.html')

# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = request.form.get('remember')  # ✅ capture "Remember Me"

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.permanent = True

            # ✅ Adjust session lifetime based on Remember Me
            if remember:
                app.permanent_session_lifetime = timedelta(seconds=10)
            else:
                app.permanent_session_lifetime = timedelta(seconds=10)

            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect('/viewnotes')
        else:
            flash("Invalid email or password.", "danger")
            return redirect('/login')

    if 'user_id' in session:
        return redirect('/viewnotes')

    return render_template('login.html')

# -------------------- FORGOT PASSWORD --------------------
@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user:
            flash("No account found with that email.", "danger")
            return redirect('/forgot')

        token = serializer.dumps(email, salt="password-reset-salt")
        reset_link = url_for('reset_password', token=token, _external=True)

        subject = "Password Reset - Notes App"
        body = f"Hi {user['username']},\n\nClick the link below to reset your password:\n{reset_link}\n\nThis link expires in 10 minutes."
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = email

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            flash("Password reset link sent to your email.", "info")
        except Exception as e:
            flash("Error sending email. Try again later.", "danger")
            print("Email error:", e)

        return redirect('/login')

    return render_template('forgot.html')

# -------------------- RESET PASSWORD --------------------
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=600)
    except (SignatureExpired, BadSignature):
        flash("The link is invalid or expired.", "danger")
        return redirect('/forgot')

    if request.method == 'POST':
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE students SET password=%s WHERE email=%s", (hashed_pw, email))
        conn.commit()
        cur.close()
        conn.close()
        flash("Password reset successful! Please log in.", "success")
        return redirect('/login')

    return render_template('reset.html')

# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

# -------------------- ADD NOTE --------------------
@app.route('/addnote', methods=['GET', 'POST'])
def addnote():
    if 'user_id' not in session:
        flash("Please log in to add a note.", "warning")
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO notes (title, content, user_id) VALUES (%s, %s, %s)",
                    (title, content, session['user_id']))
        conn.commit()
        cur.close()
        conn.close()
        flash("Note added!", "success")
        return redirect('/viewnotes')

    return render_template('addnote.html')

# -------------------- VIEW NOTES --------------------
@app.route('/viewnotes')
def viewnotes():
    if 'user_id' not in session:
        flash("Please log in to view notes.", "warning")
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    notes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('viewnotes.html', notes=notes)

# -------------------- SINGLE NOTE --------------------
@app.route('/singlenote/<int:id>')
def singlenote(id):
    if 'user_id' not in session:
        flash("Please log in to view notes.", "warning")
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    note = cur.fetchone()
    cur.close()
    conn.close()

    if not note:
        flash("Note not found.", "danger")
        return redirect('/viewnotes')

    return render_template('singlenote.html', note=note)

# -------------------- UPDATE NOTE --------------------
@app.route('/updatenote/<int:id>', methods=['GET', 'POST'])
def updatenote(id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    note = cur.fetchone()

    if not note:
        flash("Note not found.", "danger")
        return redirect('/viewnotes')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cur.execute("UPDATE notes SET title=%s, content=%s WHERE id=%s", (title, content, id))
        conn.commit()
        flash("Note updated!", "success")
        return redirect('/viewnotes')

    return render_template('updatenote.html', note=note)

# -------------------- DELETE NOTE --------------------
@app.route('/deletenote/<int:id>', methods=['POST'])
def deletenote(id):
    if 'user_id' not in session:
        flash("Please log in first.", "warning")
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes WHERE id=%s AND user_id=%s", (id, session['user_id']))
    conn.commit()
    cur.close()
    conn.close()
    flash("Note deleted!", "info")
    return redirect('/viewnotes')

# -------------------- RUN APP --------------------
if __name__ == '__main__':
    app.run(debug=True)


# CREATE TABLE students (id INT AUTO_INCREMENT PRIMARY KEY,username VARCHAR(100) NOT NULL,email VARCHAR(100) NOT NULL UNIQUE,password VARCHAR(255) NOT NULL);

# CREATE TABLE notes (id INT AUTO_INCREMENT PRIMARY KEY,title VARCHAR(255) NOT NULL,content TEXT NOT NULL,user_id INT NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (user_id) REFERENCES students(id) ON DELETE CASCADE);