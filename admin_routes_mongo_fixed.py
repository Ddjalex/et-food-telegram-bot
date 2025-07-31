"""
MongoDB-based Admin Routes for ET-FOOD Delivery System
Administrative interface routes using MongoDB models
"""
from flask import render_template, request, jsonify, redirect, url_for, session
from app_mongo_fixed import app
from models_mongo_fixed import (
    restaurant_model, menu_item_model, order_model, driver_model,
    admin_user_model, payment_transaction_model, category_model
)
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Admin Authentication
def check_admin_session():
    """Check if user is logged in as admin"""
    return session.get('admin_logged_in', False)

@app.route('/admin')
@app.route('/admin/')
def admin_dashboard():
    """Main admin dashboard"""
    if not check_admin_session():
        return redirect(url_for('admin_login'))
    
    try:
        # Get dashboard statistics
        stats = {
            'total_orders': order_model.count(),
            'pending_orders': order_model.count({'status': 'pending'}),
            'total_restaurants': restaurant_model.count(),
            'total_drivers': driver_model.count(),
            'active_drivers': driver_model.count({'is_active': True, 'is_available': True})
        }
        
        return render_template('admin.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        return render_template('admin.html', stats={})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('admin_login.html', error='Username and password are required')
        
        # Find admin user
        admin_user = admin_user_model.find_by_username(username)
        
        if admin_user and admin_user['password_hash'] == password:  # In production, use proper password hashing
            session['admin_logged_in'] = True
            session['admin_user_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_role'] = admin_user.get('role', 'admin')
            
            # Update last login
            admin_user_model.update_last_login(admin_user['id'])
            
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid username or password')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/superadmin')
@app.route('/superadmin/')
def super_admin_dashboard():
    """Super admin dashboard"""
    if not check_admin_session():
        return redirect(url_for('super_admin_login'))
    
    try:
        # Get comprehensive statistics
        stats = {
            'total_orders': order_model.count(),
            'total_restaurants': restaurant_model.count(),
            'total_drivers': driver_model.count(),
            'total_admins': admin_user_model.count()
        }
        
        return render_template('super_admin_dashboard.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading super admin dashboard: {e}")
        return render_template('super_admin_dashboard.html', stats={})

@app.route('/superadmin/login', methods=['GET', 'POST'])
def super_admin_login():
    """Super admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('superadmin_login.html', error='Username and password are required')
        
        # Find admin user
        admin_user = admin_user_model.find_by_username(username)
        
        if admin_user and admin_user['password_hash'] == password and admin_user.get('role') == 'super_admin':
            session['admin_logged_in'] = True
            session['admin_user_id'] = admin_user['id']
            session['admin_username'] = admin_user['username']
            session['admin_role'] = 'super_admin'
            
            # Update last login
            admin_user_model.update_last_login(admin_user['id'])
            
            return redirect(url_for('super_admin_dashboard'))
        else:
            return render_template('superadmin_login.html', error='Invalid credentials or insufficient privileges')
    
    return render_template('superadmin_login.html')