#!/usr/bin/env python3
"""
Update database schema to support payment workflow
"""
import sqlite3
import os

def update_database_schema():
    """Add missing columns to support payment workflow"""
    db_path = os.path.join('instance', 'food_delivery.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database file not found. It will be created when the app starts.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add payment workflow columns to order table
        columns_to_add = [
            ('deposit_amount', 'REAL'),
            ('deposit_deadline', 'DATETIME'),
            ('deposit_submitted_at', 'DATETIME'),
            ('payment_verified_at', 'DATETIME'),
            ('preparation_started_at', 'DATETIME')
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f'ALTER TABLE "order" ADD COLUMN {column_name} {column_type}')
                print(f"Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' in str(e):
                    print(f"Column {column_name} already exists")
                else:
                    print(f"Error adding column {column_name}: {e}")
        
        # Create payment_transaction table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_transaction (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                payment_type VARCHAR(20) NOT NULL,
                amount REAL NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                transaction_id VARCHAR(100),
                screenshot_url VARCHAR(500),
                status VARCHAR(20) DEFAULT 'pending_verification',
                admin_notes TEXT,
                verified_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES "order" (id)
            )
        ''')
        print("Payment transaction table created/verified")
        
        conn.commit()
        print("Database schema updated successfully!")
        
    except Exception as e:
        print(f"Error updating database schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_database_schema()