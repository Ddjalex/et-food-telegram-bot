from extensions import db
from datetime import datetime
from sqlalchemy import func

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50), default='burgers')  # burgers, snacks, sauces, drinks
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'image_url': self.image_url,
            'category': self.category,
            'available': self.available
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
    location_lat = db.Column(db.Float)
    location_lng = db.Column(db.Float)
    delivery_notes = db.Column(db.Text)
    estimated_delivery_time = db.Column(db.DateTime)
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
            'location_lat': self.location_lat,
            'location_lng': self.location_lng,
            'delivery_notes': self.delivery_notes,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)

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
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(10), default='🍽️')
    image_url = db.Column(db.String(500))  # Optional category image
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
