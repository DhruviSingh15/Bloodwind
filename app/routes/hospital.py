from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, send_file
from flask_login import login_required, current_user
from app import db, csrf
from app.models.user import User, HospitalProfile
from app.models.donation import Donation, BloodInventory, Notification
from app.forms.hospital_forms import BloodRequestForm, UpdateHospitalProfileForm
from app.utils.sms import send_blood_request_notification
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFError
import csv
from io import StringIO
from sqlalchemy import func
import os
from flask_mail import Message
from flask import current_app
from app.utils.email import generate_donation_certificate
from app.utils.email import mail

hospital = Blueprint('hospital', __name__)

@hospital.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get blood inventory and ensure all 8 blood groups are present
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    raw_inventory = BloodInventory.query.filter_by(hospital_id=hospital_profile.id).all()
    inventory_dict = {inv.blood_group: inv for inv in raw_inventory}
    class DummyInv:
        def __init__(self, blood_group):
            self.blood_group = blood_group
            self.units = 0
    inventory = [inventory_dict.get(bg, DummyInv(bg)) for bg in blood_groups]
    
    # Get pending donation requests
    pending_donations = Donation.query.filter_by(
        hospital_id=hospital_profile.id,
        status='pending'
    ).order_by(Donation.request_date.desc()).limit(10).all()
    
    # Get recent approved and completed donations
    recent_donations = Donation.query.filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed'])
    ).order_by(
        Donation.approval_date.desc() if Donation.status == 'approved' else Donation.completion_date.desc()
    ).limit(5).all()
    
    return render_template('hospital/dashboard.html', 
                          title='Hospital Dashboard',
                          hospital=hospital_profile,
                          inventory=inventory,
                          pending_donations=pending_donations,
                          recent_donations=recent_donations)


@hospital.route('/donations/pending')
@login_required
def pending_donations():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get all pending donations with pagination
    page = request.args.get('page', 1, type=int)
    donations = Donation.query.filter_by(
        hospital_id=hospital_profile.id,
        status='pending'
    ).order_by(Donation.request_date.desc()).paginate(page=page, per_page=10)
    
    return render_template('hospital/pending_donations.html',
                          title='Pending Donations',
                          donations=donations)


@hospital.route('/donation/<int:donation_id>/approve', methods=['POST'])
@login_required
def approve_donation(donation_id):
    try:
        if not current_user.is_hospital():
            abort(403)
        
        # Get hospital profile
        hospital_profile = current_user.hospital_profile
        
        # Get donation
        donation = Donation.query.get_or_404(donation_id)
        
        # Check if donation belongs to this hospital
        if donation.hospital_id != hospital_profile.id:
            abort(403)
        
        # Check if donation is pending
        if donation.status != 'pending':
            flash('This donation request has already been processed.', 'warning')
            return redirect(url_for('hospital.pending_donations'))
    except CSRFError:
        flash('CSRF token is missing or invalid. Please try again.', 'danger')
        return redirect(url_for('hospital.pending_donations'))
    
    # Update donation status
    donation.status = 'approved'
    donation.approval_date = datetime.utcnow()
    
    # Update donor's last donation date
    donor = User.query.get(donation.donor_id)
    donor.donor_profile.last_donation_date = datetime.utcnow()
    
    # Update blood inventory
    inventory = BloodInventory.query.filter_by(
        hospital_id=hospital_profile.id,
        blood_group=donation.blood_group
    ).first()
    
    if inventory:
        inventory.units += donation.units
    else:
        # Create new inventory entry if it doesn't exist
        inventory = BloodInventory(
            hospital_id=hospital_profile.id,
            blood_group=donation.blood_group,
            units=donation.units
        )
        db.session.add(inventory)
    
    # Create notification for donor
    notification = Notification(
        user_id=donation.donor_id,
        message=f"Your blood donation request has been approved by {hospital_profile.name}. Thank you for saving lives!",
        notification_type='system'
    )
    db.session.add(notification)
    
    try:
        db.session.commit()
        flash('Donation request has been approved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving donation: {str(e)}', 'danger')
    
    return redirect(url_for('hospital.pending_donations'))


