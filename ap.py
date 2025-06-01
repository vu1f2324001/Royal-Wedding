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
        'expiry': expiry
    }
    
    msg = EmailMessage()
    msg['Subject'] = 'Your OTP Verification Code'
    msg['From'] = 'akshadavalkunde40@gmail.com'
    msg['To'] = email
    msg.set_content(f'Your OTP is: {otp}\nIt will expire in 2 minutes.')
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login('akshadavalkunde40@gmail.com', 'mexi zoru usvy viul')
            smtp.send_message(msg)
        print("OTP sent successfully!")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

# test
send_otp('valkundeakshada@gmail.com')