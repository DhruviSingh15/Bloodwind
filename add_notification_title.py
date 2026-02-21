from app import create_app, db
from app.models.donation import Notification
from sqlalchemy import text

def add_missing_columns():
    app = create_app()
    with app.app_context():
        # Add title column if it doesn't exist
        try:
            # Try to query using the title column
            Notification.query.filter_by(title='Test').first()
            print("Title column already exists in the notification table.")
        except Exception as e:
            print(f"Title column doesn't exist: {str(e)}")
            
            # Add the title column to the notification table
            try:
                # Get a connection from the engine
                with db.engine.connect() as conn:
                    # Create a transaction
                    with conn.begin():
                        # Add the column
                        conn.execute(text('ALTER TABLE notification ADD COLUMN title VARCHAR(100) DEFAULT "Notification" NOT NULL'))
                
                print("Successfully added title column to notification table.")
            except Exception as e:
                print(f"Error adding title column: {str(e)}")
        
        # Add delivery_method column if it doesn't exist
        try:
            # Try to query using the delivery_method column
            Notification.query.filter_by(delivery_method='system').first()
            print("Delivery method column already exists in the notification table.")
        except Exception as e:
            print(f"Delivery method column doesn't exist: {str(e)}")
            
            # Add the delivery_method column to the notification table
            try:
                # Get a connection from the engine
                with db.engine.connect() as conn:
                    # Create a transaction
                    with conn.begin():
                        # Add the column
                        conn.execute(text('ALTER TABLE notification ADD COLUMN delivery_method VARCHAR(20) DEFAULT "system" NOT NULL'))
                
                print("Successfully added delivery_method column to notification table.")
            except Exception as e:
                print(f"Error adding delivery_method column: {str(e)}")


if __name__ == '__main__':
    add_missing_columns()
