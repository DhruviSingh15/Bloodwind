from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
from app.models.user import User, DonorProfile, HospitalProfile
from app.forms.auth_forms import (
    RegistrationForm, LoginForm, DonorRegistrationForm, 
    HospitalRegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
)
from app.utils.email import send_reset_email

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.role.data == 'donor':
            return redirect(url_for('auth.register_donor'))
        elif form.role.data == 'hospital':
            return redirect(url_for('auth.register_hospital'))
    
    return render_template('auth/register.html', title='Register', form=form)


@auth.route('/register/donor', methods=['GET', 'POST'])
def register_donor():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = DonorRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password, role='donor')
        db.session.add(user)
        db.session.flush()  # Flush to get the user ID
        
        donor_profile = DonorProfile(
            user_id=user.id,
            name=form.name.data,
            age=form.age.data,
            gender=form.gender.data,
            blood_group=form.blood_group.data,
            weight=form.weight.data,
            phone=form.phone.data,
            address=form.address.data,
            pincode=form.pincode.data
        )
        db.session.add(donor_profile)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register_donor.html', title='Donor Registration', form=form)


@auth.route('/register/hospital', methods=['GET', 'POST'])
def register_hospital():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = HospitalRegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password, role='hospital')
        db.session.add(user)
        db.session.flush()  # Flush to get the user ID
        
        hospital_profile = HospitalProfile(
            user_id=user.id,
            name=form.name.data,
            license_number=form.license_number.data,
            phone=form.phone.data,
            address=form.address.data,
            pincode=form.pincode.data
        )
        db.session.add(hospital_profile)
        
        # Commit to get the hospital_profile.id
        db.session.commit()
        
        # Initialize blood inventory for all blood groups
        from app.models.donation import BloodInventory
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        for bg in blood_groups:
            inventory = BloodInventory(hospital_id=hospital_profile.id, blood_group=bg, units=0)
            db.session.add(inventory)
        
        # Commit the inventory entries
        db.session.commit()
        
        flash('Your hospital account has been created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register_hospital.html', title='Hospital Registration', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            # Redirect based on user role
            if user.is_donor():
                return redirect(next_page) if next_page else redirect(url_for('donor.dashboard'))
            elif user.is_hospital():
                return redirect(next_page) if next_page else redirect(url_for('hospital.dashboard'))
            elif user.is_admin():
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    
    return render_template('auth/login.html', title='Login', form=form)


@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_request.html', title='Reset Password', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('auth.reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_token.html', title='Reset Password', form=form)
