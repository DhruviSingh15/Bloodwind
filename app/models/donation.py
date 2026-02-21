from app import db
from datetime import datetime, timedelta

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital_profile.id'), nullable=True)
    blood_group = db.Column(db.String(5), nullable=False)
    units = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected, completed, cancelled
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    approval_date = db.Column(db.DateTime, nullable=True)
    rejection_date = db.Column(db.DateTime, nullable=True)
    completion_date = db.Column(db.DateTime, nullable=True)
    cancellation_date = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships - Using back_populates to define bidirectional relationships
    donor = db.relationship('User', foreign_keys=[donor_id], back_populates='donations')
    hospital = db.relationship('HospitalProfile', foreign_keys=[hospital_id], back_populates='hospital_donations')
    
    def __repr__(self):
        return f"Donation('{self.blood_group}', '{self.status}', '{self.request_date}')"
    
    def mark_approved(self):
        self.status = 'approved'
        self.approval_date = datetime.utcnow()
    
    def mark_rejected(self):
        self.status = 'rejected'
        self.rejection_date = datetime.utcnow()
    
    def mark_completed(self):
        self.status = 'completed'
        self.completion_date = datetime.utcnow()
    
    def mark_cancelled(self):
        self.status = 'cancelled'
        self.cancellation_date = datetime.utcnow()


class BloodInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital_profile.id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    units = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('hospital_id', 'blood_group', name='unique_blood_inventory'),)
    
    def __repr__(self):
        return f"BloodInventory('{self.blood_group}', '{self.units} units')"


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False, default='Notification')
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # donation_approved, donation_rejected, etc.
    delivery_method = db.Column(db.String(20), nullable=False, default='system')  # sms, email, system
    is_sent = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    related_entity_type = db.Column(db.String(50), nullable=True)  # donation, user, etc.
    related_entity_id = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f"Notification('{self.title}', '{self.notification_type}', '{self.is_sent}', '{self.created_at}')"
    
    def mark_as_read(self):
        self.is_read = True
        db.session.commit()
    
    def mark_as_sent(self):
        self.is_sent = True
        self.sent_at = datetime.utcnow()
        db.session.commit()
