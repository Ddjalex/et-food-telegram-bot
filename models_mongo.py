"""
MongoDB Models for ET-FOOD Delivery System
Using PyMongo for direct MongoDB operations
"""
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
from typing import Optional, Dict, List, Any

# MongoDB Connection
MONGO_URI = "mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.etfood_delivery

class BaseModel:
    """Base model with common functionality"""
    
    def __init__(self, collection_name: str):
        self.collection = db[collection_name]
    
    def to_dict(self, doc: Dict) -> Dict:
        """Convert MongoDB document to dictionary with string ID"""
        if doc and '_id' in doc:
            doc['id'] = str(doc['_id'])
            del doc['_id']
        return doc
    
    def insert_one(self, data: Dict) -> str:
        """Insert a single document and return its ID"""
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        result = self.collection.insert_one(data)
        return str(result.inserted_id)
    
    def find_one(self, filter_dict: Dict) -> Optional[Dict]:
        """Find a single document"""
        doc = self.collection.find_one(filter_dict)
        return self.to_dict(doc) if doc else None
    
    def find_by_id(self, doc_id: str) -> Optional[Dict]:
        """Find document by ID"""
        try:
            return self.find_one({"_id": ObjectId(doc_id)})
        except:
            return None
    
    def find_many(self, filter_dict: Dict = None, sort: List = None, limit: int = None) -> List[Dict]:
        """Find multiple documents"""
        filter_dict = filter_dict or {}
        cursor = self.collection.find(filter_dict)
        
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
            
        return [self.to_dict(doc) for doc in cursor]
    
    def update_one(self, filter_dict: Dict, update_data: Dict) -> bool:
        """Update a single document"""
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(filter_dict, {"$set": update_data})
        return result.modified_count > 0
    
    def update_by_id(self, doc_id: str, update_data: Dict) -> bool:
        """Update document by ID"""
        try:
            return self.update_one({"_id": ObjectId(doc_id)}, update_data)
        except:
            return False
    
    def delete_one(self, filter_dict: Dict) -> bool:
        """Delete a single document"""
        result = self.collection.delete_one(filter_dict)
        return result.deleted_count > 0
    
    def delete_by_id(self, doc_id: str) -> bool:
        """Delete document by ID"""
        try:
            return self.delete_one({"_id": ObjectId(doc_id)})
        except:
            return False
    
    def count(self, filter_dict: Dict = None) -> int:
        """Count documents"""
        filter_dict = filter_dict or {}
        return self.collection.count_documents(filter_dict)

class Restaurant(BaseModel):
    def __init__(self):
        super().__init__('restaurants')
    
    def create(self, name: str, description: str = None, **kwargs) -> str:
        """Create a new restaurant"""
        data = {
            'name': name,
            'description': description,
            'address': kwargs.get('address'),
            'phone': kwargs.get('phone'),
            'latitude': kwargs.get('latitude'),
            'longitude': kwargs.get('longitude'),
            'logo_url': kwargs.get('logo_url'),
            'cover_image_url': kwargs.get('cover_image_url'),
            'is_active': kwargs.get('is_active', True),
            'is_featured': kwargs.get('is_featured', False),
            'delivery_fee': kwargs.get('delivery_fee', 0.0),
            'minimum_order': kwargs.get('minimum_order', 0.0),
            'estimated_delivery_time': kwargs.get('estimated_delivery_time', '30-45 minutes'),
            'opening_hours': kwargs.get('opening_hours', {})
        }
        return self.insert_one(data)
    
    def get_active_restaurants(self) -> List[Dict]:
        """Get all active restaurants"""
        return self.find_many({'is_active': True})
    
    def get_featured_restaurants(self) -> List[Dict]:
        """Get featured restaurants"""
        return self.find_many({'is_active': True, 'is_featured': True})

