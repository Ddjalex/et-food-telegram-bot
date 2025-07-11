"""
Admin Approval System for Driver Registration
Handles notifications and approval workflow for driver registrations
"""

import logging
from datetime import datetime
from models import Driver, AdminUser
from extensions import db
from driver_bot import send_driver_message

logger = logging.getLogger(__name__)

def notify_admin_new_driver_registration(driver_id):
    """Notify admin about new driver registration with documents"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            logger.error(f"Driver with ID {driver_id} not found")
            return False
            
        # Count uploaded documents
        documents_count = 0
        documents_list = []
        
        # Check both old and new field names for backwards compatibility
        if driver.license_document or driver.license_front_url:
            documents_count += 1
            documents_list.append("Driver License")
        if driver.id_document or driver.id_front_url:
            documents_count += 1
            documents_list.append("Government ID")
        if driver.vehicle_document or driver.vehicle_registration_url:
            documents_count += 1
            documents_list.append("Vehicle Registration")
        
        # Create admin notification message
        message = f"""🚨 *NEW DRIVER REGISTRATION*\n\n"""
        message += f"👤 **Driver Details:**\n"
        message += f"• Name: {driver.name}\n"
        message += f"• Phone: {driver.phone_number}\n"
        message += f"• Email: {getattr(driver, 'email', 'Not provided')}\n"
        message += f"• Vehicle: {driver.vehicle_type.title()}\n"
        message += f"• Registration Date: {driver.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        message += f"📄 **Documents Uploaded ({documents_count}):**\n"
        for doc in documents_list:
            message += f"• ✅ {doc}\n"
        
        message += f"\n⏳ **Status:** Pending Your Approval\n"
        message += f"🔔 **Action Required:** Please review and approve/reject this driver in the admin dashboard.\n\n"
        message += f"📋 **Driver ID:** #{driver.id}\n"
        message += f"📱 **Telegram ID:** {driver.telegram_user_id or 'Not linked'}"
        
        # Send to all active admins via driver bot to avoid customer bot interference
        admins = AdminUser.query.filter_by(is_active=True).all()
        if not admins:
            # Fallback to default admin IDs if no admins in database
            default_admin_ids = [383870191, 383870190]  # Add your admin IDs here
            for admin_id in default_admin_ids:
                try:
                    send_driver_message(admin_id, message)
                    logger.info(f"Sent new driver notification to admin {admin_id} via driver bot")
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin_id}: {e}")
        else:
            for admin in admins:
                try:
                    send_driver_message(admin.telegram_user_id, message)
                    logger.info(f"Sent new driver notification to admin {admin.telegram_user_id} via driver bot")
                except Exception as e:
                    logger.error(f"Failed to send notification to admin {admin.telegram_user_id}: {e}")
        
        # Customer notifications disabled - driver registration messages only go to admins
        
        return True
        
    except Exception as e:
        logger.error(f"Error notifying admin about new driver registration: {e}")
        return False

# Customer notifications for driver registrations have been completely disabled
# All driver registration notifications now go only to admins for review

def approve_driver(driver_id, admin_telegram_id=None):
    """Approve a pending driver and send congratulations notification"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            logger.error(f"Driver with ID {driver_id} not found")
            return False
            
        # Update driver status
        driver.is_approved = True
        driver.approval_status = 'approved'
        driver.is_active = True
        driver.approved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send congratulations notification to driver
        congratulations_message = f"""🎉 *CONGRATULATIONS! You're Approved!*\n\n"""
        congratulations_message += f"✅ **Your driver application has been approved!**\n\n"
        congratulations_message += f"👤 **Driver Details:**\n"
        congratulations_message += f"• Name: {driver.name}\n"
        congratulations_message += f"• Phone: {driver.phone_number}\n"
        congratulations_message += f"• Vehicle: {driver.vehicle_type.title()}\n"
        congratulations_message += f"• Status: **APPROVED** ✅\n\n"
        
        congratulations_message += f"🚚 **Next Steps:**\n"
        congratulations_message += f"• Share your live location to receive orders\n"
        congratulations_message += f"• Keep your phone charged and ready\n"
        congratulations_message += f"• Maintain professional service\n\n"
        
        congratulations_message += f"📍 **IMPORTANT:** You must share your live location to receive delivery orders near you.\n\n"
        congratulations_message += f"🎯 **You're now part of the ET-FOOD delivery team!**\n"
        congratulations_message += f"Start earning money by delivering food to customers in your area."
        
        if driver.telegram_user_id:
            # Send enhanced approval success message with interactive buttons
            from enhanced_driver_system import send_driver_approval_success_message
            send_driver_approval_success_message(driver_id)
            logger.info(f"Sent enhanced approval notification to driver {driver.telegram_user_id}")
        else:
            logger.warning(f"Driver {driver.name} has no Telegram account linked for approval notification")
        
        # Log approval
        logger.info(f"Driver {driver.name} (ID: {driver.id}) approved by admin {admin_telegram_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error approving driver {driver_id}: {e}")
        return False

def reject_driver(driver_id, admin_telegram_id=None, reason="Application does not meet requirements"):
    """Reject a pending driver and send notification"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            logger.error(f"Driver with ID {driver_id} not found")
            return False
            
        # Update driver status
        driver.is_approved = False
        driver.approval_status = 'rejected'
        driver.is_active = False
        driver.rejection_reason = reason
        # Note: Add rejected_at field to model if needed for tracking
        driver.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send rejection notification to driver
        rejection_message = f"""❌ *Application Update*\n\n"""
        rejection_message += f"We've reviewed your driver application.\n\n"
        rejection_message += f"👤 **Application Details:**\n"
        rejection_message += f"• Name: {driver.name}\n"
        rejection_message += f"• Phone: {driver.phone_number}\n"
        rejection_message += f"• Vehicle: {driver.vehicle_type.title()}\n"
        rejection_message += f"• Status: **Not Approved**\n\n"
        
        rejection_message += f"📝 **Reason:** {reason}\n\n"
        rejection_message += f"🔄 **Next Steps:**\n"
        rejection_message += f"• You can reapply after addressing the issues\n"
        rejection_message += f"• Contact admin for clarification\n"
        rejection_message += f"• Make sure all documents are clear and valid\n\n"
        
        rejection_message += f"📞 **Support:** Contact restaurant admin for more information."
        
        if driver.telegram_user_id:
            send_driver_message(driver.telegram_user_id, rejection_message)
            logger.info(f"Sent rejection notification to driver {driver.telegram_user_id}")
        
        # Log rejection
        logger.info(f"Driver {driver.name} (ID: {driver.id}) rejected by admin {admin_telegram_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error rejecting driver {driver_id}: {e}")
        return False

def get_pending_drivers():
    """Get all pending driver applications"""
    try:
        pending_drivers = Driver.query.filter_by(approval_status='pending').all()
        return pending_drivers
        
    except Exception as e:
        logger.error(f"Error getting pending drivers: {e}")
        return []

def get_driver_documents(driver_id):
    """Get driver document URLs for admin review"""
    try:
        driver = Driver.query.get(driver_id)
        if not driver:
            return None
            
        documents = {
            'license_document': driver.license_document,
            'id_document': driver.id_document,
            'vehicle_document': driver.vehicle_document
        }
        
        return documents
        
    except Exception as e:
        logger.error(f"Error getting driver documents: {e}")
        return None