@hospital.route('/donation/<int:donation_id>/reject', methods=['POST'])
@login_required
def reject_donation(donation_id):
    try:
        if not current_user.is_hospital():
            abort(403)
        
        # Get hospital profile
        hospital_profile = current_user.hospital_profile
        
        # Get donation
        donation = Donation.query.get_or_404(donation_id)
        
        # Check if donation belongs to this hospital
        if donation.hospital_id != hospital_profile.id:
            abort(403)
        
        # Check if donation is pending
        if donation.status != 'pending':
            flash('This donation request has already been processed.', 'warning')
            return redirect(url_for('hospital.pending_donations'))
    except CSRFError:
        flash('CSRF token is missing or invalid. Please try again.', 'danger')
        return redirect(url_for('hospital.pending_donations'))
    
    # Update donation status
    donation.status = 'rejected'
    donation.rejection_date = datetime.utcnow()
    
    # Send notification to donor
    notification = Notification(
        user_id=donation.donor_id,
        title='Donation Request Rejected',
        message=f'Your donation request to {hospital_profile.name} has been rejected.',
        notification_type='donation_rejected',
        delivery_method='system',
        related_entity_type='donation',
        related_entity_id=donation.id
    )
    
    db.session.add(notification)
    
    try:
        db.session.commit()
        flash('Donation request has been rejected.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting donation: {str(e)}', 'danger')
    
    return redirect(url_for('hospital.pending_donations'))


@hospital.route('/donation/<int:donation_id>/complete', methods=['POST'])
@login_required
def mark_completed(donation_id):
    try:
        if not current_user.is_hospital():
            abort(403)
        
        # Get hospital profile
        hospital_profile = current_user.hospital_profile
        
        # Get donation
        donation = Donation.query.get_or_404(donation_id)
        
        # Check if donation belongs to this hospital
        if donation.hospital_id != hospital_profile.id:
            abort(403)
        
        # Check if donation is approved
        if donation.status != 'approved':
            flash('Only approved donations can be marked as completed.', 'warning')
            return redirect(url_for('hospital.donation_history'))
    except CSRFError:
        flash('CSRF token is missing or invalid. Please try again.', 'danger')
        return redirect(url_for('hospital.donation_history'))
    
    # Update donation status
    donation.status = 'completed'
    donation.completion_date = datetime.utcnow()
    
    # Update donor's last donation date
    donor = User.query.get(donation.donor_id)
    if donor and donor.donor_profile:
        donor.donor_profile.last_donation_date = datetime.utcnow()
        # Set next eligible donation date (6 months from now)
        donor.donor_profile.next_donation_date = datetime.utcnow() + timedelta(days=180)
    
    # Send notification to donor
    notification = Notification(
        user_id=donation.donor_id,
        title='Donation Completed',
        message=f'Your donation at {hospital_profile.name} has been marked as completed. Thank you for your contribution!',
        notification_type='donation_completed',
        delivery_method='system',
        related_entity_type='donation',
        related_entity_id=donation.id
    )
    
    db.session.add(notification)
    
    try:
        db.session.commit()
        flash('Donation has been marked as completed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing donation: {str(e)}', 'danger')
    
    return redirect(url_for('hospital.donation_history'))


@hospital.route('/blood/request', methods=['GET', 'POST'])
@login_required
def request_blood():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    form = BloodRequestForm()
    
    if form.validate_on_submit():
        # Send blood request notification to eligible donors
        success_count, failed_count = send_blood_request_notification(
            hospital_profile.id,
            form.blood_group.data,
            form.units.data
        )
        
        flash(f'Blood request broadcast sent to {success_count} eligible donors!', 'success')
        if failed_count > 0:
            flash(f'Failed to send notification to {failed_count} donors.', 'warning')
        
        return redirect(url_for('hospital.dashboard'))
    
    return render_template('hospital/request_blood.html',
                          title='Request Blood Donation',
                          form=form)


@hospital.route('/inventory')
@login_required
def inventory():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Define all blood groups
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Get blood inventory
    raw_inventory = BloodInventory.query.filter_by(hospital_id=hospital_profile.id).all()
    inventory_dict = {item.blood_group: item for item in raw_inventory}
    
    # Ensure all blood groups exist
    inventory = []
    for blood_group in blood_groups:
        if blood_group in inventory_dict:
            inventory.append(inventory_dict[blood_group])
        else:
            # Create a new inventory item if it doesn't exist
            new_item = BloodInventory(
                hospital_id=hospital_profile.id,
                blood_group=blood_group,
                units=0,
                last_updated=datetime.utcnow()
            )
            db.session.add(new_item)
            inventory.append(new_item)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('Error initializing inventory items.', 'danger')
        current_app.logger.error(f"Error initializing inventory: {str(e)}")
    
    # Prepare chart data
    chart_data = {
        'blood_groups': blood_groups,
        'units': [inventory_dict.get(bg, type('DummyInv', (), {'units': 0})).units for bg in blood_groups]
    }
    
    current_app.logger.info(f"Chart data: {chart_data}")  # Add logging
    
    return render_template('hospital/inventory.html',
                          title='Blood Inventory',
                          inventory=inventory,
                          chart_data=chart_data)


