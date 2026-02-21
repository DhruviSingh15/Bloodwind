from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, make_response, current_app, send_file
import csv
import tempfile
from app.utils.notifications import send_notification
from flask_login import login_required, current_user
from app import db
from app.models.user import User, DonorProfile
from app.models.donation import Donation, Notification
from app.forms.donor_forms import DonationRequestForm, UpdateProfileForm
from datetime import datetime, timedelta
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER
import os

donor = Blueprint('donor', __name__)

@donor.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_donor():
        abort(403)
    
    # Get donor profile
    donor_profile = current_user.donor_profile
    
    # Get donation history
    donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.request_date.desc()).all()
    
    # Get notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Check eligibility
    is_eligible, eligibility_message = donor_profile.is_eligible()
    
    # Calculate next eligible date
    next_eligible_date = None
    if donor_profile.last_donation_date:
        next_eligible_date = donor_profile.last_donation_date + timedelta(days=180)
        days_remaining = (next_eligible_date - datetime.utcnow()).days
    else:
        days_remaining = 0
    
    # Calculate all-time donation statistics
    completed_donations = [d for d in donations if d.status == 'completed']
    total_donations = len(donations)  # All donations
    completed_count = len(completed_donations)  # Only completed donations
    total_units = sum(d.units for d in completed_donations)  # Only count completed donations
    lives_saved = total_units * 3  # Each donation can save up to 3 lives
    
    return render_template('donor/dashboard.html', 
                          title='Donor Dashboard',
                          donor=donor_profile,
                          donations=donations[:5],  # Only show last 5 donations
                          notifications=notifications,
                          is_eligible=is_eligible,
                          eligibility_message=eligibility_message,
                          now=datetime.utcnow(),
                          next_eligible_date=next_eligible_date,
                          days_remaining=days_remaining,
                          # Statistics
                          total_donations=total_donations,
                          completed_count=completed_count,
                          total_units=total_units,
                          lives_saved=lives_saved)


@donor.route('/donation/request', methods=['GET', 'POST'])
@login_required
def request_donation():
    if not current_user.is_donor():
        abort(403)
    
    # Check eligibility
    donor_profile = current_user.donor_profile
    is_eligible, eligibility_message = donor_profile.is_eligible()
    
    if not is_eligible:
        flash(f'You are not eligible to donate blood: {eligibility_message}', 'warning')
        return redirect(url_for('donor.dashboard'))
    
    form = DonationRequestForm()
    
    # Populate hospital choices with only matching pincode hospitals
    from app.models.user import HospitalProfile
    hospitals = HospitalProfile.query.filter_by(pincode=donor_profile.pincode).all()
    
    if not hospitals:
        flash('No hospitals found in your pincode area. Please check back later.', 'info')
        return redirect(url_for('donor.dashboard'))
    
    form.hospital_id.choices = [(h.id, f"{h.name} - {h.address}") for h in hospitals]
    
    if form.validate_on_submit():
        # Verify hospital pincode again for security
        hospital = HospitalProfile.query.get(form.hospital_id.data)
        if hospital.pincode != donor_profile.pincode:
            flash('Invalid hospital selection.', 'danger')
            return redirect(url_for('donor.request_donation'))
        
        donation = Donation(
            donor_id=current_user.id,
            hospital_id=form.hospital_id.data,
            blood_group=donor_profile.blood_group,
            units=form.units.data,
            notes=form.notes.data
        )
        db.session.add(donation)
        db.session.commit()
        
        flash('Your donation request has been submitted successfully!', 'success')
        return redirect(url_for('donor.dashboard'))
    
    return render_template('donor/request_donation.html', 
                          title='Request Donation',
                          form=form)


