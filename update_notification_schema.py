from app import create_app, db
from app.models.donation import Notification
from sqlalchemy import text, inspect

def update_notification_schema():
    app = create_app()
    with app.app_context():
        # Get the database inspector
        inspector = inspect(db.engine)
        
        # Get existing columns in the notification table
        existing_columns = [column['name'] for column in inspector.get_columns('notification')]
        print(f"Existing columns in notification table: {existing_columns}")
        
        # Define all columns from the Notification model
        model_columns = {
            'id': 'INTEGER PRIMARY KEY', 
            'user_id': 'INTEGER NOT NULL',
            'title': 'VARCHAR(100) DEFAULT "Notification" NOT NULL',
            'message': 'TEXT NOT NULL',
            'notification_type': 'VARCHAR(50) NOT NULL',
            'delivery_method': 'VARCHAR(20) DEFAULT "system" NOT NULL',
            'is_sent': 'BOOLEAN DEFAULT 0',
            'is_read': 'BOOLEAN DEFAULT 0',
            'created_at': 'DATETIME',
            'sent_at': 'DATETIME',
            'related_entity_type': 'VARCHAR(50)',
            'related_entity_id': 'INTEGER'
        }
        
        # Check for missing columns and add them
        for column_name, column_type in model_columns.items():
            if column_name not in existing_columns:
                print(f"Adding missing column: {column_name}")
                try:
                    with db.engine.connect() as conn:
                        with conn.begin():
                            conn.execute(text(f'ALTER TABLE notification ADD COLUMN {column_name} {column_type}'))
                    print(f"Successfully added {column_name} column to notification table.")
                except Exception as e:
                    print(f"Error adding {column_name} column: {str(e)}")
            else:
                print(f"Column {column_name} already exists.")

if __name__ == '__main__':
    update_notification_schema()
