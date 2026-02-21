from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, current_app, session
from flask_login import login_required, current_user
from app import db
from app.models.user import User, DonorProfile, HospitalProfile
from app.models.donation import Donation, BloodInventory, Notification
from app.forms.admin_forms import CreateAdminForm, ManualStockAdjustmentForm, TestSMSForm
from app.utils.sms import send_sms
from datetime import datetime, timedelta
from sqlalchemy import func
import os

admin = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get counts for dashboard
    donor_count = User.query.filter_by(role='donor').count()
    hospital_count = User.query.filter_by(role='hospital').count()
    donation_count = Donation.query.count()
    approved_donations = Donation.query.filter_by(status='approved').count()
    
    # Get recent donations
    recent_donations = Donation.query.order_by(Donation.request_date.desc()).limit(10).all()
    
    # Get blood group distribution
    blood_groups = db.session.query(
        DonorProfile.blood_group, 
        func.count(DonorProfile.blood_group)
    ).group_by(DonorProfile.blood_group).all()
    
    # Get donation trend (last 7 days)
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    
    donation_trend = []
    for date_str in dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        next_date = date_obj + timedelta(days=1)
        
        count = Donation.query.filter(
            func.date(Donation.request_date) >= date_obj,
            func.date(Donation.request_date) < next_date
        ).count()
        
        donation_trend.append({
            'date': date_str,
            'count': count
        })
    
    return render_template('admin/dashboard.html',
                          title='Admin Dashboard',
                          donor_count=donor_count,
                          hospital_count=hospital_count,
                          donation_count=donation_count,
                          approved_donations=approved_donations,
                          recent_donations=recent_donations,
                          blood_groups=blood_groups,
                          donation_trend=donation_trend)


@admin.route('/users/donors')
@login_required
@admin_required
def manage_donors():
    page = request.args.get('page', 1, type=int)
    donors = User.query.filter_by(role='donor').join(DonorProfile).paginate(page=page, per_page=15)
    
    return render_template('admin/donors.html',
                          title='Manage Donors',
                          donors=donors)


@admin.route('/users/hospitals')
@login_required
@admin_required
def manage_hospitals():
    page = request.args.get('page', 1, type=int)
    hospitals = User.query.filter_by(role='hospital').join(HospitalProfile).paginate(page=page, per_page=15)
    
    return render_template('admin/hospitals.html',
                          title='Manage Hospitals',
                          hospitals=hospitals)


@admin.route('/users/admins')
@login_required
@admin_required
def manage_admins():
    page = request.args.get('page', 1, type=int)
    admins = User.query.filter_by(role='admin').paginate(page=page, per_page=15)
    
    return render_template('admin/admins.html',
                          title='Manage Admins',
                          admins=admins)


@admin.route('/users/create_admin', methods=['GET', 'POST'])
@login_required
@admin_required
def create_admin():
    form = CreateAdminForm()
    
    if form.validate_on_submit():
        from app import bcrypt
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        user = User(
            email=form.email.data,
            password=hashed_password,
            role='admin'
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('New admin account has been created!', 'success')
        return redirect(url_for('admin.manage_admins'))
    
    return render_template('admin/create_admin.html',
                          title='Create Admin',
                          form=form)


@admin.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.email} has been deleted!', 'success')
    
    if user.role == 'donor':
        return redirect(url_for('admin.manage_donors'))
    elif user.role == 'hospital':
        return redirect(url_for('admin.manage_hospitals'))
    else:
        return redirect(url_for('admin.manage_admins'))


@admin.route('/donations')
@login_required
@admin_required
def all_donations():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    query = Donation.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    donations = query.order_by(Donation.request_date.desc()).paginate(page=page, per_page=15)
    
    return render_template('admin/donations.html',
                          title='All Donations',
                          donations=donations,
                          current_status=status)


@admin.route('/inventory')
@login_required
@admin_required
def all_inventory():
    hospital_id = request.args.get('hospital_id', type=int)
    
    if hospital_id:
        hospital = HospitalProfile.query.get_or_404(hospital_id)
        inventory = BloodInventory.query.filter_by(hospital_id=hospital_id).all()
        return render_template('admin/hospital_inventory.html',
                              title=f'Inventory - {hospital.name}',
                              hospital=hospital,
                              inventory=inventory)
    
    hospitals = HospitalProfile.query.all()
    return render_template('admin/all_inventory.html',
                          title='All Blood Inventory',
                          hospitals=hospitals)


