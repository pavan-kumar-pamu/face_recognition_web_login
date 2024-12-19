from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import cv2
import os
import face_recognition
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database and image folder setup
DATABASE = 'users.db'
USER_PHOTOS_FOLDER = 'usersphotos'
os.makedirs(USER_PHOTOS_FOLDER, exist_ok=True)

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        face_path TEXT NOT NULL
                    )''')
        conn.commit()

init_db()

@app.route('/')
def login():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); width: 300px; text-align: center; }
            input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
            button { background-color: #28a745; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
            button:hover { background-color: #218838; }
            .register { margin-top: 10px; font-size: 14px; }
            .face-login { background-color: #007bff; color: white; margin-top: 10px; }
            .face-login:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Login</h2>
            <form action="/login" method="post">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <form action="/face-login" method="post">
                <button type="submit" class="face-login">Login with Face</button>
            </form>
            <p class="register">Don't have an account? <a href="/register">Register here</a></p>
        </div>
    </body>
    </html>
    '''

@app.route('/login', methods=['POST'])
def login_user():
    username = request.form['username']
    password = request.form['password']
    
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()

    if user:
        session['username'] = username
        return redirect(url_for('home'))
    else:
        flash('Invalid credentials')
        return redirect(url_for('login'))

@app.route('/face-login', methods=['POST'])
def face_login():
    webcam = cv2.VideoCapture(0)
    
    if not webcam.isOpened():
        flash("Error accessing webcam")
        return redirect(url_for('login'))

    ret, frame = webcam.read()
    if ret:
        temp_image_path = 'temp.jpg'
        cv2.imwrite(temp_image_path, frame)
        webcam.release()
        
        try:
            input_face = face_recognition.load_image_file(temp_image_path)
            input_encoding = face_recognition.face_encodings(input_face)[0]
        except:
            flash("Face not recognized. Try again.")
            return redirect(url_for('login'))

        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT username, face_path FROM users")
            users = c.fetchall()

        for user in users:
            stored_image = face_recognition.load_image_file(user[1])
            stored_encoding = face_recognition.face_encodings(stored_image)[0]

            if face_recognition.compare_faces([stored_encoding], input_encoding)[0]:
                session['username'] = user[0]
                os.remove(temp_image_path)
                return redirect(url_for('home'))

    flash("No match found. Please register.")
    return redirect(url_for('login'))

@app.route('/register')
def register():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Register</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); width: 300px; text-align: center; }
            input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
            button { background-color: #007bff; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
            button:hover { background-color: #0056b3; }
            .capture { margin-top: 10px; background-color: #28a745; }
            .capture:hover { background-color: #218838; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Register</h2>
            <form action="/register" method="post">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit" class="capture">Capture Face</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/register', methods=['POST'])
def register_user():
    username = request.form['username']
    password = request.form['password']
    
    webcam = cv2.VideoCapture(0)
    
    if not webcam.isOpened():
        flash("Error accessing webcam")
        return redirect(url_for('register'))

    ret, frame = webcam.read()
    if ret:
        filename = secure_filename(f"{username}.jpg")
        face_path = os.path.join(USER_PHOTOS_FOLDER, filename)
        cv2.imwrite(face_path, frame)
        webcam.release()

        with sqlite3.connect(DATABASE) as conn:
            try:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password, face_path) VALUES (?, ?, ?)",
                          (username, password, face_path))
                conn.commit()
            except sqlite3.IntegrityError:
                flash("Username already exists")
                return redirect(url_for('register'))

        flash("Registration successful. Please login.")
        return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'username' in session:
        return '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Home</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); width: 300px; text-align: center; }
                button { background-color: #dc3545; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }
                button:hover { background-color: #c82333; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Welcome, ''' + session['username'] + '''</h2>
                <form action="/logout" method="post">
                    <button type="submit">Logout</button>
                </form>
            </div>
        </body>
        </html>
        '''
    return redirect(url_for('login'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
