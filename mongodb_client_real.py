"""
Real MongoDB Atlas Client using PyMongo
Using actual MongoDB Atlas database connection
"""
import pymongo
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class RealMongoDBClient:
    """Real MongoDB Atlas Client using PyMongo"""
    
    def __init__(self):
        # Your MongoDB Atlas connection string
        self.connection_string = "mongodb+srv://almeseged:A1l2m3e4s5@cluster0.t6sz6bo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.database_name = "etfood_delivery"
        
        try:
            # Create MongoDB client
            self.client = pymongo.MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB Atlas!")
            
            # Initialize collections if they don't exist
            self._initialize_collections()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    def _initialize_collections(self):
        """Initialize collections with default data if empty"""
        try:
            # Check if restaurants collection exists and has data
            if self.db.restaurants.count_documents({}) == 0:
                self._create_default_data()
                logger.info("📦 Initialized database with default data")
            else:
                logger.info("📊 Database already contains data")
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
    
    def _generate_id(self) -> str:
        """Generate a unique string ID"""
        return str(uuid.uuid4())
    
    def _create_default_data(self):
        """Create default restaurants, categories, and menu items"""
        # Create default restaurants
        flavour_id = self._generate_id()
        y_factory_id = self._generate_id()
        
        restaurants = [
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
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'id': y_factory_id,
                'name': 'Y Factory Restaurant',
                'description': 'Modern Ethiopian Fusion Cuisine',
                'address': 'Bole, Addis Ababa',
                'phone': '+251911654321',
                'latitude': 9.0084,
                'longitude': 38.7975,
                'logo_url': None,
                'cover_image_url': None,
                'is_active': True,
                'is_featured': False,
                'delivery_fee': 25.0,
                'minimum_order': 100.0,
                'estimated_delivery_time': '25-40 minutes',
                'opening_hours': {},
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        
        # Insert restaurants
        self.db.restaurants.insert_many(restaurants)
        
        # Create categories
        categories = [
            {'id': self._generate_id(), 'name': 'Burgers', 'description': 'Delicious burgers', 'restaurant_id': flavour_id, 'created_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Pizza', 'description': 'Fresh pizzas', 'restaurant_id': flavour_id, 'created_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Drinks', 'description': 'Refreshing drinks', 'restaurant_id': flavour_id, 'created_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Shawarma', 'description': 'Authentic shawarma', 'restaurant_id': flavour_id, 'created_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Traditional Ethiopian Breakfast', 'description': 'Ethiopian traditional foods', 'restaurant_id': flavour_id, 'created_at': datetime.utcnow()}
        ]
        
        self.db.categories.insert_many(categories)
        
        # Create menu items
        menu_items = [
            # Burgers
            {'id': self._generate_id(), 'name': 'Beef Burger Normal', 'description': 'Delicious beef burger with classic toppings', 'price': 400.0, 'category': 'Burgers', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975047_images_25.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Chicken Burger Special', 'description': 'Premium chicken burger with special sauce', 'price': 540.0, 'category': 'Burgers', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975080_images_26.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Cheese Burger', 'description': 'Juicy burger with melted cheese', 'price': 450.0, 'category': 'Burgers', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975114_images_27.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            
            # Pizza
            {'id': self._generate_id(), 'name': 'Margherita Pizza', 'description': 'Classic pizza with tomato and mozzarella', 'price': 450.0, 'category': 'Pizza', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Pepperoni Pizza', 'description': 'Pizza with pepperoni and cheese', 'price': 520.0, 'category': 'Pizza', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751976242_images_35.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            
            # Drinks
            {'id': self._generate_id(), 'name': 'Ethiopian Coffee', 'description': 'Traditional Ethiopian coffee', 'price': 80.0, 'category': 'Drinks', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975047_images_25.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Fresh Juice', 'description': 'Freshly squeezed fruit juice', 'price': 120.0, 'category': 'Drinks', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975080_images_26.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Soft Drink', 'description': 'Carbonated soft drink', 'price': 60.0, 'category': 'Drinks', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975114_images_27.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            
            # Shawarma
            {'id': self._generate_id(), 'name': 'Beef Shawarma Large', 'description': 'Large beef shawarma with traditional spices', 'price': 495.0, 'category': 'Shawarma', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975388_images_28.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Chicken Shawarma Small', 'description': 'Small chicken shawarma with authentic taste', 'price': 430.0, 'category': 'Shawarma', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975863_images_33.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Chicken Shawarma Large', 'description': 'Large chicken shawarma with extra filling', 'price': 520.0, 'category': 'Shawarma', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975907_fried-egg-sandwich_1.webp', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            
            # Traditional Ethiopian Breakfast
            {'id': self._generate_id(), 'name': 'Injera with Doro Wat', 'description': 'Traditional Ethiopian injera with spicy chicken stew', 'price': 350.0, 'category': 'Traditional Ethiopian Breakfast', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975047_images_25.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Kitfo', 'description': 'Ethiopian beef tartare', 'price': 280.0, 'category': 'Traditional Ethiopian Breakfast', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975080_images_26.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Tibs', 'description': 'Ethiopian sautéed meat', 'price': 320.0, 'category': 'Traditional Ethiopian Breakfast', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975388_images_28.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
            {'id': self._generate_id(), 'name': 'Shiro Wat', 'description': 'Ethiopian chickpea stew', 'price': 180.0, 'category': 'Traditional Ethiopian Breakfast', 'restaurant_id': flavour_id, 'image_url': '/static/uploads/1751975114_images_27.jpg', 'available': True, 'created_at': datetime.utcnow(), 'updated_at': datetime.utcnow()},
        ]
        
        self.db.menu_items.insert_many(menu_items)
        
        # Create admin users
        admin_users = [
            {
                'id': self._generate_id(),
                'username': 'admin',
                'password': 'admin123',  # In production, this should be hashed
                'email': 'admin@etfood.com',
                'role': 'admin',
                'restaurant_id': flavour_id,
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            },
            {
                'id': self._generate_id(),
                'username': 'superadmin',
                'password': 'superadmin123',  # In production, this should be hashed
                'email': 'superadmin@etfood.com',
                'role': 'superadmin',
                'restaurant_id': None,
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        
        self.db.admin_users.insert_many(admin_users)
    
    # Collection operations
    def insert_one(self, collection_name: str, data: Dict) -> str:
        """Insert a single document and return its ID"""
        try:
            if 'id' not in data:
                data['id'] = self._generate_id()
            if 'created_at' not in data:
                data['created_at'] = datetime.utcnow()
            if 'updated_at' not in data:
                data['updated_at'] = datetime.utcnow()
            
            result = self.db[collection_name].insert_one(data)
            return data['id']
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            return None
    
    def find_one(self, collection_name: str, filter_dict: Dict) -> Optional[Dict]:
        """Find a single document"""
        try:
            result = self.db[collection_name].find_one(filter_dict)
            if result:
                # Remove MongoDB's _id field
                result.pop('_id', None)
            return result
        except Exception as e:
            logger.error(f"Error finding document: {e}")
            return None
    
    def find_many(self, collection_name: str, filter_dict: Dict = None, sort: str = None, limit: int = None) -> List[Dict]:
        """Find multiple documents"""
        try:
            query = self.db[collection_name].find(filter_dict or {})
            
            if sort:
                # Sort by field (assuming ascending order)
                query = query.sort(sort, 1)
            
            if limit:
                query = query.limit(limit)
            
            results = list(query)
            # Remove MongoDB's _id field from all results
            for result in results:
                result.pop('_id', None)
            
            return results
        except Exception as e:
            logger.error(f"Error finding documents: {e}")
            return []
    
    def update_one(self, collection_name: str, filter_dict: Dict, update_data: Dict) -> bool:
        """Update a single document"""
        try:
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.db[collection_name].update_one(filter_dict, {'$set': update_data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return False
    
    def delete_one(self, collection_name: str, filter_dict: Dict) -> bool:
        """Delete a single document"""
        try:
            result = self.db[collection_name].delete_one(filter_dict)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def count_documents(self, collection_name: str, filter_dict: Dict = None) -> int:
        """Count documents"""
        try:
            return self.db[collection_name].count_documents(filter_dict or {})
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0

# Create global MongoDB client instance
mongo_client = RealMongoDBClient()