@admin.route('/inventory/adjust/<int:inventory_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def adjust_inventory(inventory_id):
    inventory = BloodInventory.query.get_or_404(inventory_id)
    hospital = HospitalProfile.query.get_or_404(inventory.hospital_id)
    
    form = ManualStockAdjustmentForm()
    
    if form.validate_on_submit():
        if form.adjustment_type.data == 'add':
            inventory.units += form.units.data
        else:
            if inventory.units < form.units.data:
                flash('Cannot deduct more units than available in stock!', 'danger')
                return redirect(url_for('admin.adjust_inventory', inventory_id=inventory_id))
            
            inventory.units -= form.units.data
        
        # Add a note about the adjustment
        note = f"Manual {form.adjustment_type.data} of {form.units.data} units by admin {current_user.email}. Reason: {form.reason.data}"
        
        db.session.commit()
        
        flash(f'Blood inventory has been adjusted successfully! New stock: {inventory.units} units', 'success')
        return redirect(url_for('admin.all_inventory', hospital_id=hospital.id))
    
    form.blood_group.data = inventory.blood_group
    form.current_stock.data = inventory.units
    
    return render_template('admin/adjust_inventory.html',
                          title='Adjust Inventory',
                          form=form,
                          inventory=inventory,
                          hospital=hospital)


@admin.route('/analytics')
@login_required
@admin_required
def analytics():
    # Get blood group distribution
    blood_groups = db.session.query(
        DonorProfile.blood_group, 
        func.count(DonorProfile.blood_group)
    ).group_by(DonorProfile.blood_group).all()
    
    # Get donation trend (last 30 days)
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    
    donation_trend = db.session.query(
        func.date(Donation.request_date).label('date'),
        func.count(Donation.id).label('count')
    ).filter(
        Donation.request_date >= thirty_days_ago
    ).group_by(
        func.date(Donation.request_date)
    ).order_by(
        func.date(Donation.request_date)
    ).all()
    
    # Get hospital activity
    hospital_activity = db.session.query(
        HospitalProfile.name,
        func.count(Donation.id).label('donation_count')
    ).join(
        Donation, Donation.hospital_id == HospitalProfile.id
    ).filter(
        Donation.status == 'approved'
    ).group_by(
        HospitalProfile.name
    ).order_by(
        func.count(Donation.id).desc()
    ).limit(10).all()
    
    return render_template('admin/analytics.html',
                          title='System Analytics',
                          blood_groups=blood_groups,
                          donation_trend=donation_trend,
                          hospital_activity=hospital_activity)


@admin.route('/sms/test', methods=['GET', 'POST'])
@login_required
@admin_required
def test_sms():
    form = TestSMSForm()
    
    # Get Twilio configuration
    twilio_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    twilio_token = current_app.config.get('TWILIO_AUTH_TOKEN')
    twilio_number = current_app.config.get('TWILIO_PHONE_NUMBER')
    
    # Create a simple SMS history for display
    class SMSRecord:
        def __init__(self, to_number, message, success, error=None):
            self.to_number = to_number
            self.message = message
            self.success = success
            self.error = error
            self.sent_at = datetime.utcnow()
    
    # Get SMS history from session or initialize empty list
    if 'sms_history' not in session:
        session['sms_history'] = []
    
    sms_history = [SMSRecord(**record) for record in session.get('sms_history', [])]
    
    if form.validate_on_submit():
        phone_number = form.phone_number.data
        message = form.message.data
        
        # Ensure phone number has country code
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number.lstrip('0')
        
        # Send SMS
        success, result = send_sms(phone_number, message)
        
        # Add to history
        record = {
            'to_number': phone_number,
            'message': message,
            'success': success,
            'error': None if success else result
        }
        
        # Update session history (keep last 10 records)
        history = session.get('sms_history', [])
        history.insert(0, record)
        session['sms_history'] = history[:10]
        
        if success:
            flash(f'SMS sent successfully to {phone_number}!', 'success')
        else:
            flash(f'Failed to send SMS: {result}', 'danger')
        
        return redirect(url_for('admin.test_sms'))
    
    return render_template('admin/test_sms.html',
                          title='Test SMS Functionality',
                          form=form,
                          twilio_sid=twilio_sid,
                          twilio_token=twilio_token,
                          twilio_number=twilio_number,
                          sms_history=sms_history)
