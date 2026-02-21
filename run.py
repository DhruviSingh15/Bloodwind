from app import create_app
import os

# Set development environment variables
os.environ['SECRET_KEY'] = 'dev_secret_key_for_testing'
os.environ['DATABASE_URI'] = 'sqlite:///blood_donation.db'
os.environ['SECURITY_PASSWORD_SALT'] = 'dev_password_salt'

# Add Twilio configuration
os.environ['TWILIO_ACCOUNT_SID'] = 'AC5fba1207ecc104460c1779b53e7d32b6'  # Replace with your Twilio Account SID
os.environ['TWILIO_AUTH_TOKEN'] = '4ebb5ea1e409262d5d1624b463cafc5b'    # Replace with your Twilio Auth Token
os.environ['TWILIO_PHONE_NUMBER'] = '+13648885857'            # Replace with your Twilio Phone Number

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
