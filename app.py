from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import random
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from dotenv import load_dotenv

password = "your_admin_password"  # Example password
hashed_password = generate_password_hash(password)

print("Hashed Password:", hashed_password)

app = Flask(__name__)
app.secret_key = "royal_secret_key"

# ==== CONFIGURATION ====
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join('static', 'uploads')
QR_FOLDER = os.path.join('static', 'qr')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER'] = QR_FOLDER

# ==== DATABASE SETUP ====
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ==== MODELS ====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=False)
    photo = db.Column(db.String(200), nullable=True)  # Profile photo path
    weddings = db.relationship('Wedding', backref='user', lazy=True)

class Wedding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bride = db.Column(db.String(100), nullable=False)
    groom = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    culture = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    guests = db.relationship('Guest', backref='wedding', lazy=True)

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    passport = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    wedding_id = db.Column(db.Integer, db.ForeignKey('wedding.id'))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    media = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_email = db.Column(db.String(120), nullable=True)  # For delete permission

# ==== OTP MANAGEMENT ====
import smtplib
from email.message import EmailMessage
import random
from datetime import datetime, timedelta

otp_storage = {}

def send_otp(email):
    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=2)
    
    otp_storage[email] = {
    'otp': otp,
    'timestamp': datetime.now(),
    'expiry': expiry
    }

    msg = EmailMessage()
    msg['Subject'] = 'Your OTP Verification Code'
    msg['From'] = os.environ.get('EMAIL_USER')
    msg['To'] = email
    msg.set_content(f'Your OTP is: {otp}\nIt will expire in 2 minutes.')
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASS'))
            smtp.send_message(msg)
        print("OTP sent successfully!")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

    
def verify_otp(email, entered_otp):
    if email not in otp_storage:
        return False, "No OTP sent to this email."
    
    record = otp_storage[email]
    if datetime.now() > record['expiry']:
        return False, "OTP expired."
    
    if entered_otp == record['otp']:
        return True, "OTP verified successfully."
    else:
        return False, "Invalid OTP."

# ==== ROUTES ====
@app.route('/')
def home():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    return render_template('home.html', user=user, comments=comments)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        role = request.form['role']
        mobile = request.form['mobile']

        if password != confirm:
            message = "Passwords do not match."
        elif User.query.filter_by(email=email).first():
            message = "Email already exists."
        elif User.query.filter_by(mobile=mobile).first():
            message = "Mobile number already exists."
        else:
            hashed_password = generate_password_hash(password)
            if send_otp(email):  # Email वर OTP पाठवा
                session['temp_user'] = {'email': email, 'password': hashed_password, 'role': role, 'mobile': mobile}
                flash("OTP sent to your email.")
                return redirect('/verify_otp')
            else:
                message = "Error sending OTP."
    return render_template('signup.html', message=message)

@app.route('/verify_mobile_otp', methods=['GET', 'POST'])
def verify_mobile_otp():
    if 'temp_user' not in session:
        return redirect('/signup')
    message = ""
    mobile = session['temp_user']['mobile']
    otp_data = otp_storage.get(mobile)

    if not otp_data:
        message = "OTP expired or not sent. Please signup again."
        return render_template('verify_otp.html', message=message, remaining_seconds=0)

    time_passed = (datetime.now() - otp_data['timestamp']).total_seconds()
    remaining_seconds = max(0, 120 - int(time_passed))

    if request.method == 'POST':
        user_otp = request.form['otp']
        if time_passed > 120:
            otp_storage.pop(mobile, None)
            session.pop('temp_user', None)
            message = "OTP expired. Please signup again."
        elif user_otp == otp_data['otp']:
            new_user = User(**session['temp_user'])
            db.session.add(new_user)
            db.session.commit()
            otp_storage.pop(mobile, None)
            session.pop('temp_user')
            flash("Account created successfully!")
            return redirect('/login')
        else:
            message = "Invalid OTP."
    return render_template('verify_otp.html', message=message, remaining_seconds=remaining_seconds)

@app.route('/send-otp', methods=['POST'])
def send_otp_route():
    email = request.form['email']
    otp = send_otp(email)  # ही function तू आधी define केली आहेस
    session['reset_email'] = email
    session['otp'] = otp
    flash("OTP sent to your email", "info")
    return redirect(url_for('forgot_password'))  # किंवा ज्या page वर जायचंय तिकडे redirect करा
  # किंवा ज्या page वर जायचंय तिकडे redirect करा

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'temp_user' not in session:
        return redirect('/signup')
    message = ""
    email = session['temp_user']['email']
    otp_data = otp_storage.get(email)

    if not otp_data:
        message = "OTP expired or not sent. Please signup again."
        return render_template('verify_otp.html', message=message, remaining_seconds=0)

    # Calculate remaining time
    time_passed = (datetime.now() - otp_data['timestamp']).total_seconds()
    remaining_seconds = max(0, 120 - int(time_passed))

    if request.method == 'POST':
        user_otp = request.form['otp']

        if time_passed > 120:
            otp_storage.pop(email, None)
            session.pop('temp_user', None)
            message = "OTP expired. Please signup again."
        elif user_otp == otp_data['otp']:
            new_user = User(**session['temp_user'])
            db.session.add(new_user)
            db.session.commit()
            otp_storage.pop(email, None)
            session.pop('temp_user')
            flash("Account created successfully!")
            return redirect('/login')
        else:
            message = "Invalid OTP."
    return render_template('verify_otp.html', message=message, remaining_seconds=remaining_seconds)


