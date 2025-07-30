#!/usr/bin/env python3
"""
Database migration script to add kitchen workflow fields to the Order table
"""

from app import app, db
from models import Order
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_kitchen_workflow_fields():
    """Add kitchen workflow fields to Order table"""
    try:
        with app.app_context():
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('order')]
            
            fields_to_add = [
                ('kitchen_accepted_at', 'DATETIME'),
                ('cancellation_reason', 'TEXT')
            ]
            
            for field_name, field_type in fields_to_add:
                if field_name not in columns:
                    logger.info(f"Adding {field_name} column to order table...")
                    with db.engine.connect() as connection:
                        connection.execute(text(f'ALTER TABLE "order" ADD COLUMN {field_name} {field_type}'))
                        connection.commit()
                    logger.info(f"Successfully added {field_name} column")
                else:
                    logger.info(f"Column {field_name} already exists, skipping...")
            
            logger.info("Kitchen workflow fields migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Error adding kitchen workflow fields: {e}")
        raise

if __name__ == "__main__":
    add_kitchen_workflow_fields()