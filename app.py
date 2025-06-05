import os
import sqlite3
from flask import Flask, request, render_template, redirect, send_from_directory, url_for, flash, session, abort
from werkzeug.utils import secure_filename, safe_join

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'docx', 'txt'}
DATABASE = 'filehub.db'

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            is_private INTEGER NOT NULL,
            password TEXT
        )''')

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        files = conn.execute("SELECT filename, is_private FROM files").fetchall()
    return render_template('index.html', files=files)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        privacy = request.form.get('privacy')
        password = request.form.get('password') if privacy == 'private' else None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            with sqlite3.connect(DATABASE) as conn:
                conn.execute("INSERT INTO files (filename, is_private, password) VALUES (?, ?, ?)",
                             (filename, 1 if privacy == 'private' else 0, password))

            flash('File uploaded successfully!')
            return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/view/<filename>', methods=['GET', 'POST'])
def view_file(filename):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT is_private, password FROM files WHERE filename=?", (filename,)).fetchone()

    if row is None:
        return "File not found", 404

    is_private, correct_password = row
    if is_private:
        if request.method == 'POST':
            entered_password = request.form.get('password')
            if entered_password == correct_password:
                return render_template('view.html', filename=filename)
            else:
                flash('Incorrect password')
        return render_template('password_prompt.html', filename=filename, action='view_file')

    else:
        return render_template('view.html', filename=filename)


@app.route('/download/<filename>', methods=['GET', 'POST'])
def download_file(filename):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute("SELECT is_private, password FROM files WHERE filename=?", (filename,)).fetchone()

    if row is None:
        return "File not found", 404

    is_private, correct_password = row
    if is_private:
        if request.method == 'POST':
            entered_password = request.form.get('password')
            if entered_password == correct_password:
                return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
            else:
                flash('Incorrect password')
        return render_template('password_prompt.html', filename=filename, action='download_file')
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