class MenuItem(BaseModel):
    def __init__(self):
        super().__init__('menu_items')
    
    def create(self, name: str, price: float, restaurant_id: str, **kwargs) -> str:
        """Create a new menu item"""
        data = {
            'name': name,
            'price': price,
            'restaurant_id': restaurant_id,
            'description': kwargs.get('description'),
            'image_url': kwargs.get('image_url'),
            'category': kwargs.get('category', 'main'),
            'available': kwargs.get('available', True),
            'ingredients': kwargs.get('ingredients', []),
            'allergens': kwargs.get('allergens', []),
            'nutritional_info': kwargs.get('nutritional_info', {}),
            'preparation_time': kwargs.get('preparation_time', 15)
        }
        return self.insert_one(data)
    
    def get_by_restaurant(self, restaurant_id: str, available_only: bool = True) -> List[Dict]:
        """Get menu items for a specific restaurant"""
        filter_dict = {'restaurant_id': restaurant_id}
        if available_only:
            filter_dict['available'] = True
        return self.find_many(filter_dict, sort=[('category', 1), ('name', 1)])
    
    def get_by_category(self, restaurant_id: str, category: str) -> List[Dict]:
        """Get menu items by category"""
        return self.find_many({
            'restaurant_id': restaurant_id,
            'category': category,
            'available': True
        })
    
    def update_availability(self, item_id: str, available: bool) -> bool:
        """Update item availability"""
        return self.update_by_id(item_id, {'available': available})

class Order(BaseModel):
    def __init__(self):
        super().__init__('orders')
    
    def create(self, customer_name: str, customer_phone: str, restaurant_id: str, items: List[Dict], **kwargs) -> str:
        """Create a new order"""
        data = {
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'customer_address': kwargs.get('customer_address'),
            'restaurant_id': restaurant_id,
            'telegram_user_id': kwargs.get('telegram_user_id'),
            'items': items,
            'total_amount': kwargs.get('total_amount', 0.0),
            'delivery_fee': kwargs.get('delivery_fee', 0.0),
            'status': kwargs.get('status', 'pending'),
            'payment_method': kwargs.get('payment_method', 'cash'),
            'payment_status': kwargs.get('payment_status', 'pending'),
            'location_lat': kwargs.get('location_lat'),
            'location_lng': kwargs.get('location_lng'),
            'special_instructions': kwargs.get('special_instructions'),
            'driver_id': kwargs.get('driver_id'),
            'estimated_delivery_time': kwargs.get('estimated_delivery_time'),
            'order_number': self._generate_order_number()
        }
        return self.insert_one(data)
    
    def _generate_order_number(self) -> str:
        """Generate unique order number"""
        import time
        return f"ET{int(time.time())}"
    
    def get_by_restaurant(self, restaurant_id: str, status: str = None) -> List[Dict]:
        """Get orders for a specific restaurant"""
        filter_dict = {'restaurant_id': restaurant_id}
        if status:
            filter_dict['status'] = status
        return self.find_many(filter_dict, sort=[('created_at', -1)])
    
    def get_by_customer(self, telegram_user_id: str) -> List[Dict]:
        """Get orders for a customer"""
        return self.find_many({'telegram_user_id': telegram_user_id}, sort=[('created_at', -1)])
    
    def update_status(self, order_id: str, status: str, **kwargs) -> bool:
        """Update order status"""
        update_data = {'status': status}
        if 'driver_id' in kwargs:
            update_data['driver_id'] = kwargs['driver_id']
        if 'estimated_delivery_time' in kwargs:
            update_data['estimated_delivery_time'] = kwargs['estimated_delivery_time']
        return self.update_by_id(order_id, update_data)

