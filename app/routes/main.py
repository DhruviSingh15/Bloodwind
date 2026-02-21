from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def home():
    if current_user.is_authenticated:
        if current_user.is_donor():
            return redirect(url_for('donor.dashboard'))
        elif current_user.is_hospital():
            return redirect(url_for('hospital.dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
    
    return render_template('main/home.html', title='Home')

@main.route('/about')
def about():
    return render_template('main/about.html', title='About')

@main.route('/contact')
def contact():
    return render_template('main/contact.html', title='Contact Us')