@donor.route('/donation/history')
@login_required
def donation_history():
    if not current_user.is_donor():
        abort(403)
    
    # Get filter parameters
    status = request.args.get('status', '')
    hospital_id = request.args.get('hospital_id', '', type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build query with filters
    query = Donation.query.filter_by(donor_id=current_user.id)
    
    # Apply filters if provided
    if status:
        query = query.filter_by(status=status)
    
    if hospital_id:
        query = query.filter_by(hospital_id=hospital_id)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Donation.request_date >= start_date_obj)
        except ValueError:
            flash('Invalid start date format', 'warning')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date in results
            end_date_obj = end_date_obj + timedelta(days=1)
            query = query.filter(Donation.request_date <= end_date_obj)
        except ValueError:
            flash('Invalid end date format', 'warning')
    
    # Calculate donation statistics
    all_donations = query.all()
    total_donations = len(all_donations)  # All donations
    completed_donations = [d for d in all_donations if d.status == 'completed']
    completed_count = len(completed_donations)  # Only completed donations
    total_units = sum(d.units for d in completed_donations)  # Only count completed donations
    lives_saved = total_units * 3  # Each donation can save up to 3 lives
    
    # Get all donations with pagination
    page = request.args.get('page', 1, type=int)
    donations = query.order_by(Donation.request_date.desc()).paginate(page=page, per_page=10)
    
    # Get all hospitals for the filter dropdown
    from app.models.user import HospitalProfile
    hospitals = HospitalProfile.query.all()
    
    return render_template('donor/donation_history.html',
                          title='Donation History',
                          donations=donations,
                          hospitals=hospitals,
                          total_donations=total_donations,
                          completed_count=completed_count,
                          total_units=total_units,
                          lives_saved=lives_saved,
                          now=datetime.utcnow(),
                          timedelta=timedelta)


@donor.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if not current_user.is_donor():
        abort(403)
    
    form = UpdateProfileForm()
    
    if form.validate_on_submit():
        donor_profile = current_user.donor_profile
        donor_profile.name = form.name.data
        donor_profile.age = form.age.data
        donor_profile.gender = form.gender.data
        donor_profile.weight = form.weight.data
        donor_profile.phone = form.phone.data
        donor_profile.address = form.address.data
        donor_profile.pincode = form.pincode.data
        
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('donor.profile'))
    elif request.method == 'GET':
        # Populate form with current data
        donor_profile = current_user.donor_profile
        form.name.data = donor_profile.name
        form.age.data = donor_profile.age
        form.gender.data = donor_profile.gender
        form.weight.data = donor_profile.weight
        form.phone.data = donor_profile.phone
        form.address.data = donor_profile.address
        form.pincode.data = donor_profile.pincode
    
    return render_template('donor/profile.html', 
                          title='Profile',
                          form=form)


@donor.route('/notifications/count')
@login_required
def notification_count():
    """Return the count of unread notifications for the current user"""
    if not current_user.is_donor():
        return jsonify({'count': 0})
    
    # Count unread notifications
    unread_count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'count': unread_count})


@donor.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    if not current_user.is_donor():
        abort(403)
    
    # Handle POST request for notification preferences
    if request.method == 'POST':
        # Check if it's a JSON request (for AJAX updates)
        if request.is_json:
            data = request.get_json()
            try:
                donor_profile = current_user.donor_profile
                
                # Update notification preferences based on JSON data
                if 'email_notifications' in data:
                    donor_profile.email_notifications = data['email_notifications']
                if 'sms_notifications' in data:
                    donor_profile.sms_notifications = data['sms_notifications']
                if 'donation_reminders' in data:
                    donor_profile.donation_reminders = data['donation_reminders']
                if 'eligibility_alerts' in data:
                    donor_profile.eligibility_alerts = data['eligibility_alerts']
                
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Notification preferences updated successfully'
                })
            except Exception as e:
                current_app.logger.error(f"Error updating notification preferences: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'Error updating preferences: {str(e)}'
                }), 500
        
        # Handle form submission for notification preferences
        try:
            donor_profile = current_user.donor_profile
            
            # Update email notifications preference
            donor_profile.email_notifications = 'email_notifications' in request.form
            
            # Update SMS notifications preference
            donor_profile.sms_notifications = 'sms_notifications' in request.form
            
            # Update donation reminders preference
            donor_profile.donation_reminders = 'donation_reminders' in request.form
            
            # Update eligibility alerts preference
            donor_profile.eligibility_alerts = 'eligibility_alerts' in request.form
            
            # If user enables SMS but doesn't have a phone number, use the one from profile
            if donor_profile.sms_notifications and not current_user.phone_number:
                current_user.phone_number = donor_profile.phone
            
            db.session.commit()
            
            # Create notification about preference update
            send_notification(
                user_id=current_user.id,
                title='Notification Preferences Updated',
                message='Your notification preferences have been updated successfully.',
                notification_type='preferences_updated',
                delivery_methods=['system'],
                related_entity_type='user',
                related_entity_id=current_user.id
            )
            
            flash('Notification preferences updated successfully', 'success')
        except Exception as e:
            current_app.logger.error(f"Error updating notification preferences: {str(e)}")
            flash(f'Error updating notification preferences: {str(e)}', 'danger')
        
        return redirect(url_for('donor.notifications'))
    
    # GET request - show notifications page
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=10)
    
    # We don't automatically mark all as read anymore
    # Let the user mark individual notifications as read
    
    return render_template('donor/notifications.html',
                          title='Notifications',
                          notifications=notifications)


