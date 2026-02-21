import requests
from bs4 import BeautifulSoup

# Create a session to maintain cookies
session = requests.Session()

# First, get the login page to get the CSRF token
login_url = 'http://127.0.0.1:5000/auth/login'
response = session.get(login_url)

# Parse the HTML to get the CSRF token
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

# Prepare login data
login_data = {
    'email': 'chintamani@gmail.com',
    'password': 'password123',
    'remember': 'y',
    'csrf_token': csrf_token
}

# Send login request
response = session.post(login_url, data=login_data, allow_redirects=True)

# Check if login was successful
if 'dashboard' in response.url:
    print("Login successful!")
    
    # Now try to access the pending donations count
    pending_url = 'http://127.0.0.1:5000/hospital/donations/pending/count'
    response = session.get(pending_url)
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
else:
    print(f"Login failed. Status code: {response.status_code}")
    print(f"Response: {response.text}")
