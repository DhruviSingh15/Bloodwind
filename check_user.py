from app import create_app, db, bcrypt
from app.models.user import User

def check_user():
    app = create_app()
    with app.app_context():
        # Get the user
        user = User.query.filter_by(email='chintamani@gmail.com').first()
        if user:
            print(f"User found: {user.email}")
            print(f"Role: {user.role}")
            print(f"Password hash: {user.password}")
            
            # Check if the password matches
            if bcrypt.check_password_hash(user.password, 'chintamani@123'):
                print("Password is correct!")
            else:
                print("Password is incorrect!")
                
            # Check with a different password format
            if bcrypt.check_password_hash(user.password, 'chintamani123'):
                print("Password 'chintamani123' is correct!")
            else:
                print("Password 'chintamani123' is incorrect!")
        else:
            print("User not found!")

if __name__ == '__main__':
    check_user()
