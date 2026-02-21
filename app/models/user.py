from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='donor')  # donor, hospital, admin
    phone_number = db.Column(db.String(20), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    donor_profile = db.relationship('DonorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    hospital_profile = db.relationship('HospitalProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    donations = db.relationship('Donation', 
                              foreign_keys='Donation.donor_id',
                              back_populates='donor',
                              lazy=True,
                              cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def is_donor(self):
        return self.role == 'donor'
    
    def is_hospital(self):
        return self.role == 'hospital'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def __repr__(self):
        return f"User('{self.email}', '{self.role}')"


class DonorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    last_donation_date = db.Column(db.DateTime, nullable=True)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    donation_reminders = db.Column(db.Boolean, default=True)
    eligibility_alerts = db.Column(db.Boolean, default=True)
    
    def is_eligible(self):
        # Check eligibility criteria
        if self.age < 18:
            return False, "Age must be at least 18 years"
        
        if self.weight < 50:
            return False, "Weight must be at least 50 kg"
        
        # Check if 180 days have passed since last donation
        if self.last_donation_date:
            days_since_last_donation = (datetime.utcnow() - self.last_donation_date).days
            if days_since_last_donation < 180:
                return False, f"You must wait {180 - days_since_last_donation} more days before donating again"
        
        return True, "You are eligible to donate blood"
    
    def __repr__(self):
        return f"DonorProfile('{self.name}', '{self.blood_group}')"


class HospitalProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(6), nullable=False)
    
    # Relationships
    blood_inventory = db.relationship('BloodInventory', backref='hospital', lazy=True, cascade='all, delete-orphan')
    hospital_donations = db.relationship('Donation', 
                                       foreign_keys='Donation.hospital_id',
                                       back_populates='hospital',
                                       lazy=True,
                                       cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"HospitalProfile('{self.name}', '{self.license_number}')"
