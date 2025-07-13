#!/usr/bin/env python3
"""
Initialize driver search radius setting in database
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import SystemSettings

def initialize_driver_radius():
    """Initialize driver search radius setting if not exists"""
    with app.app_context():
        # Check if setting already exists
        existing_setting = SystemSettings.query.filter_by(setting_key='driver_search_radius').first()
        
        if existing_setting:
            print(f"Driver search radius already set to: {existing_setting.setting_value}km")
            return
        
        # Create new setting with default value
        setting = SystemSettings(
            setting_key='driver_search_radius',
            setting_value='10.0',
            description='Driver search radius in kilometers for order assignments'
        )
        
        db.session.add(setting)
        db.session.commit()
        
        print("✅ Driver search radius initialized to 10.0km")

if __name__ == '__main__':
    initialize_driver_radius()