@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    if 'temp_user' not in session:
        return redirect('/signup')
    
    email = session['temp_user']['email']
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = {
        'otp': otp,
        'timestamp': datetime.now(),
        'expiry': datetime.now() + timedelta(minutes=2)
    }
    send_otp(email)  # Email वर OTP पुन्हा पाठवा
    print(f"[Resent OTP for {email}]: {otp}")

    flash("OTP has been resent. Please check your email.")
    return redirect('/verify_otp')

from flask import Flask, render_template, request, redirect, flash
import random


# In-memory OTP storage (for demo purpose only)
otp_storage = {}

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        otp_entered = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # STEP 1: Send OTP
        if email and not otp_entered and not new_password:
            generated_otp = str(random.randint(100000, 999999))
            otp_storage[email] = {'otp': generated_otp}
            send_otp(email)  # Email वर OTP पाठवा
            print(f"OTP sent to {email}: {generated_otp}")
            return render_template('forgot_password.html', show_otp=True, email=email, message="OTP sent to your email.")

        # STEP 2: Verify OTP
        elif otp_entered and email and not new_password:
            if otp_storage.get(email) and otp_storage[email]['otp'] == otp_entered:
                return render_template('forgot_password.html', show_reset=True, email=email)
            else:
                return render_template('forgot_password.html', show_otp=True, email=email, message="Invalid OTP.")

        # STEP 3: Reset Password
        elif new_password and confirm_password and email:
            if new_password != confirm_password:
                return render_template('forgot_password.html', show_reset=True, email=email, message="Passwords do not match.")
            # इथे पासवर्ड DB मध्ये update करा
            user = User.query.filter_by(email=email).first()
            if user:
                user.password = new_password  # Note: Production मध्ये hashing वापरा
                db.session.commit()
                flash("Password reset successful! Please log in.")
                return redirect('/login')
            else:
                return render_template('forgot_password.html', show_reset=True, email=email, message="User not found.")

    # GET method
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if 'otp' not in session or 'email' not in session:
            flash('Session expired. Please start from Forgot Password.', 'error')
            return redirect(url_for('forgot_password'))

        if otp != session['otp']:
            return render_template('reset_password.html', error='Invalid OTP.')

        if new_password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match.')

        # User शोधा आणि पासवर्ड अपडेट करा
        user = User.query.filter_by(email=session['email']).first()
        if user:
            user.password = new_password  # Note: Production मध्ये password hashing वापरा!
            db.session.commit()
        
        session.pop('otp', None)
        session.pop('email', None)

        return render_template('reset_password.html', success='Password reset successfully!')

    return render_template('reset_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if send_otp(user.email):
                session['login_email'] = email
                session['login_user_id'] = user.id
                flash("OTP sent to your email.")
                return redirect('/login_verify_otp')
            else:
                message = "Error sending OTP."
        else:
            message = "Invalid credentials."
    return render_template('login.html', message=message)

@app.route('/login_verify_otp', methods=['GET', 'POST'])
def login_verify_otp():
    if 'login_email' not in session or 'login_user_id' not in session:
        return redirect('/login')
    message = ""
    user = User.query.get(session['login_user_id'])
    otp_data = otp_storage.get(user.email)
    if not otp_data:
        message = "OTP expired or not sent. Please login again."
        return render_template('verify_otp.html', message=message, remaining_seconds=0)
    time_passed = (datetime.now() - otp_data['timestamp']).total_seconds()
    remaining_seconds = max(0, 120 - int(time_passed))
    if request.method == 'POST':
        user_otp = request.form['otp']
        if time_passed > 120:
            otp_storage.pop(user.email, None)
            session.pop('login_email', None)
            session.pop('login_user_id', None)
            message = "OTP expired. Please login again."
        elif user_otp == otp_data['otp']:
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            otp_storage.pop(user.email, None)
            session.pop('login_email')
            session.pop('login_user_id')
            flash("Login successful!")
            # Redirect by role
            if user.role == 'admin' or user.role == 'register':
                return redirect('/register')
            else:
                return redirect('/guest_dashboard')
        else:
            message = "Invalid OTP."
    return render_template('verify_otp.html', message=message, remaining_seconds=remaining_seconds)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/register', methods=['GET', 'POST'])
def register():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    if request.method == 'POST':
        bride = request.form['bride']
        groom = request.form['groom']
        date = request.form['date']
        venue = request.form['venue']
        culture = request.form['culture']
        image_file = request.files['image']

        image_path = ""
        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            unique_filename = f"{bride.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            image_path = f"uploads/{unique_filename}"

        new_wedding = Wedding(
            bride=bride, groom=groom, date=date, venue=venue,
            culture=culture, image=image_path, user_id=session['user_id']
        )
        db.session.add(new_wedding)
        db.session.commit()
        return redirect('/dashboard')
    return render_template('register.html', user=user)

@app.route('/attend')
def attend():
    query = request.args.get('query', '').lower()
    weddings = Wedding.query.all()
    if query:
        weddings = [w for w in weddings if query in w.venue.lower() or query in w.culture.lower() or query in str(w.date)]
    weddings.sort(key=lambda w: datetime.strptime(w.date, '%Y-%m-%d'))
    return render_template('attend.html', weddings=weddings)

@app.route('/attend/<int:wedding_id>', methods=['POST'])
def attend_submit(wedding_id):
    guest = Guest(
        name=request.form['fullname'],
        passport=request.form['passport'],
        email=request.form['email'],
        amount=int(request.form['amount']),
        wedding_id=wedding_id
    )
    db.session.add(guest)
    db.session.commit()
    flash("Payment Successful! You are registered as a guest.")
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    weddings = Wedding.query.filter_by(user_id=session['user_id']).all()
    all_guests = Guest.query.all()
    wedding_guest_data = []
    for wedding in weddings:
        guests = [g for g in all_guests if g.wedding_id == wedding.id]
        total_amount = sum(g.amount for g in guests)
        wedding_guest_data.append({'wedding': wedding, 'guests': guests, 'total_amount': total_amount})
    return render_template('dashboard.html', wedding_guest_data=wedding_guest_data)

@app.route('/delete_wedding/<int:wedding_id>', methods=['POST'])
def delete_wedding(wedding_id):
    if 'user_id' not in session:
        flash("Login required.")
        return redirect('/login')

    wedding = Wedding.query.get_or_404(wedding_id)
    
    if wedding.user_id != session['user_id']:
        flash("Unauthorized access.")
        return redirect('/dashboard')

    # Delete related guests
    Guest.query.filter_by(wedding_id=wedding_id).delete()

    # Delete uploaded image
    if wedding.image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(wedding.image))
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete wedding entry
    db.session.delete(wedding)
    db.session.commit()

    flash("Wedding deleted successfully.")
    return redirect('/dashboard')


