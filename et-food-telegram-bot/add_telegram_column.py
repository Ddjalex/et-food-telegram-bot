#!/usr/bin/env python3
"""
Add telegram_user_id column to kitchen_staff table
"""

import sqlite3
import os

# Database path
db_path = os.path.join(os.getcwd(), 'instance', 'food_delivery.db')

def add_telegram_column():
    """Add telegram_user_id column to kitchen_staff table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(kitchen_staff)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'telegram_user_id' not in columns:
            # Add the new column
            cursor.execute('ALTER TABLE kitchen_staff ADD COLUMN telegram_user_id INTEGER')
            print("✅ Added telegram_user_id column to kitchen_staff table")
        else:
            print("✅ telegram_user_id column already exists")
        
        # Check if PaymentTransaction table exists and has all required columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment_transaction'")
        if not cursor.fetchone():
            # Create PaymentTransaction table
            cursor.execute('''
                CREATE TABLE payment_transaction (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_method VARCHAR(50),
                    transaction_id VARCHAR(100),
                    transaction_image_url VARCHAR(500),
                    status VARCHAR(20) DEFAULT 'pending',
                    verified_at DATETIME,
                    admin_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES "order" (id)
                )
            ''')
            print("✅ Created payment_transaction table")
        
        conn.commit()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_telegram_column()