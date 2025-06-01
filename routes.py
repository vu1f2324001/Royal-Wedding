from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

from main import app, db
from models import User, Wedding, Guest, send_otp, verify_otp

# ==== Routes ====

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for('register'))

        user = User(email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful!")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash("Logged in successfully!")
            return redirect(url_for('dashboard'))

        flash("Invalid credentials.")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    weddings = Wedding.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', weddings=weddings)

@app.route('/create_wedding', methods=['GET', 'POST'])
def create_wedding():
    if request.method == 'POST':
        bride = request.form['bride']
        groom = request.form['groom']
        date = request.form['date']
        venue = request.form['venue']
        culture = request.form['culture']

        image = request.files['image']
        image_filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image.save(image_path)

        wedding = Wedding(
            bride=bride,
            groom=groom,
            date=date,
            venue=venue,
            culture=culture,
            image=image_filename,
            user_id=session['user_id']
        )
        db.session.add(wedding)
        db.session.commit()
        flash("Wedding created successfully!")
        return redirect(url_for('dashboard'))

    return render_template('create_wedding.html')

@app.route('/send_otp', methods=['POST'])
def send_otp_route():
    email = request.form['email']
    if send_otp(email):
        flash("OTP sent successfully.")
    else:
        flash("Failed to send OTP.")
    return redirect(url_for('register'))

@app.route('/verify_otp', methods=['POST'])
def verify_otp_route():
    email = request.form['email']
    entered_otp = request.form['otp']
    success, message = verify_otp(email, entered_otp)
    flash(message)
    return redirect(url_for('register'))