@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            unique_filename = f"{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            user.photo = f"uploads/{unique_filename}"
        user.email = email
        user.mobile = mobile
        user.name = name
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect('/edit_profile')
    return render_template('edit_profile.html', user=user)

@app.route('/admin/my_weddings_guests')
def my_weddings_guests():
    if 'user_id' not in session:
        return redirect('/login')
    my_weddings = Wedding.query.filter_by(user_id=session['user_id']).all()
    all_guests = Guest.query.all()

    wedding_guest_data = []
    for wedding in my_weddings:
        guests = [g for g in all_guests if g.wedding_id == wedding.id]
        total_amount = sum(g.amount for g in guests)
        wedding_guest_data.append({'wedding': wedding, 'guests': guests, 'total_amount': total_amount})

    return render_template("my_guests.html", wedding_guest_data=wedding_guest_data)

@app.route('/guest_dashboard')
def guest_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    # Guest user ने attend केलेल्या सर्व weddings
    guest_entries = Guest.query.filter_by(email=user.email).all()
    attended_weddings = []
    for guest in guest_entries:
        wedding = Wedding.query.get(guest.wedding_id)
        attended_weddings.append({'wedding': wedding, 'guest': guest})
    return render_template('guest_dashboard.html', attended_weddings=attended_weddings, user=user)

@app.route('/add_comment', methods=['POST'])
def add_comment():
    name = request.form['name']
    comment = request.form['comment']
    media_file = request.files.get('media')
    media_filename = None
    if media_file and media_file.filename:
        media_filename = secure_filename(media_file.filename)
        media_folder = os.path.join('static', 'comments')
        if not os.path.exists(media_folder):
            os.makedirs(media_folder)
        media_path = os.path.join(media_folder, media_filename)
        media_file.save(media_path)
    user_email = session.get('email') if 'email' in session else None
    new_comment = Comment(name=name, comment=comment, media=media_filename, user_email=user_email)
    db.session.add(new_comment)
    db.session.commit()
    return redirect('/')

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if 'email' in session and comment.user_email == session['email']:
        db.session.delete(comment)
        db.session.commit()
    return redirect('/')

@app.route('/delete_all_comments')
def delete_all_comments():
    # Only allow if admin (for demo, no auth)
    Comment.query.delete()
    db.session.commit()
    return redirect('/')

# ==== MAIN ====
if __name__ == '__main__':
    load_dotenv()
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)