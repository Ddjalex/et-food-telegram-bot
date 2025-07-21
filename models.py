from extensions import db
from datetime import datetime
from sqlalchemy import func

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    logo_url = db.Column(db.String(500))
    cover_image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    delivery_fee = db.Column(db.Float, default=0.0)
    minimum_order = db.Column(db.Float, default=0.0)
    estimated_delivery_time = db.Column(db.String(50), default='30-45 minutes')
    opening_hours = db.Column(db.JSON)  # Store as JSON: {"monday": "09:00-22:00", ...}
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True)
    orders = db.relationship('Order', backref='restaurant', lazy=True)
    
    def to_dict(self):
        # Add cache-busting timestamp to image URLs for real-time updates
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'phone': self.phone,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'logo_url': f"{self.logo_url}?t={timestamp}" if self.logo_url else None,
            'cover_image_url': f"{self.cover_image_url}?t={timestamp}" if self.cover_image_url else None,
            'is_active': self.is_active,
            'is_featured': self.is_featured,
            'delivery_fee': self.delivery_fee,
            'minimum_order': self.minimum_order,
            'estimated_delivery_time': self.estimated_delivery_time,
            'opening_hours': self.opening_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50), default='burgers')  # burgers, snacks, sauces, drinks
    available = db.Column(db.Boolean, default=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'image_url': self.image_url,
            'category': self.category,
            'available': self.available,
            'restaurant_id': self.restaurant_id
        }

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    items = db.Column(db.JSON, nullable=False)  # Store order items as JSON
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    transaction_id = db.Column(db.String(100))  # Payment transaction ID
    transaction_image_url = db.Column(db.String(500))  # Payment screenshot URL
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, preparing, out_for_delivery, delivered, cancelled
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False, default=1)
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    delivery_notes = db.Column(db.Text)
    estimated_delivery_time = db.Column(db.DateTime)
    
    # Payment workflow fields
    deposit_amount = db.Column(db.Float)  # Required deposit amount (50% of total)
    deposit_deadline = db.Column(db.DateTime)  # Deadline for deposit payment
    deposit_submitted_at = db.Column(db.DateTime)  # When customer submitted deposit
    payment_verified_at = db.Column(db.DateTime)  # When admin verified payment
    preparation_started_at = db.Column(db.DateTime)  # When kitchen started preparing
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    driver = db.relationship('Driver', backref='orders')

    def to_dict(self):
        return {
            'id': self.id,
            'telegram_user_id': self.telegram_user_id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'items': self.items,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'transaction_image_url': self.transaction_image_url,
            'status': self.status,
            'driver_id': self.driver_id,
            'restaurant_id': self.restaurant_id,
            'location_lat': self.location_lat,
            'location_lng': self.location_lng,
            'delivery_notes': self.delivery_notes,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(120))
    full_name = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='admin')  # super_admin, admin, kitchen_staff
    is_active = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(256))
    last_login = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=True)
    permissions = db.Column(db.JSON)  # Store permissions as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Performance tracking
    orders_processed = db.Column(db.Integer, default=0)
    orders_completed = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float, default=0.0)  # in minutes
    total_revenue_managed = db.Column(db.Float, default=0.0)
    
    # Self-referential relationship for admin hierarchy
    created_admins = db.relationship('AdminUser', backref=db.backref('creator', remote_side=[id]))
    
    # Relationship with Restaurant
    restaurant = db.relationship('Restaurant', backref='admins')
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'telegram_user_id': self.telegram_user_id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'is_blocked': self.is_blocked,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'restaurant_id': self.restaurant_id,
            'orders_processed': self.orders_processed,
            'orders_completed': self.orders_completed,
            'average_response_time': self.average_response_time,
            'total_revenue_managed': self.total_revenue_managed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'setting_key': self.setting_key,
            'setting_value': self.setting_value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(10), default='🍽️')
    image_url = db.Column(db.String(500))  # Optional category image
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'restaurant_id': self.restaurant_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    telegram_user_id = db.Column(db.BigInteger, unique=True)
    email = db.Column(db.String(120))  # Driver email address
    vehicle_type = db.Column(db.String(50))  # motorcycle, car, bicycle
    experience = db.Column(db.Text)  # Driver experience description
    is_active = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # Admin approval status
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=True)  # Associated restaurant
    
    # Document storage fields - updated to match registration system
    license_document = db.Column(db.String(500))  # License document URL
    license_front_url = db.Column(db.String(500))  # License front URL
    license_back_url = db.Column(db.String(500))  # License back URL
    id_document = db.Column(db.String(500))  # ID document URL
    id_front_url = db.Column(db.String(500))  # ID front URL
    id_back_url = db.Column(db.String(500))  # ID back URL
    vehicle_document = db.Column(db.String(500))  # Vehicle registration document URL
    vehicle_registration_url = db.Column(db.String(500))  # Vehicle registration URL
    
    rejection_reason = db.Column(db.Text)  # Reason for rejection
    approved_by = db.Column(db.Integer, db.ForeignKey('admin_user.id'))
    approved_at = db.Column(db.DateTime)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)  # Registration date
    current_lat = db.Column(db.Float)
    current_lng = db.Column(db.Float)
    last_location_update = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref='drivers')

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    username = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    language = db.Column(db.String(10), default='en')  # en, am, or, ti
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    live_location_period = db.Column(db.Integer, default=0)  # Live location tracking period
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdminActivity(db.Model):
    """Track admin activities for performance monitoring"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # order_processed, menu_updated, driver_approved, etc.
    entity_type = db.Column(db.String(50))  # order, menu_item, driver, etc.
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    response_time = db.Column(db.Float)  # Time taken to complete action in minutes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    admin = db.relationship('AdminUser', backref='activities')
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'action_type': self.action_type,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'response_time': self.response_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AdminSession(db.Model):
    """Track admin login sessions for security and performance"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))  # Support both IPv4 and IPv6
    user_agent = db.Column(db.Text)
    session_duration = db.Column(db.Integer)  # in minutes
    actions_performed = db.Column(db.Integer, default=0)
    
    admin = db.relationship('AdminUser', backref='sessions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'logout_time': self.logout_time.isoformat() if self.logout_time else None,
            'ip_address': self.ip_address,
            'session_duration': self.session_duration,
            'actions_performed': self.actions_performed
        }