@donor.route('/notifications/<int:notification_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    if not current_user.is_donor():
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
        abort(403)
    
    # Get the notification
    notification = Notification.query.get_or_404(notification_id)
    
    # Check if notification belongs to this user
    if notification.user_id != current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
        abort(403)
    
    try:
        # Mark as read
        notification.is_read = True
        db.session.commit()
        
        # If it's an AJAX request, return JSON response
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Notification marked as read',
                'notification_id': notification.id
            })
        
        # For regular form submissions
        flash('Notification marked as read', 'success')
        return redirect(url_for('donor.notifications'))
    
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        
        flash('An error occurred while marking the notification as read', 'danger')
        return redirect(url_for('donor.notifications'))


def generate_certificate(donation):
    """Generate a beautiful certificate for a blood donation"""
    # Create a PDF certificate
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Set background color
    p.setFillColor(colors.white)
    p.rect(0, 0, width, height, fill=1)
    
    # Add decorative border
    p.setStrokeColor(colors.red)
    p.setLineWidth(2)
    p.rect(1*cm, 1*cm, width - 2*cm, height - 2*cm)
    
    # Add inner decorative border
    p.setStrokeColor(colors.red.clone(alpha=0.5))
    p.setLineWidth(1)
    p.rect(1.5*cm, 1.5*cm, width - 3*cm, height - 3*cm)
    
    # Add corner decorations
    for x, y in [(1.5*cm, 1.5*cm), (width-1.5*cm, 1.5*cm), (1.5*cm, height-1.5*cm), (width-1.5*cm, height-1.5*cm)]:
        p.setFillColor(colors.red)
        p.circle(x, y, 0.3*cm, fill=1)
    
    # Add blood drop logo
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                           'static', 'images', 'certificate', 'blood_drop.svg')
    if os.path.exists(logo_path):
        try:
            p.drawImage(logo_path, width/2 - 2*cm, height - 6*cm, width=4*cm, height=4*cm, mask='auto')
        except:
            # If SVG not supported, draw a simple circle
            p.setFillColor(colors.red)
            p.circle(width/2, height - 4*cm, 2*cm, fill=1)
    else:
        # Fallback if image doesn't exist
        p.setFillColor(colors.red)
        p.circle(width/2, height - 4*cm, 2*cm, fill=1)
    
    # Add watermark
    p.saveState()
    p.setFillColor(colors.red.clone(alpha=0.05))
    p.setFont('Helvetica-Bold', 60)
    p.rotate(45)
    p.drawCentredString(width, 0, "LIFE SAVER")
    p.restoreState()
    
    # Add title
    p.setFillColor(colors.red)
    p.setFont('Helvetica-Bold', 24)
    p.drawCentredString(width/2, height - 7*cm, 'Certificate of Appreciation')
    
    p.setFillColor(colors.black)
    p.setFont('Helvetica-Bold', 16)
    p.drawCentredString(width/2, height - 8*cm, 'For Blood Donation')
    
    # Get donor and hospital information
    user = User.query.get(donation.donor_id)
    donor_name = user.donor_profile.name if user and user.donor_profile else "Valued Donor"
    hospital = donation.hospital
    hospital_name = hospital.name if hospital else "Our Blood Bank"
    hospital_address = hospital.address if hospital else ""
    
    # Add donor information
    p.setFont('Helvetica-Bold', 18)
    p.drawCentredString(width/2, height - 10*cm, donor_name)
    
    # Add donation details
    p.setFont('Helvetica', 12)
    p.drawCentredString(width/2, height - 11*cm, 
                      f"Has generously donated {donation.units} unit(s) ({donation.units * 500}ml) of {donation.blood_group} blood")
    p.drawCentredString(width/2, height - 11.5*cm, 
                      f"This selfless act will help save up to {donation.units * 3} lives")
    
    # Add donation date
    donation_date = donation.approval_date or donation.request_date
    p.setFont('Helvetica-Bold', 12)
    p.drawCentredString(width/2, height - 13*cm, 
                      f"Donation Date: {donation_date.strftime('%B %d, %Y')}")
    
    # Add hospital information
    p.setFont('Helvetica', 12)
    p.drawCentredString(width/2, height - 14*cm, f"At: {hospital_name}")
    if hospital_address:
        p.drawCentredString(width/2, height - 14.5*cm, hospital_address)
    
    # Add thank you message
    p.setFont('Helvetica-Oblique', 12)
    p.drawCentredString(width/2, height - 16*cm, 
                      "Thank you for your generous contribution to saving lives!")
    
    # Add signature lines
    p.line(width/4 - 2*cm, height - 19*cm, width/4 + 2*cm, height - 19*cm)
    p.line(3*width/4 - 2*cm, height - 19*cm, 3*width/4 + 2*cm, height - 19*cm)
    
    p.setFont('Helvetica', 10)
    p.drawCentredString(width/4, height - 19.5*cm, "Hospital Director")
    p.drawCentredString(3*width/4, height - 19.5*cm, "Medical Officer")
    
    # Add certificate ID and date of issue
    p.setFont('Helvetica', 8)
    p.setFillColor(colors.grey)
    certificate_id = f"DON-{donation.id}-{donation.donor_id}"
    p.drawString(2*cm, 1.5*cm, f"Certificate ID: {certificate_id}")
    p.drawString(width - 7*cm, 1.5*cm, f"Issued: {datetime.utcnow().strftime('%Y-%m-%d')}")
    
    p.save()
    buffer.seek(0)
    return buffer


