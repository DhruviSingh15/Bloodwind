from twilio.rest import Client
import os
from app.models.user import User, DonorProfile
from app.models.donation import Notification
from app import db
from datetime import datetime
from flask import current_app

def send_sms(to_number, message):
    """
    Send SMS using Twilio API
    """
    try:
        # Get Twilio credentials from environment variables
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # Check if credentials are available
        if not all([account_sid, auth_token, from_number]):
            current_app.logger.error("Missing Twilio credentials:")
            current_app.logger.error(f"TWILIO_ACCOUNT_SID present: {bool(account_sid)}")
            current_app.logger.error(f"TWILIO_AUTH_TOKEN present: {bool(auth_token)}")
            current_app.logger.error(f"TWILIO_PHONE_NUMBER present: {bool(from_number)}")
            return False, "Twilio credentials not configured"
            
        # Log phone number format
        current_app.logger.info(f"Attempting to send SMS to: {to_number}")
        current_app.logger.info(f"From number: {from_number}")
        
        # Initialize Twilio client
        client = Client(account_sid, auth_token)
        
        # Send message
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        
        current_app.logger.info(f"SMS sent successfully. Message SID: {message.sid}")
        return True, message.sid
    
    except Exception as e:
        current_app.logger.error(f"Error sending SMS: {str(e)}")
        current_app.logger.error(f"Error type: {type(e).__name__}")
        current_app.logger.error(f"To number: {to_number}")
        current_app.logger.error(f"Message length: {len(message)}")
        return False, str(e)


def send_blood_request_notification(hospital_id, blood_group, quantity):
    """
    Send SMS to eligible donors when a hospital requests blood
    """
    from app.models.user import User, DonorProfile, HospitalProfile
    
    # Get hospital information
    hospital = HospitalProfile.query.get(hospital_id)
    if not hospital:
        current_app.logger.error(f"Hospital with ID {hospital_id} not found")
        return 0, 0
    
    # Find eligible donors with matching blood group
    eligible_donors = User.query.join(DonorProfile).filter(
        User.role == 'donor',
        DonorProfile.blood_group == blood_group
    ).all()
    
    success_count = 0
    failed_count = 0
    
    for donor in eligible_donors:
        # Check if donor is eligible
        if donor.donor_profile and donor.donor_profile.is_eligible()[0]:
            # Create a more detailed message
            message = f"URGENT: {hospital.name} needs {quantity} units of {blood_group} blood. Please contact {hospital.phone} or check your account for details."
            
            # Create notification in system
            notification = Notification(
                user_id=donor.id,
                title="Urgent Blood Request",
                message=message,
                notification_type='blood_request',
                delivery_method='sms',
                related_entity_type='hospital',
                related_entity_id=hospital_id
            )
            db.session.add(notification)
            
            # Get the donor's phone number
            phone_number = donor.donor_profile.phone
            
            # Ensure phone number is properly formatted
            if not phone_number.startswith('+'):
                # Add India country code if not present
                phone_number = '+91' + phone_number.lstrip('0')
            
            # Send SMS
            current_app.logger.info(f"Sending SMS to {phone_number}")
            success, message_result = send_sms(
                phone_number,
                message
            )
            
            if success:
                notification.is_sent = True
                notification.sent_at = datetime.utcnow()
                success_count += 1
                current_app.logger.info(f"Successfully sent SMS to {phone_number}, SID: {message_result}")
            else:
                failed_count += 1
                current_app.logger.error(f"Failed to send SMS to {phone_number}: {message_result}")
    
    db.session.commit()
    return success_count, failed_count


def send_donation_reminder(donor_id):
    """
    Send reminder to donor that they are eligible to donate again
    """
    donor = User.query.filter_by(id=donor_id, role='donor').first()
    
    if not donor or not donor.donor_profile:
        current_app.logger.error(f"Donor with ID {donor_id} not found or has no profile")
        return False, "Donor not found"
    
    # Create a personalized message
    message = f"Hello {donor.donor_profile.name}, good news! It's been 180 days since your last blood donation. You are now eligible to donate again. Please consider donating to save lives!"
    
    # Create notification in system
    notification = Notification(
        user_id=donor.id,
        title="Donation Eligibility Reminder",
        message=message,
        notification_type='donation_reminder',
        delivery_method='sms'
    )
    db.session.add(notification)
    
    # Get the donor's phone number
    phone_number = donor.donor_profile.phone
    
    # Ensure phone number is properly formatted
    if not phone_number.startswith('+'):
        # Add India country code if not present
        phone_number = '+91' + phone_number.lstrip('0')
    
    # Send SMS
    current_app.logger.info(f"Sending donation reminder SMS to {phone_number}")
    success, message_result = send_sms(
        phone_number,
        message
    )
    
    if success:
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(f"Successfully sent donation reminder SMS to {phone_number}, SID: {message_result}")
        return True, "Reminder sent successfully"
    else:
        db.session.commit()
        current_app.logger.error(f"Failed to send donation reminder SMS to {phone_number}: {message_result}")
        return False, message_result
