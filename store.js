const { v4: uuidv4 } = require('uuid');

class Store {
    constructor() {
        this.collections = {
            restaurants: [],
            menu_items: [],
            orders: [],
            drivers: [],
            admin_users: [],
            payment_transactions: [],
            categories: []
        };
        this._initializeDefaults();
    }

    _generateId() { return uuidv4(); }
    _now() { return new Date(); }

    _initializeDefaults() {
        const flavourId = this._generateId();
        const yFactoryId = this._generateId();

        this.collections.restaurants = [
            { id: flavourId, name: 'Flavour cafe | E.Fabrica', description: 'Authentic Ethiopian and International Cuisine', address: 'Addis Ababa, Ethiopia', phone: '+251911123456', logo_url: null, cover_image_url: null, is_active: true, is_featured: true, delivery_fee: 0, minimum_order: 0, estimated_delivery_time: '30-45 minutes', rating: 4.5, created_at: this._now(), updated_at: this._now() },
            { id: yFactoryId, name: 'Y Factory Restaurant', description: 'Modern restaurant with diverse cuisine', address: 'Addis Ababa, Ethiopia', phone: '+251922334455', logo_url: null, cover_image_url: null, is_active: true, is_featured: false, delivery_fee: 0, minimum_order: 0, estimated_delivery_time: '25-40 minutes', rating: 4.3, created_at: this._now(), updated_at: this._now() }
        ];

        this.collections.categories = [
            { id: this._generateId(), name: 'Burgers', description: 'Delicious beef and chicken burgers', icon: '🍔', sort_order: 1, is_active: true },
            { id: this._generateId(), name: 'Shawarma', description: 'Traditional Middle Eastern wraps', icon: '🌯', sort_order: 2, is_active: true },
            { id: this._generateId(), name: 'Pizza', description: 'Italian style pizzas', icon: '🍕', sort_order: 3, is_active: true },
            { id: this._generateId(), name: 'Traditional Ethiopian Breakfast', description: 'Authentic Ethiopian breakfast', icon: '☕', sort_order: 4, is_active: true },
            { id: this._generateId(), name: 'Drinks', description: 'Beverages and drinks', icon: '🥤', sort_order: 5, is_active: true }
        ];

        const menuItems = [
            { name: 'Beef Burger Normal', price: 400, description: 'Delicious beef burger with classic toppings', category: 'Burgers', image_url: '/static/uploads/1751975047_images_25.jpg' },
            { name: 'Chicken Burger Special', price: 540, description: 'Premium chicken burger with special sauce', category: 'Burgers', image_url: '/static/uploads/1751975080_images_26.jpg' },
            { name: 'Cheese Burger', price: 450, description: 'Juicy burger with melted cheese', category: 'Burgers', image_url: '/static/uploads/1751975114_images_27.jpg' },
            { name: 'Beef Shawarma Large', price: 495, description: 'Large beef shawarma with traditional spices', category: 'Shawarma', image_url: '/static/uploads/1751975388_images_28.jpg' },
            { name: 'Chicken Shawarma Small', price: 430, description: 'Small chicken shawarma with authentic taste', category: 'Shawarma', image_url: '/static/uploads/1751975863_images_33.jpg' },
            { name: 'Chicken Shawarma Large', price: 520, description: 'Large chicken shawarma with extra filling', category: 'Shawarma', image_url: '/static/uploads/1751975907_fried-egg-sandwich_1.webp' },
            { name: 'Injera with Doro Wat', price: 350, description: 'Traditional Ethiopian injera with spicy chicken stew', category: 'Traditional Ethiopian Breakfast', image_url: '/static/uploads/1751975047_images_25.jpg' },
            { name: 'Kitfo', price: 280, description: 'Ethiopian beef tartare', category: 'Traditional Ethiopian Breakfast', image_url: '/static/uploads/1751975080_images_26.jpg' },
            { name: 'Tibs', price: 320, description: 'Ethiopian sautéed meat', category: 'Traditional Ethiopian Breakfast', image_url: '/static/uploads/1751975388_images_28.jpg' },
            { name: 'Shiro Wat', price: 180, description: 'Ethiopian chickpea stew', category: 'Traditional Ethiopian Breakfast', image_url: '/static/uploads/1751975114_images_27.jpg' },
            { name: 'Margherita Pizza', price: 450, description: 'Classic pizza with tomato and mozzarella', category: 'Pizza', image_url: '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg' },
            { name: 'Pepperoni Pizza', price: 520, description: 'Pizza with pepperoni and cheese', category: 'Pizza', image_url: '/static/uploads/1751976242_images_35.jpg' },
            { name: 'Ethiopian Coffee', price: 80, description: 'Traditional Ethiopian coffee', category: 'Drinks', image_url: '/static/uploads/1751975047_images_25.jpg' },
            { name: 'Fresh Juice', price: 120, description: 'Freshly squeezed fruit juice', category: 'Drinks', image_url: '/static/uploads/1751975080_images_26.jpg' },
            { name: 'Soft Drink', price: 60, description: 'Carbonated soft drink', category: 'Drinks', image_url: '/static/uploads/1751975114_images_27.jpg' }
        ];

        for (const item of menuItems) {
            this.collections.menu_items.push({
                id: this._generateId(),
                restaurant_id: flavourId,
                available: true,
                ingredients: [],
                allergens: [],
                nutritional_info: {},
                preparation_time: 15,
                created_at: this._now(),
                updated_at: this._now(),
                ...item
            });
        }

        this.collections.admin_users = [
            { id: this._generateId(), username: 'admin', password: 'admin123', full_name: 'Admin User', role: 'admin', is_active: true, restaurant_id: flavourId, created_at: this._now(), updated_at: this._now() },
            { id: this._generateId(), username: 'superadmin', password: 'superadmin123', full_name: 'Super Administrator', role: 'superadmin', is_active: true, created_at: this._now(), updated_at: this._now() },
            { id: this._generateId(), username: 'kitchen', password: 'kitchen123', full_name: 'Kitchen Staff', role: 'kitchen', is_active: true, restaurant_id: flavourId, created_at: this._now(), updated_at: this._now() }
        ];
    }