class KitchenStaff(db.Model):
    """Kitchen staff management"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    avatar_url = db.Column(db.String(500))  # Profile image/avatar
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False, default=1)
    is_active = db.Column(db.Boolean, default=True)
    position = db.Column(db.String(50), default='Kitchen Staff')  # Chef, Cook, Assistant, etc.
    hire_date = db.Column(db.Date, default=datetime.utcnow)
    salary = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    restaurant = db.relationship('Restaurant', backref='kitchen_staff')
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'phone': self.phone,
            'email': self.email,
            'avatar_url': self.avatar_url,
            'restaurant_id': self.restaurant_id,
            'is_active': self.is_active,
            'position': self.position,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'salary': self.salary,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MenuItemModification(db.Model):
    """Track menu item changes for audit trail"""
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # created, updated, deleted, activated, deactivated
    old_values = db.Column(db.JSON)  # Previous values
    new_values = db.Column(db.JSON)  # New values
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    menu_item = db.relationship('MenuItem', backref='modifications')
    admin = db.relationship('AdminUser', backref='menu_modifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'admin_id': self.admin_id,
            'action': self.action,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PaymentTransaction(db.Model):
    """Payment transaction tracking for deposits and full payments"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # 'deposit', 'full_payment'
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # 'CBE Birr', 'M-Pesa', 'Bank Transfer', 'Cash'
    transaction_id = db.Column(db.String(100))
    screenshot_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending_verification')  # 'pending_verification', 'verified', 'rejected'
    admin_notes = db.Column(db.Text)
    verified_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to order
    order = db.relationship('Order', backref='payment_transactions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'payment_type': self.payment_type,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'screenshot_url': self.screenshot_url,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
