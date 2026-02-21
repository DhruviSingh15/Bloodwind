from app import create_app, db
from app.models.user import User, HospitalProfile, DonorProfile
from app.models.donation import BloodInventory

def setup_test_data():
    app = create_app()
    with app.app_context():
        # Check if any users exist
        users = User.query.all()
        print(f"Found {len(users)} users in the database")
        
        # Create a test hospital user if none exists
        if not users:
            print("Creating test hospital user...")
            # Create user
            hashed_password = app.bcrypt.generate_password_hash('test123').decode('utf-8')
            user = User(email='hospital@example.com', password=hashed_password, role='hospital')
            db.session.add(user)
            db.session.flush()  # Get the user ID
            
            # Create hospital profile
            hospital = HospitalProfile(
                user_id=user.id,
                name='Test Hospital',
                license_number='HOSP123',
                phone='1234567890',
                address='123 Test St, Test City'
            )
            db.session.add(hospital)
            db.session.flush()  # Get the hospital ID
            
            # Create blood inventory
            blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
            for bg in blood_groups:
                inventory = BloodInventory(hospital_id=hospital.id, blood_group=bg, units=0)
                db.session.add(inventory)
            
            db.session.commit()
            print("Test hospital user created successfully!")
            print(f"Email: hospital@example.com")
            print(f"Password: test123")
        else:
            print("Existing users:")
            for user in users:
                print(f"- {user.email} ({user.role})")

if __name__ == '__main__':
    setup_test_data()
