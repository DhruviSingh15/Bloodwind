from app import scheduler
from datetime import datetime, timedelta
from flask import current_app
from app.models.user import User, DonorProfile
from app.models.donation import Donation
from app.utils.sms import send_donation_reminder
from sqlalchemy import and_

def check_donation_reminders():
    """
    Check for donors who are eligible to donate again (180 days since last donation)
    and send them reminders
    """
    with current_app.app_context():
        # Find donors whose last donation was 180 days ago
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        # Find donations that were approved exactly 180 days ago
        recent_eligible_donations = Donation.query.filter(
            and_(
                Donation.status == 'approved',
                Donation.approval_date <= six_months_ago,
                Donation.approval_date >= six_months_ago - timedelta(days=1)  # Within the last day of becoming eligible
            )
        ).all()
        
        for donation in recent_eligible_donations:
            # Send reminder to donor
            send_donation_reminder(donation.donor_id)
            current_app.logger.info(f"Sent donation reminder to donor ID: {donation.donor_id}")


def start_scheduler(app):
    """
    Start the background scheduler for automated tasks
    """
    if not scheduler.running:
        with app.app_context():
            # Add scheduled jobs
            scheduler.add_job(
                func=check_donation_reminders,
                trigger='interval',
                hours=24,  # Run once a day
                id='donation_reminder_job',
                replace_existing=True
            )
            
            # Start the scheduler
            scheduler.start()
            app.logger.info("Background scheduler started")
            
            # Shut down scheduler when app context ends
            def shutdown_scheduler(exception):
                try:
                    if scheduler.running:
                        scheduler.shutdown(wait=False)
                except:
                    pass
                
            app.teardown_appcontext(shutdown_scheduler)
