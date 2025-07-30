#!/usr/bin/env python3
"""
Fix Driver Status Script
Updates driver status to active when they have recent location updates
"""

import logging
from datetime import datetime, timedelta
from models import Driver
from app import db
from main import app

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_driver_status():
    """Fix driver status for drivers who should be active"""
    try:
        with app.app_context():
            # Get all drivers who have recent location updates but are inactive
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)
            
            inactive_drivers = Driver.query.filter(
                Driver.is_active == False,
                Driver.last_location_update.isnot(None),
                Driver.last_location_update > cutoff_time
            ).all()
            
            logger.info(f"Found {len(inactive_drivers)} inactive drivers with recent location updates")
            
            for driver in inactive_drivers:
                logger.info(f"Activating driver: {driver.name} (ID: {driver.id})")
                driver.is_active = True
                
            # Also activate drivers who are available but inactive
            available_inactive = Driver.query.filter(
                Driver.is_active == False,
                Driver.is_available == True
            ).all()
            
            logger.info(f"Found {len(available_inactive)} available but inactive drivers")
            
            for driver in available_inactive:
                logger.info(f"Activating available driver: {driver.name} (ID: {driver.id})")
                driver.is_active = True
                
            db.session.commit()
            logger.info("Driver status updates completed successfully")
            
            # Show updated status
            all_drivers = Driver.query.all()
            logger.info("Current driver status:")
            for driver in all_drivers:
                logger.info(f"  {driver.name}: Active={driver.is_active}, Available={driver.is_available}")
            
    except Exception as e:
        logger.error(f"Error fixing driver status: {e}")
        db.session.rollback()

if __name__ == "__main__":
    fix_driver_status()