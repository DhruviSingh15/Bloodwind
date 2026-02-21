from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
mail = Mail()
csrf = CSRFProtect()
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key_for_development')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///blood_donation.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY', 'default_csrf_key_for_development')
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Twilio configuration
    app.config['TWILIO_ACCOUNT_SID'] = os.getenv('TWILIO_ACCOUNT_SID')
    app.config['TWILIO_AUTH_TOKEN'] = os.getenv('TWILIO_AUTH_TOKEN')
    app.config['TWILIO_PHONE_NUMBER'] = os.getenv('TWILIO_PHONE_NUMBER')
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    migrate = Migrate(app, db)
    
    @app.after_request
    def set_csrf_cookie(response):
        if 'csrf_token' not in request.cookies:
            response.set_cookie('csrf_token', generate_csrf())
        return response
    
    # Register blueprints
    from app.routes.auth import auth
    from app.routes.donor import donor
    from app.routes.hospital import hospital
    from app.routes.admin import admin
    from app.routes.main import main
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(donor, url_prefix='/donor')
    app.register_blueprint(hospital, url_prefix='/hospital')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(main)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize scheduler for reminders but don't start it in development
    # We'll enable this later when the application is more stable
    # from app.utils.scheduler import start_scheduler
    # start_scheduler(app)
    
    return app