@hospital.route('/inventory/update/<int:inventory_id>', methods=['POST'])
@login_required
def update_inventory(inventory_id):
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get inventory item
    inventory_item = BloodInventory.query.filter_by(id=inventory_id, hospital_id=hospital_profile.id).first_or_404()
    
    # Update units
    units = request.form.get('units', type=int)
    if units is not None and units >= 0:
        inventory_item.units = units
        inventory_item.last_updated = datetime.utcnow()
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'{inventory_item.blood_group} inventory updated successfully!',
                'data': {
                    'id': inventory_item.id,
                    'blood_group': inventory_item.blood_group,
                    'units': inventory_item.units,
                    'last_updated': inventory_item.last_updated.strftime('%d %b, %Y %H:%M')
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error updating inventory: {str(e)}'
            }), 500
    else:
        return jsonify({
            'success': False,
            'message': 'Invalid units value. Please enter a positive number.'
        }), 400


@hospital.route('/donations/pending/count')
@login_required
def pending_donations_count():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Count pending donations
    count = Donation.query.filter_by(hospital_id=hospital_profile.id, status='pending').count()
    
    return jsonify({'count': count})


@hospital.route('/donations/export-csv')
@login_required
def export_donations_csv():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    blood_group = request.args.get('blood_group', 'all')
    
    # Build query
    query = Donation.query.filter_by(hospital_id=hospital_profile.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    if blood_group != 'all':
        query = query.filter_by(blood_group=blood_group)
    
    # Order by date
    donations = query.order_by(Donation.request_date.desc()).all()
    
    # Create CSV file in memory
    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers
    cw.writerow(['Donation ID', 'Donor Name', 'Donor Email', 'Blood Group', 'Units', 
                 'Status', 'Request Date', 'Approval Date', 'Completion Date', 'Notes'])
    
    # Write data
    for donation in donations:
        cw.writerow([
            donation.id,
            donation.donor.donor_profile.name,
            donation.donor.email,
            donation.blood_group,
            donation.units,
            donation.status,
            donation.request_date.strftime('%Y-%m-%d %H:%M:%S'),
            donation.approval_date.strftime('%Y-%m-%d %H:%M:%S') if donation.approval_date else '',
            donation.completion_date.strftime('%Y-%m-%d %H:%M:%S') if donation.completion_date else '',
            donation.notes or ''
        ])
    
    # Create response
    output = si.getvalue()
    si.close()
    
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'donation_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@hospital.route('/donations/statistics')
@login_required
def get_donation_statistics():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Calculate total donations and units
    total_stats = db.session.query(
        func.count(Donation.id).label('total_count'),
        func.sum(Donation.units).label('total_units')
    ).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed'])
    ).first()
    
    # Calculate this month's donations
    first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = db.session.query(
        func.count(Donation.id).label('month_count'),
        func.sum(Donation.units).label('month_units')
    ).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed']),
        Donation.request_date >= first_day_of_month
    ).first()
    
    # Calculate approval rate
    total_requests = db.session.query(func.count(Donation.id)).filter(
        Donation.hospital_id == hospital_profile.id
    ).scalar()
    
    approved_requests = db.session.query(func.count(Donation.id)).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed'])
    ).scalar()
    
    approval_rate = round((approved_requests / total_requests * 100) if total_requests > 0 else 0, 1)
    
    stats = {
        'total_donations': total_stats.total_count or 0,
        'total_units': total_stats.total_units or 0,
        'month_donations': this_month.month_count or 0,
        'month_units': this_month.month_units or 0,
        'approval_rate': approval_rate
    }
    
    return jsonify(stats)


@hospital.route('/donations/history')
@login_required
def donation_history():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    blood_group = request.args.get('blood_group', 'all')
    
    # Build query
    query = Donation.query.filter_by(hospital_id=hospital_profile.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    if blood_group != 'all':
        query = query.filter_by(blood_group=blood_group)
    
    # Get total count for pagination
    total = query.count()
    per_page = 10
    
    # Get paginated results
    donations = query.order_by(Donation.request_date.desc()).paginate(page=page, per_page=per_page)
    
    # Calculate statistics
    total_stats = db.session.query(
        func.count(Donation.id).label('total_count'),
        func.sum(Donation.units).label('total_units')
    ).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed'])
    ).first()
    
    # Calculate this month's donations
    first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = db.session.query(
        func.count(Donation.id).label('month_count'),
        func.sum(Donation.units).label('month_units')
    ).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed']),
        Donation.request_date >= first_day_of_month
    ).first()
    
    # Calculate approval rate
    total_requests = db.session.query(func.count(Donation.id)).filter(
        Donation.hospital_id == hospital_profile.id
    ).scalar()
    
    approved_requests = db.session.query(func.count(Donation.id)).filter(
        Donation.hospital_id == hospital_profile.id,
        Donation.status.in_(['approved', 'completed'])
    ).scalar()
    
    approval_rate = round((approved_requests / total_requests * 100) if total_requests > 0 else 0, 1)
    
    return render_template('hospital/donation_history.html',
                          title='Donation History',
                          donations=donations,
                          current_status=status,
                          current_blood_group=blood_group,
                          total_donations=total,
                          stats={
                              'total_donations': total_stats.total_count or 0,
                              'total_units': total_stats.total_units or 0,
                              'month_donations': this_month.month_count or 0,
                              'month_units': this_month.month_units or 0,
                              'approval_rate': approval_rate
                          })


