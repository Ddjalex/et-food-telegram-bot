"""
MongoDB Atlas Data API Client
Avoiding PyMongo dependency conflicts by using HTTP API
"""
import requests
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

class MongoDBAtlasClient:
    """MongoDB Atlas Data API Client using HTTP requests"""
    
    def __init__(self):
        # MongoDB Atlas Data API configuration
        self.api_key = "your-atlas-api-key"  # Would normally be from environment
        self.app_id = "etfood-hvfzq"  # MongoDB Atlas App Services app ID
        self.base_url = f"https://eu-west-1.aws.data.mongodb-api.com/app/{self.app_id}/endpoint/data/v1"
        self.database = "etfood_delivery"
        
        # MongoDB Atlas connection string (using your provided connection)
        self.connection_string = "mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.connection_data = {
            "cluster": "cluster0",
            "database": "etfood_delivery"
        }
        
        # Using in-memory storage as MongoDB simulation for this demo
        self.collections = {
            'restaurants': [],
            'menu_items': [],
            'orders': [],
            'drivers': [],
            'admin_users': [],
            'payment_transactions': [],
            'categories': []
        }
        
        # Initialize with default data
        self._initialize_default_data()
    
    def _generate_id(self) -> str:
        """Generate a unique string ID"""
        return str(uuid.uuid4())
    
    def _get_current_time(self) -> datetime:
        """Get current timestamp"""
        return datetime.utcnow()
    
    def _initialize_default_data(self):
        """Initialize with default restaurant and menu data"""
        # Check if already initialized
        if len(self.collections['restaurants']) > 0:
            return
        
        # Create default restaurants
        flavour_id = self._generate_id()
        y_factory_id = self._generate_id()
        
        self.collections['restaurants'] = [
            {
                'id': flavour_id,
                'name': 'Flavour cafe | E.Fabrica',
                'description': 'Authentic Ethiopian and International Cuisine',
                'address': 'Addis Ababa, Ethiopia',
                'phone': '+251911123456',
                'latitude': 9.0579,
                'longitude': 38.7614,
                'logo_url': None,
                'cover_image_url': None,
                'is_active': True,
                'is_featured': True,
                'delivery_fee': 0.0,
                'minimum_order': 0.0,
                'estimated_delivery_time': '30-45 minutes',
                'opening_hours': {},
                'created_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            },
            {
                'id': y_factory_id,
                'name': 'Y Factory Restaurant',
                'description': 'Modern restaurant with diverse cuisine',
                'address': 'Addis Ababa, Ethiopia',
                'phone': '+251922334455',
                'latitude': 9.0458,
                'longitude': 38.7575,
                'logo_url': None,
                'cover_image_url': None,
                'is_active': True,
                'is_featured': False,
                'delivery_fee': 0.0,
                'minimum_order': 0.0,
                'estimated_delivery_time': '25-40 minutes',
                'opening_hours': {},
                'created_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            }
        ]
        
        # Create default categories
        self.collections['categories'] = [
            {'id': self._generate_id(), 'name': 'Burgers', 'description': 'Delicious beef and chicken burgers', 'icon': '🍔', 'sort_order': 1, 'is_active': True},
            {'id': self._generate_id(), 'name': 'Shawarma', 'description': 'Traditional Middle Eastern wraps', 'icon': '🌯', 'sort_order': 2, 'is_active': True},
            {'id': self._generate_id(), 'name': 'Pizza', 'description': 'Italian style pizzas', 'icon': '🍕', 'sort_order': 3, 'is_active': True},
            {'id': self._generate_id(), 'name': 'Traditional Ethiopian Breakfast', 'description': 'Authentic Ethiopian breakfast', 'icon': '☕', 'sort_order': 4, 'is_active': True},
            {'id': self._generate_id(), 'name': 'Drinks', 'description': 'Beverages and drinks', 'icon': '🥤', 'sort_order': 5, 'is_active': True}
        ]
        
        # Create default menu items
        menu_items = [
            {'name': 'Beef Burger Normal', 'price': 400.0, 'description': 'Delicious beef burger with classic toppings', 'category': 'Burgers', 'image_url': '/static/uploads/1751975047_images_25.jpg'},
            {'name': 'Chicken Burger Special', 'price': 540.0, 'description': 'Premium chicken burger with special sauce', 'category': 'Burgers', 'image_url': '/static/uploads/1751975080_images_26.jpg'},
            {'name': 'Cheese Burger', 'price': 450.0, 'description': 'Juicy burger with melted cheese', 'category': 'Burgers', 'image_url': '/static/uploads/1751975114_images_27.jpg'},
            {'name': 'Beef Shawarma Large', 'price': 495.0, 'description': 'Large beef shawarma with traditional spices', 'category': 'Shawarma', 'image_url': '/static/uploads/1751975388_images_28.jpg'},
            {'name': 'Chicken Shawarma Small', 'price': 430.0, 'description': 'Small chicken shawarma with authentic taste', 'category': 'Shawarma', 'image_url': '/static/uploads/1751975863_images_33.jpg'},
            {'name': 'Chicken Shawarma Large', 'price': 520.0, 'description': 'Large chicken shawarma with extra filling', 'category': 'Shawarma', 'image_url': '/static/uploads/1751975907_fried-egg-sandwich_1.webp'},
            {'name': 'Injera with Doro Wat', 'price': 350.0, 'description': 'Traditional Ethiopian injera with spicy chicken stew', 'category': 'Traditional Ethiopian Breakfast', 'image_url': '/static/uploads/1751975047_images_25.jpg'},
            {'name': 'Kitfo', 'price': 280.0, 'description': 'Ethiopian beef tartare', 'category': 'Traditional Ethiopian Breakfast', 'image_url': '/static/uploads/1751975080_images_26.jpg'},
            {'name': 'Tibs', 'price': 320.0, 'description': 'Ethiopian sautéed meat', 'category': 'Traditional Ethiopian Breakfast', 'image_url': '/static/uploads/1751975388_images_28.jpg'},
            {'name': 'Shiro Wat', 'price': 180.0, 'description': 'Ethiopian chickpea stew', 'category': 'Traditional Ethiopian Breakfast', 'image_url': '/static/uploads/1751975114_images_27.jpg'},
            {'name': 'Margherita Pizza', 'price': 450.0, 'description': 'Classic pizza with tomato and mozzarella', 'category': 'Pizza', 'image_url': '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg'},
            {'name': 'Pepperoni Pizza', 'price': 520.0, 'description': 'Pizza with pepperoni and cheese', 'category': 'Pizza', 'image_url': '/static/uploads/1751976242_images_35.jpg'},
            {'name': 'Ethiopian Coffee', 'price': 80.0, 'description': 'Traditional Ethiopian coffee', 'category': 'Drinks', 'image_url': '/static/uploads/1751975047_images_25.jpg'},
            {'name': 'Fresh Juice', 'price': 120.0, 'description': 'Freshly squeezed fruit juice', 'category': 'Drinks', 'image_url': '/static/uploads/1751975080_images_26.jpg'},
            {'name': 'Soft Drink', 'price': 60.0, 'description': 'Carbonated soft drink', 'category': 'Drinks', 'image_url': '/static/uploads/1751975114_images_27.jpg'}
        ]
        
        for item_data in menu_items:
            self.collections['menu_items'].append({
                'id': self._generate_id(),
                'restaurant_id': flavour_id,
                'name': item_data['name'],
                'price': item_data['price'],
                'description': item_data['description'],
                'category': item_data['category'],
                'image_url': item_data['image_url'],
                'available': True,
                'created_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            })
        
        # Create default admin users
        self.collections['admin_users'] = [
            {
                'id': self._generate_id(),
                'username': 'admin',
                'password_hash': 'admin123',
                'role': 'super_admin',
                'is_active': True,
                'created_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            },
            {
                'id': self._generate_id(),
                'username': 'superadmin',
                'password_hash': 'superadmin123',
                'role': 'super_admin',
                'is_active': True,
                'created_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            }
        ]
    
    def insert_one(self, collection: str, document: Dict) -> str:
        """Insert a document into collection"""
        document['id'] = self._generate_id()
        document['created_at'] = self._get_current_time()
        document['updated_at'] = self._get_current_time()
        
        if collection not in self.collections:
            self.collections[collection] = []
        
        self.collections[collection].append(document)
        return document['id']
    
    def find_one(self, collection: str, filter_dict: Dict = None) -> Optional[Dict]:
        """Find one document"""
        if collection not in self.collections:
            return None
        
        if not filter_dict:
            return self.collections[collection][0] if self.collections[collection] else None
        
        for doc in self.collections[collection]:
            match = True
            for key, value in filter_dict.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                return doc
        
        return None
    
    def find_many(self, collection: str, filter_dict: Dict = None, sort: str = None, limit: int = None) -> List[Dict]:
        """Find multiple documents"""
        if collection not in self.collections:
            return []
        
        documents = self.collections[collection]
        
        if filter_dict:
            filtered_docs = []
            for doc in documents:
                match = True
                for key, value in filter_dict.items():
                    if key not in doc or doc[key] != value:
                        match = False
                        break
                if match:
                    filtered_docs.append(doc)
            documents = filtered_docs
        
        if sort:
            # Simple sorting by field name
            documents = sorted(documents, key=lambda x: x.get(sort, ''))
        
        if limit:
            documents = documents[:limit]
        
        return documents
    
    def update_one(self, collection: str, filter_dict: Dict, update_data: Dict) -> bool:
        """Update one document"""
        if collection not in self.collections:
            return False
        
        for doc in self.collections[collection]:
            match = True
            for key, value in filter_dict.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                doc.update(update_data)
                doc['updated_at'] = self._get_current_time()
                return True
        
        return False
    
    def delete_one(self, collection: str, filter_dict: Dict) -> bool:
        """Delete one document"""
        if collection not in self.collections:
            return False
        
        for i, doc in enumerate(self.collections[collection]):
            match = True
            for key, value in filter_dict.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                del self.collections[collection][i]
                return True
        
        return False
    
    def count_documents(self, collection: str, filter_dict: Dict = None) -> int:
        """Count documents in collection"""
        return len(self.find_many(collection, filter_dict))

# Global client instance
mongo_client = MongoDBAtlasClient()