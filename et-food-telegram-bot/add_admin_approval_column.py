#!/usr/bin/env python3
"""
Migration script to add is_approved column to AdminUser table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app
from models import db, AdminUser
from sqlalchemy import text

def add_admin_approval_column():
    """Add is_approved column to AdminUser table if it doesn't exist"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'admin_user' 
                AND COLUMN_NAME = 'is_approved'
                AND TABLE_SCHEMA = DATABASE()
            """)).fetchone()
            
            if result and result.count == 0:
                print("Adding is_approved column to AdminUser table...")
                
                # Add the column with default value True
                db.session.execute(text("""
                    ALTER TABLE admin_user 
                    ADD COLUMN is_approved BOOLEAN DEFAULT TRUE
                """))
                
                # Update all existing admin users to be approved by default
                db.session.execute(text("""
                    UPDATE admin_user 
                    SET is_approved = TRUE 
                    WHERE is_approved IS NULL
                """))
                
                db.session.commit()
                print("✓ Successfully added is_approved column to AdminUser table")
                print("✓ All existing admin users set to approved by default")
                
            else:
                print("✓ is_approved column already exists in AdminUser table")
                
        except Exception as e:
            print(f"Error adding is_approved column: {e}")
            db.session.rollback()
            
            # For SQLite, use different syntax
            try:
                print("Trying SQLite syntax...")
                db.session.execute(text("""
                    ALTER TABLE admin_user 
                    ADD COLUMN is_approved BOOLEAN DEFAULT 1
                """))
                
                # Update existing records for SQLite
                db.session.execute(text("""
                    UPDATE admin_user 
                    SET is_approved = 1 
                    WHERE is_approved IS NULL
                """))
                
                db.session.commit()
                print("✓ Successfully added is_approved column using SQLite syntax")
                
            except Exception as e2:
                print(f"Error with SQLite syntax too: {e2}")
                db.session.rollback()
                
                # Check if column exists by trying to query it
                try:
                    admin_count = AdminUser.query.filter_by(is_approved=True).count()
                    print(f"✓ Column already exists. Found {admin_count} approved admins")
                except Exception as e3:
                    print(f"Column doesn't exist and can't be added: {e3}")

if __name__ == "__main__":
    add_admin_approval_column()