@donor.route('/donation/<int:donation_id>/certificate')
@login_required
def download_certificate(donation_id):
    if not current_user.is_donor():
        abort(403)
    
    # Get the donation
    donation = Donation.query.get_or_404(donation_id)
    
    # Check if donation belongs to this user
    if donation.donor_id != current_user.id:
        abort(403)
    
    # Check if donation is completed or approved
    if donation.status not in ['completed', 'approved']:
        flash('Certificate is only available for approved or completed donations', 'warning')
        return redirect(url_for('donor.donation_history'))
    
    # Generate certificate
    buffer = generate_certificate(donation)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=donation_certificate_{donation.id}.pdf'
    
    return response


@donor.route('/cancel-donation/<int:donation_id>', methods=['POST'])
@login_required
def cancel_donation(donation_id):
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    donation = Donation.query.get_or_404(donation_id)
    
    # Check if the current user is the donor
    if donation.donor_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    # Check if donation can be cancelled (only pending donations can be cancelled)
    if donation.status != 'pending':
        return jsonify({
            'success': False, 
            'message': f'Cannot cancel donation with status: {donation.status}'
        }), 400
    
    try:
        # Update donation status
        donation.status = 'cancelled'
        donation.cancellation_date = datetime.utcnow()
        
        # Create notification using the enhanced notification system
        notification_result = send_notification(
            user_id=current_user.id,
            title='Donation Cancelled',
            message=f'Your donation request on {donation.request_date.strftime("%Y-%m-%d")} has been cancelled.',
            notification_type='donation_cancelled',
            delivery_methods=['system', 'email'],  # Send both system and email notifications
            related_entity_type='donation',
            related_entity_id=donation.id
        )
        
        # Log notification result
        if not notification_result['success']:
            current_app.logger.warning(f"Failed to send some notifications: {notification_result}")
            
        db.session.commit()
        
        # Log the cancellation
        current_app.logger.info(f'Donation {donation_id} cancelled by user {current_user.id}')
        
        return jsonify({
            'success': True,
            'message': 'Donation cancelled successfully',
            'donation_id': donation.id,
            'status': donation.status
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error cancelling donation: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An error occurred while cancelling the donation'
        }), 500


