from app.models.donation import Donation

def get_donation(donation_id):
    """
    Helper function to get donation details for templates
    """
    return Donation.query.get(donation_id)