    _matches(doc, filter) {
        if (!filter || Object.keys(filter).length === 0) return true;
        for (const [key, value] of Object.entries(filter)) {
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                if ('$gte' in value && doc[key] < value['$gte']) return false;
            } else {
                if (doc[key] !== value) return false;
            }
        }
        return true;
    }

    insertOne(collection, document) {
        const now = this._now();
        const doc = { id: this._generateId(), created_at: now, updated_at: now, ...document };
        if (!this.collections[collection]) this.collections[collection] = [];
        this.collections[collection].push(doc);
        return doc.id;
    }

    findOne(collection, filter = {}) {
        const col = this.collections[collection] || [];
        if (!filter || Object.keys(filter).length === 0) return col[0] || null;
        return col.find(doc => this._matches(doc, filter)) || null;
    }

    findById(collection, id) {
        return this.findOne(collection, { id });
    }

    findMany(collection, filter = {}, sortField = null, limit = null) {
        let docs = (this.collections[collection] || []).filter(doc => this._matches(doc, filter));
        if (sortField) docs = [...docs].sort((a, b) => (a[sortField] > b[sortField] ? 1 : -1));
        if (limit) docs = docs.slice(0, limit);
        return docs;
    }

    updateOne(collection, filter, update) {
        const col = this.collections[collection] || [];
        const idx = col.findIndex(doc => this._matches(doc, filter));
        if (idx === -1) return false;
        Object.assign(col[idx], update, { updated_at: this._now() });
        return true;
    }

    updateById(collection, id, update) {
        return this.updateOne(collection, { id }, update);
    }

    deleteOne(collection, filter) {
        const col = this.collections[collection] || [];
        const idx = col.findIndex(doc => this._matches(doc, filter));
        if (idx === -1) return false;
        col.splice(idx, 1);
        return true;
    }

    count(collection, filter = {}) {
        return this.findMany(collection, filter).length;
    }
}

module.exports = new Store();
