from flask import current_app, url_for
from flask_mail import Message, Mail
from app import mail
from itsdangerous import URLSafeTimedSerializer
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime

def send_reset_email(user):
    """
    Send password reset email to user
    """
    token = generate_reset_token(user.email)
    msg = Message('Password Reset Request',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('auth.reset_token', token=token, _external=True)}

If you did not make this request, simply ignore this email and no changes will be made.
'''
    mail.send(msg)


def generate_reset_token(email):
    """
    Generate a secure token for password reset
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=os.getenv('SECURITY_PASSWORD_SALT', 'password-reset-salt'))


def verify_reset_token(token, expires_sec=1800):
    """
    Verify the reset token
    """
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=os.getenv('SECURITY_PASSWORD_SALT', 'password-reset-salt'),
            max_age=expires_sec
        )
        return email
    except:
        return None

mail = Mail()

def generate_donation_certificate(donation, hospital):
    """Generate a PDF certificate for blood donation."""
    try:
        buffer = BytesIO()
        
        # Create the PDF object, using BytesIO as its "file."
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Register a nice font
        try:
            font_path = os.path.join(current_app.root_path, 'static', 'fonts', 'OpenSans-Regular.ttf')
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('OpenSans', font_path))
                font_name = 'OpenSans'
            else:
                font_name = 'Helvetica'
        except:
            font_name = 'Helvetica'
        
        # Title
        c.setFont(font_name, 24)
        c.drawCentredString(width/2, height-2*inch, "Certificate of Blood Donation")
        
        # Hospital Logo (if available)
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'img', 'hospital_logo.png')
            if os.path.exists(logo_path):
                c.drawImage(logo_path, width/2-1*inch, height-4*inch, width=2*inch, height=1.5*inch)
        except:
            pass
        
        # Certificate content
        c.setFont(font_name, 14)
        
        # Donor details
        y_position = height-5*inch
        c.drawString(1*inch, y_position, f"This is to certify that")
        
        c.setFont(font_name, 16)
        y_position -= 0.5*inch
        donor_name = donation.donor.donor_profile.name if donation.donor and donation.donor.donor_profile else "Valued Donor"
        c.drawString(1*inch, y_position, f"{donor_name}")
        
        c.setFont(font_name, 14)
        y_position -= 0.5*inch
        c.drawString(1*inch, y_position, f"has donated {donation.units} unit(s) of blood (Blood Group: {donation.blood_group})")
        
        y_position -= 0.4*inch
        c.drawString(1*inch, y_position, f"at {hospital.name}")
        
        y_position -= 0.4*inch
        # Use completion_date if available, otherwise use request_date
        donation_date = donation.completion_date if donation.completion_date else donation.request_date
        c.drawString(1*inch, y_position, f"on {donation_date.strftime('%d %B, %Y')}")
        
        # Thank you message
        y_position -= 0.8*inch
        c.setFont(font_name, 12)
        c.drawString(1*inch, y_position, "Thank you for your generous contribution to saving lives!")
        
        # Hospital details
        y_position -= 1.5*inch
        c.setFont(font_name, 12)
        c.drawString(1*inch, y_position, f"Hospital Name: {hospital.name}")
        y_position -= 0.3*inch
        c.drawString(1*inch, y_position, f"Contact: {hospital.phone}")
        
        # Certificate ID and date
        c.setFont(font_name, 8)
        c.drawString(1*inch, 1*inch, f"Certificate ID: DON-{donation.id}")
        c.drawRightString(width-1*inch, 1*inch, f"Generated on: {datetime.utcnow().strftime('%d %B, %Y')}")
        
        # Border
        c.setStrokeColor(colors.red)
        c.setLineWidth(3)
        c.rect(0.5*inch, 0.5*inch, width-1*inch, height-1*inch)
        
        # Save the PDF
        c.save()
        
        # Get the value of the BytesIO buffer and write it to the response
        buffer.seek(0)
        return buffer
    except Exception as e:
        current_app.logger.error(f"Error generating certificate: {str(e)}")
        raise