@hospital.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if not current_user.is_hospital():
        abort(403)
    
    form = UpdateHospitalProfileForm()
    hospital_profile = current_user.hospital_profile
    
    if form.validate_on_submit():
        hospital_profile.name = form.name.data
        hospital_profile.phone = form.phone.data
        hospital_profile.address = form.address.data
        hospital_profile.pincode = form.pincode.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('hospital.profile'))
    elif request.method == 'GET':
        form.name.data = hospital_profile.name
        form.phone.data = hospital_profile.phone
        form.address.data = hospital_profile.address
        form.pincode.data = hospital_profile.pincode
    
    return render_template('hospital/profile.html', 
                         title='Hospital Profile',
                         form=form,
                         hospital=hospital_profile)


@hospital.route('/inventory/chart-data')
@login_required
def inventory_chart_data():
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Define all blood groups
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    # Get blood inventory
    raw_inventory = BloodInventory.query.filter_by(hospital_id=hospital_profile.id).all()
    inventory_dict = {item.blood_group: item for item in raw_inventory}
    
    # Prepare data for charts ensuring all blood groups are present
    units = [inventory_dict.get(bg, type('DummyInv', (), {'units': 0})).units for bg in blood_groups]
    
    # Log the data being sent
    current_app.logger.info(f"Sending chart data - groups: {blood_groups}, units: {units}")
    
    return jsonify({
        'groups': blood_groups,
        'units': units
    })


@hospital.route('/donation/<int:donation_id>/generate-certificate', methods=['POST'])
@login_required
def generate_certificate(donation_id):
    if not current_user.is_hospital():
        abort(403)
    
    # Get hospital profile
    hospital_profile = current_user.hospital_profile
    
    # Get donation
    donation = Donation.query.get_or_404(donation_id)
    
    # Check if donation belongs to this hospital
    if donation.hospital_id != hospital_profile.id:
        abort(403)
    
    # Check if donation is completed
    if donation.status != 'completed':
        flash('Only completed donations can have certificates generated.', 'warning')
        return redirect(url_for('hospital.donation_history'))
    
    try:
        # Generate certificate PDF
        certificate_pdf = generate_donation_certificate(donation, hospital_profile)
        
        # Save certificate to a temporary file
        temp_filename = f'donation_certificate_{donation.id}.pdf'
        certificate_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
        
        # Ensure upload folder exists
        os.makedirs(os.path.dirname(certificate_path), exist_ok=True)
        
        # Save the PDF
        with open(certificate_path, 'wb') as f:
            f.write(certificate_pdf.getvalue())
        
        # Create notification for donor
        notification = Notification(
            user_id=donation.donor_id,
            title='Donation Certificate Available',
            message=f'Your donation certificate from {hospital_profile.name} is now available. Thank you for your contribution!',
            notification_type='certificate_available',
            delivery_method='email',
            related_entity_type='donation',
            related_entity_id=donation.id
        )
        
        db.session.add(notification)
        
        # Send email with certificate
        donor_email = donation.donor.email
        donor_name = donation.donor.donor_profile.name if donation.donor and donation.donor.donor_profile else "Valued Donor"
        
        msg = Message(
            subject='Your Blood Donation Certificate',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[donor_email]
        )
        
        msg.body = f'''Dear {donor_name},

Thank you for your generous blood donation at {hospital_profile.name}. Your contribution helps save lives!

Please find your donation certificate attached to this email.

Best regards,
{hospital_profile.name}
'''
        
        with open(certificate_path, 'rb') as pdf:
            msg.attach(
                filename=temp_filename,
                content_type='application/pdf',
                data=pdf.read()
            )
        
        mail.send(msg)
        
        # Clean up the temporary file
        try:
            os.remove(certificate_path)
        except:
            pass
        
        db.session.commit()
        flash('Certificate has been generated and sent to donor\'s email.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating certificate: {str(e)}")
        try:
            if os.path.exists(certificate_path):
                os.remove(certificate_path)
        except:
            pass
        flash('Error generating certificate. Please try again or contact support if the issue persists.', 'danger')
    
    return redirect(url_for('hospital.donation_history'))
