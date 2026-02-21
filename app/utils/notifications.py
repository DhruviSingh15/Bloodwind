from flask import current_app, render_template
from app import mail
from flask_mail import Message
from app.models.donation import Notification
from app.models.user import User
from app import db
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

def send_email_notification(notification_id):
    """
    Send an email notification based on the notification ID
    """
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return False
            
        user = User.query.get(notification.user_id)
        if not user or not user.email:
            logger.error(f"User {notification.user_id} not found or has no email")
            return False
            
        # Create email message
        msg = Message(
            subject=notification.title,
            recipients=[user.email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        # Generate HTML content based on notification type
        template_name = f"emails/{notification.notification_type}.html"
        try:
            msg.html = render_template(
                template_name,
                user=user,
                notification=notification,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            # Fallback to generic template if specific one doesn't exist
            logger.warning(f"Template {template_name} not found, using generic: {str(e)}")
            msg.html = render_template(
                "emails/generic.html",
                user=user,
                notification=notification,
                timestamp=datetime.utcnow()
            )
        
        # Send the email
        mail.send(msg)
        
        # Update notification status
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Email notification {notification_id} sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email notification {notification_id}: {str(e)}")
        return False

def send_sms_notification(notification_id):
    """
    Send an SMS notification based on the notification ID
    Uses Twilio API if configured
    """
    try:
        # Check if Twilio is configured
        twilio_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        twilio_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        twilio_number = current_app.config.get('TWILIO_PHONE_NUMBER')
        
        if not (twilio_sid and twilio_token and twilio_number):
            logger.warning("Twilio not configured, skipping SMS notification")
            return False
            
        # Import Twilio client only if configured
        from twilio.rest import Client
        
        notification = Notification.query.get(notification_id)
        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return False
            
        user = User.query.get(notification.user_id)
        if not user or not user.phone_number:
            logger.error(f"User {notification.user_id} not found or has no phone number")
            return False
            
        # Create Twilio client
        client = Client(twilio_sid, twilio_token)
        
        # Send SMS
        message = client.messages.create(
            body=f"{notification.title}: {notification.message}",
            from_=twilio_number,
            to=user.phone_number
        )
        
        # Update notification status
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"SMS notification {notification_id} sent to {user.phone_number}, SID: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending SMS notification {notification_id}: {str(e)}")
        return False

def send_notification(user_id, title, message, notification_type, delivery_methods=None, related_entity_type=None, related_entity_id=None):
    """
    Create and send a notification to a user through specified delivery methods
    
    Args:
        user_id: ID of the user to notify
        title: Title of the notification
        message: Content of the notification
        notification_type: Type of notification (e.g., donation_approved)
        delivery_methods: List of methods to deliver the notification (system, email, sms)
                         If None, will use user's preferences
        related_entity_type: Type of related entity (e.g., donation)
        related_entity_id: ID of the related entity
        
    Returns:
        Dictionary with status of each delivery method
    """
    try:
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {"success": False, "error": "User not found"}
            
        # If delivery methods not specified, use user preferences
        if delivery_methods is None:
            delivery_methods = ["system"]  # System notification is always sent
            
            # Add email if user has email and has opted in
            if user.email and getattr(user, 'email_notifications', True):
                delivery_methods.append("email")
                
            # Add SMS if user has phone number and has opted in
            if user.phone_number and getattr(user, 'sms_notifications', False):
                delivery_methods.append("sms")
        
        results = {}
        
        # Create a system notification (always created regardless of delivery methods)
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            delivery_method="system",
            is_sent=True,  # System notifications are considered sent immediately
            sent_at=datetime.utcnow(),
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )
        db.session.add(notification)
        db.session.commit()
        results["system"] = True
        
        # Send email notification if requested
        if "email" in delivery_methods and user.email:
            email_notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                delivery_method="email",
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
            db.session.add(email_notification)
            db.session.commit()
            
            results["email"] = send_email_notification(email_notification.id)
        
        # Send SMS notification if requested
        if "sms" in delivery_methods and user.phone_number:
            sms_notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                delivery_method="sms",
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id
            )
            db.session.add(sms_notification)
            db.session.commit()
            
            results["sms"] = send_sms_notification(sms_notification.id)
            
        return {"success": True, "results": results}
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        return {"success": False, "error": str(e)}
