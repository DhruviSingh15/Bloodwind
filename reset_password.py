from app import create_app, db, bcrypt
from app.models.user import User

def reset_user_password():
    app = create_app()
    with app.app_context():
        # Get the user
        user = User.query.filter_by(email='chintamani@gmail.com').first()
        if user:
            print(f"Resetting password for user: {user.email}")
            
            # Set a new password
            new_password = 'password123'  # Simple password for testing
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            
            # Commit the changes
            db.session.commit()
            print(f"Password has been reset to: {new_password}")
        else:
            print("User not found!")

if __name__ == '__main__':
    reset_user_password()