class Driver(BaseModel):
    def __init__(self):
        super().__init__('drivers')
    
    def create(self, name: str, phone_number: str, **kwargs) -> str:
        """Create a new driver"""
        data = {
            'name': name,
            'phone_number': phone_number,
            'telegram_user_id': kwargs.get('telegram_user_id'),
            'vehicle_type': kwargs.get('vehicle_type', 'motorcycle'),
            'license_number': kwargs.get('license_number'),
            'vehicle_registration': kwargs.get('vehicle_registration'),
            'is_active': kwargs.get('is_active', True),
            'is_available': kwargs.get('is_available', True),
            'is_approved': kwargs.get('is_approved', False),
            'current_lat': kwargs.get('current_lat'),
            'current_lng': kwargs.get('current_lng'),
            'last_location_update': kwargs.get('last_location_update'),
            'rating': kwargs.get('rating', 5.0),
            'total_deliveries': kwargs.get('total_deliveries', 0),
            'documents': kwargs.get('documents', {}),
            'restaurant_id': kwargs.get('restaurant_id')
        }
        return self.insert_one(data)
    
    def get_available_drivers(self, restaurant_id: str = None) -> List[Dict]:
        """Get available drivers"""
        filter_dict = {
            'is_active': True,
            'is_available': True,
            'is_approved': True
        }
        if restaurant_id:
            filter_dict['restaurant_id'] = restaurant_id
        return self.find_many(filter_dict)
    
    def update_location(self, driver_id: str, lat: float, lng: float) -> bool:
        """Update driver location"""
        return self.update_by_id(driver_id, {
            'current_lat': lat,
            'current_lng': lng,
            'last_location_update': datetime.utcnow()
        })
    
    def update_availability(self, driver_id: str, is_available: bool) -> bool:
        """Update driver availability"""
        return self.update_by_id(driver_id, {'is_available': is_available})

class AdminUser(BaseModel):
    def __init__(self):
        super().__init__('admin_users')
    
    def create(self, username: str, **kwargs) -> str:
        """Create a new admin user"""
        data = {
            'username': username,
            'password_hash': kwargs.get('password_hash'),
            'role': kwargs.get('role', 'admin'),
            'restaurant_id': kwargs.get('restaurant_id'),
            'telegram_user_id': kwargs.get('telegram_user_id'),
            'is_active': kwargs.get('is_active', True),
            'last_login': kwargs.get('last_login'),
            'permissions': kwargs.get('permissions', [])
        }
        return self.insert_one(data)
    
    def find_by_username(self, username: str) -> Optional[Dict]:
        """Find admin by username"""
        return self.find_one({'username': username})
    
    def update_last_login(self, user_id: str) -> bool:
        """Update last login time"""
        return self.update_by_id(user_id, {'last_login': datetime.utcnow()})

class PaymentTransaction(BaseModel):
    def __init__(self):
        super().__init__('payment_transactions')
    
    def create(self, order_id: str, amount: float, **kwargs) -> str:
        """Create a new payment transaction"""
        data = {
            'order_id': order_id,
            'amount': amount,
            'payment_method': kwargs.get('payment_method', 'cash'),
            'status': kwargs.get('status', 'pending'),
            'transaction_id': kwargs.get('transaction_id'),
            'receipt_image_url': kwargs.get('receipt_image_url'),
            'verified_by': kwargs.get('verified_by'),
            'verified_at': kwargs.get('verified_at'),
            'notes': kwargs.get('notes')
        }
        return self.insert_one(data)
    
    def get_by_order(self, order_id: str) -> List[Dict]:
        """Get transactions for an order"""
        return self.find_many({'order_id': order_id}, sort=[('created_at', -1)])
    
    def update_status(self, transaction_id: str, status: str, verified_by: str = None) -> bool:
        """Update payment status"""
        update_data = {'status': status}
        if verified_by:
            update_data['verified_by'] = verified_by
            update_data['verified_at'] = datetime.utcnow()
        return self.update_by_id(transaction_id, update_data)

class Category(BaseModel):
    def __init__(self):
        super().__init__('categories')
    
    def create(self, name: str, **kwargs) -> str:
        """Create a new category"""
        data = {
            'name': name,
            'description': kwargs.get('description'),
            'icon': kwargs.get('icon'),
            'sort_order': kwargs.get('sort_order', 0),
            'is_active': kwargs.get('is_active', True)
        }
        return self.insert_one(data)
    
    def get_active_categories(self) -> List[Dict]:
        """Get all active categories"""
        return self.find_many({'is_active': True}, sort=[('sort_order', 1)])

# Initialize model instances
restaurant_model = Restaurant()
menu_item_model = MenuItem()
order_model = Order()
driver_model = Driver()
admin_user_model = AdminUser()
payment_transaction_model = PaymentTransaction()
category_model = Category()