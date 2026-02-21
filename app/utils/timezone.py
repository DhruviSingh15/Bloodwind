from datetime import datetime, timedelta

def get_ist_now():
    """
    Returns the current datetime in Indian Standard Time (IST)
    IST is UTC+5:30
    """
    utc_now = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    ist_now = utc_now + ist_offset
    return ist_now

def format_ist_datetime(dt, format_str="%Y-%m-%d %H:%M:%S"):
    """
    Formats a UTC datetime object to IST string representation
    """
    if dt is None:
        return None
    ist_dt = dt + timedelta(hours=5, minutes=30)
    return ist_dt.strftime(format_str)

def convert_to_ist(dt):
    """
    Converts a UTC datetime object to IST
    """
    if dt is None:
        return None
    ist_offset = timedelta(hours=5, minutes=30)
    return dt + ist_offset
