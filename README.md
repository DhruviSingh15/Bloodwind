# BloodWind - Blood Donation Management System

BloodWind is a comprehensive web application that connects blood donors with hospitals, streamlining the blood donation process and helping save lives.

## Features

### Donor Module
- **Registration/Login**: Secure account creation with personal details
- **Eligibility Checker**: Automatically checks if donors meet criteria (age ≥ 18, weight ≥ 50kg, 180+ days since last donation)
- **Donation Requests**: Submit requests to donate blood to specific hospitals
- **Donation History**: View all previous donations and their statuses
- **SMS Notifications**: Get alerts when your blood type is needed
- **Donation Reminders**: Automatic reminders when you're eligible to donate again

### Hospital Module
- **Hospital Dashboard**: Secure login to manage blood donation logistics
- **Approve/Reject Donations**: Review incoming donor requests
- **Blood Request Broadcast**: Send mass SMS to eligible donors when blood is needed
- **Blood Stock Management**: Live tracking of available blood units by type
- **Donation Records**: Comprehensive record-keeping of all donations

### Admin Panel
- **User Management**: Add, delete, and manage donor and hospital accounts
- **System Analytics**: View statistics on donations, users, and blood group trends
- **Manual Stock Adjustment**: Emergency adjustments to blood inventory

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Authentication**: Flask-Login
- **SMS Integration**: Twilio
- **Scheduled Tasks**: APScheduler

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/bloodwind.git
   cd bloodwind
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables (create a .env file):
   ```
   SECRET_KEY=your_secret_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_phone
   MAIL_USERNAME=your_email@gmail.com
   MAIL_PASSWORD=your_email_password
   ```

5. Run the application:
   ```
   python run.py
   ```

6. Access the application at http://localhost:5000

## Project Structure

```
bloodwind/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   └── donation.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── donor.py
│   │   ├── hospital.py
│   │   ├── admin.py
│   │   └── main.py
│   ├── forms/
│   │   ├── auth_forms.py
│   │   ├── donor_forms.py
│   │   ├── hospital_forms.py
│   │   └── admin_forms.py
│   ├── templates/
│   │   ├── layout.html
│   │   ├── main/
│   │   ├── auth/
│   │   ├── donor/
│   │   ├── hospital/
│   │   └── admin/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── utils/
│       ├── sms.py
│       ├── email.py
│       └── scheduler.py
├── run.py
├── requirements.txt
└── README.md
```

## Security Features

- Password hashing using Bcrypt
- CSRF protection for all forms
- Role-based access control
- Input validation on both frontend and backend

## Future Enhancements

- OTP-based donor login
- Integration with real hospital databases
- Geolocation-based donor matching
- Mobile application
- Blood donation appointment scheduling

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [Bootstrap](https://getbootstrap.com/)
- [Twilio](https://www.twilio.com/)
- [Font Awesome](https://fontawesome.com/)