@donor.route('/view-certificate/<int:donation_id>')
@login_required
def view_certificate(donation_id):
    """View donation certificate in the browser"""
    donation = Donation.query.get_or_404(donation_id)
    
    # Check if the current user is the donor or an admin
    if donation.donor_id != current_user.id and not current_user.is_admin():
        abort(403)
        
    # Check if donation was completed
    if donation.status != 'completed':
        flash('Certificate is only available for completed donations.', 'warning')
        return redirect(url_for('donor.donation_history'))
        
    # Generate the certificate
    pdf = generate_certificate(donation)
    
    # Create response
    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=certificate_donation_{donation_id}.pdf'
    
    return response


@donor.route('/export-donations')
@login_required
def export_donations():
    """Export donation history to CSV"""
    # Get filter parameters
    status = request.args.get('status', '')
    hospital_id = request.args.get('hospital_id', '', type=int)
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build query with filters
    query = Donation.query.filter_by(donor_id=current_user.id)
    
    # Apply filters if provided
    if status:
        query = query.filter_by(status=status)
    
    if hospital_id:
        query = query.filter_by(hospital_id=hospital_id)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Donation.request_date >= start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the end date in results
            end_date_obj = end_date_obj + timedelta(days=1)
            query = query.filter(Donation.request_date <= end_date_obj)
        except ValueError:
            pass
    
    # Get all donations for the current user with applied filters
    donations = query.order_by(Donation.request_date.desc()).all()
    
    if not donations:
        flash('No donation records to export.', 'info')
        return redirect(url_for('donor.donation_history'))
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='')
    
    try:
        # Write CSV data
        fieldnames = ['Donation ID', 'Hospital', 'Address', 'Request Date', 'Units', 'Volume (ml)', 
                     'Status', 'Notes', 'Donation Date', 'Cancellation Date']
        
        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        
        for donation in donations:
            writer.writerow({
                'Donation ID': donation.id,
                'Hospital': donation.hospital.name,
                'Address': donation.hospital.address,
                'Request Date': donation.request_date.strftime('%Y-%m-%d'),
                'Units': donation.units,
                'Volume (ml)': donation.units * 500,
                'Status': donation.status,
                'Notes': donation.notes or '',
                'Donation Date': donation.donation_date.strftime('%Y-%m-%d') if donation.donation_date else '',
                'Cancellation Date': donation.cancellation_date.strftime('%Y-%m-%d') if donation.cancellation_date else ''
            })
        
        temp_file.close()
        
        # Log the export
        current_app.logger.info(f'User {current_user.id} exported donation history')
        
        # Create notification using the enhanced notification system
        notification_result = send_notification(
            user_id=current_user.id,
            title='Donation History Exported',
            message=f'You have exported your donation history on {datetime.utcnow().strftime("%Y-%m-%d %H:%M")}.',
            notification_type='data_export',
            delivery_methods=['system'],  # Only system notification for exports
            related_entity_type='user',
            related_entity_id=current_user.id
        )
        
        # Log notification result
        if not notification_result['success']:
            current_app.logger.warning(f"Failed to send export notification: {notification_result}")
        
        db.session.commit()
        
        # Send the file
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'donation_history_{datetime.utcnow().strftime("%Y%m%d")}.csv',
            mimetype='text/csv'
        )
    
    except Exception as e:
        current_app.logger.error(f'Error exporting donations: {str(e)}')
        flash('An error occurred while exporting your donation history.', 'danger')
        return redirect(url_for('donor.donation_history'))
