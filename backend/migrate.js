const { query } = require('./db');
const { v4: uuidv4 } = require('uuid');

async function createTables() {
    await query(`
        CREATE TABLE IF NOT EXISTS restaurants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            address TEXT,
            phone VARCHAR(50),
            logo_url TEXT,
            cover_image_url TEXT,
            is_active BOOLEAN DEFAULT true,
            is_featured BOOLEAN DEFAULT false,
            delivery_fee DECIMAL(10,2) DEFAULT 0,
            minimum_order DECIMAL(10,2) DEFAULT 0,
            estimated_delivery_time VARCHAR(100),
            rating DECIMAL(3,2) DEFAULT 4.5,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            icon VARCHAR(20),
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS menu_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            restaurant_id UUID REFERENCES restaurants(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(255),
            image_url TEXT,
            available BOOLEAN DEFAULT true,
            preparation_time INTEGER DEFAULT 15,
            ingredients JSONB DEFAULT '[]',
            allergens JSONB DEFAULT '[]',
            nutritional_info JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_number VARCHAR(50),
            customer_name VARCHAR(255),
            customer_phone VARCHAR(50),
            customer_address TEXT,
            restaurant_id UUID REFERENCES restaurants(id),
            telegram_user_id VARCHAR(100),
            items JSONB DEFAULT '[]',
            total_amount DECIMAL(10,2) DEFAULT 0,
            delivery_fee DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(50) DEFAULT 'pending',
            payment_method VARCHAR(50) DEFAULT 'cash',
            payment_status VARCHAR(50) DEFAULT 'pending',
            location_lat DECIMAL(10,8),
            location_lng DECIMAL(11,8),
            special_instructions TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS drivers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255),
            phone_number VARCHAR(50),
            telegram_user_id VARCHAR(100),
            vehicle_type VARCHAR(100) DEFAULT 'motorcycle',
            license_number VARCHAR(100),
            is_active BOOLEAN DEFAULT true,
            is_available BOOLEAN DEFAULT false,
            is_approved BOOLEAN DEFAULT false,
            current_lat DECIMAL(10,8),
            current_lng DECIMAL(11,8),
            last_location_update TIMESTAMPTZ,
            rating DECIMAL(3,2) DEFAULT 5.0,
            total_deliveries INTEGER DEFAULT 0,
            restaurant_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS admin_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            email VARCHAR(255),
            role VARCHAR(50) DEFAULT 'admin',
            restaurant_id UUID,
            is_active BOOLEAN DEFAULT true,
            last_login TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID REFERENCES orders(id),
            amount DECIMAL(10,2),
            method VARCHAR(50),
            status VARCHAR(50) DEFAULT 'pending',
            receipt_url TEXT,
            verified_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS driver_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
            doc_type VARCHAR(100) DEFAULT 'document',
            file_url TEXT,
            filename VARCHAR(255),
            uploaded_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`ALTER TABLE drivers ADD COLUMN IF NOT EXISTS rejection_reason TEXT`);
    await query(`ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT false`);
    await query(`ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)`);
    await query(`ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS telegram_user_id VARCHAR(100)`);
    await query(`ALTER TABLE orders ADD COLUMN IF NOT EXISTS driver_id UUID`);
    await query(`ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lat DECIMAL(10,8)`);
    await query(`ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS lng DECIMAL(11,8)`);
    await query(`ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS location_url TEXT`);
    await query(`ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS rating_count INTEGER DEFAULT 0`);

    await query(`
        CREATE TABLE IF NOT EXISTS restaurant_ratings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            restaurant_id UUID REFERENCES restaurants(id) ON DELETE CASCADE,
            telegram_user_id VARCHAR(100) NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(restaurant_id, telegram_user_id)
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS customer_live_locations (
            telegram_user_id VARCHAR(100) PRIMARY KEY,
            lat DECIMAL(10,8),
            lng DECIMAL(11,8),
            live_period INTEGER,
            expires_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    await query(`
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            admin_id VARCHAR(100),
            admin_username VARCHAR(100) NOT NULL,
            action VARCHAR(100) NOT NULL,
            target_type VARCHAR(50),
            target_id VARCHAR(100),
            target_name VARCHAR(255),
            details TEXT,
            ip_address VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);
    await query(`CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)`);

    // System settings table
    await query(`
        CREATE TABLE IF NOT EXISTS system_settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);
    // Default price per km if not set
    await query(`
        INSERT INTO system_settings (key, value) VALUES ('price_per_km', '10')
        ON CONFLICT (key) DO NOTHING
    `);

    // Driver fee columns on orders
    await query(`ALTER TABLE orders ADD COLUMN IF NOT EXISTS driver_fee DECIMAL(10,2) DEFAULT 0`);
    await query(`ALTER TABLE orders ADD COLUMN IF NOT EXISTS driver_distance_km DECIMAL(8,2) DEFAULT 0`);

    // Customer profiles table
    await query(`
        CREATE TABLE IF NOT EXISTS customers (
            telegram_user_id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255),
            phone_number VARCHAR(50),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    `);

    console.log('All tables created successfully');
}

async function seedData() {
    const existing = await query('SELECT COUNT(*) FROM restaurants');
    if (parseInt(existing.rows[0].count) > 0) {
        console.log('Data already seeded, skipping...');
        return;
    }

    const flavourId = uuidv4();
    const yFactoryId = uuidv4();

    await query(`
        INSERT INTO restaurants (id, name, description, address, phone, is_active, is_featured, delivery_fee, minimum_order, estimated_delivery_time, rating)
        VALUES
            ($1, 'Flavour cafe | E.Fabrica', 'Authentic Ethiopian and International Cuisine', 'Addis Ababa, Ethiopia', '+251911123456', true, true, 0, 0, '30-45 minutes', 4.5),
            ($2, 'Y Factory Restaurant', 'Modern restaurant with diverse cuisine', 'Addis Ababa, Ethiopia', '+251922334455', true, false, 0, 0, '25-40 minutes', 4.3)
    `, [flavourId, yFactoryId]);

    await query(`
        INSERT INTO categories (name, description, icon, sort_order, is_active) VALUES
            ('Burgers', 'Delicious beef and chicken burgers', '🍔', 1, true),
            ('Shawarma', 'Traditional Middle Eastern wraps', '🌯', 2, true),
            ('Pizza', 'Italian style pizzas', '🍕', 3, true),
            ('Traditional Ethiopian Breakfast', 'Authentic Ethiopian breakfast', '☕', 4, true),
            ('Drinks', 'Beverages and drinks', '🥤', 5, true)
    `);

    const menuItems = [
        ['Beef Burger Normal', 400, 'Delicious beef burger with classic toppings', 'Burgers', '/static/uploads/1751975047_images_25.jpg'],
        ['Chicken Burger Special', 540, 'Premium chicken burger with special sauce', 'Burgers', '/static/uploads/1751975080_images_26.jpg'],
        ['Cheese Burger', 450, 'Juicy burger with melted cheese', 'Burgers', '/static/uploads/1751975114_images_27.jpg'],
        ['Beef Shawarma Large', 495, 'Large beef shawarma with traditional spices', 'Shawarma', '/static/uploads/1751975388_images_28.jpg'],
        ['Chicken Shawarma Small', 430, 'Small chicken shawarma with authentic taste', 'Shawarma', '/static/uploads/1751975863_images_33.jpg'],
        ['Chicken Shawarma Large', 520, 'Large chicken shawarma with extra filling', 'Shawarma', '/static/uploads/1751975907_fried-egg-sandwich_1.webp'],
        ['Injera with Doro Wat', 350, 'Traditional Ethiopian injera with spicy chicken stew', 'Traditional Ethiopian Breakfast', '/static/uploads/1751975047_images_25.jpg'],
        ['Kitfo', 280, 'Ethiopian beef tartare', 'Traditional Ethiopian Breakfast', '/static/uploads/1751975080_images_26.jpg'],
        ['Tibs', 320, 'Ethiopian sautéed meat', 'Traditional Ethiopian Breakfast', '/static/uploads/1751975388_images_28.jpg'],
        ['Shiro Wat', 180, 'Ethiopian chickpea stew', 'Traditional Ethiopian Breakfast', '/static/uploads/1751975114_images_27.jpg'],
        ['Margherita Pizza', 450, 'Classic pizza with tomato and mozzarella', 'Pizza', '/static/uploads/1751976198_ALR-recipe-16895-fluffy-french-toast-hero-01-ddmfs-4x3-7fd61e054f2c4f0f868b7ab0dd8767ae.jpg'],
        ['Pepperoni Pizza', 520, 'Pizza with pepperoni and cheese', 'Pizza', '/static/uploads/1751976242_images_35.jpg'],
        ['Ethiopian Coffee', 80, 'Traditional Ethiopian coffee', 'Drinks', '/static/uploads/1751975047_images_25.jpg'],
        ['Fresh Juice', 120, 'Freshly squeezed fruit juice', 'Drinks', '/static/uploads/1751975080_images_26.jpg'],
        ['Soft Drink', 60, 'Carbonated soft drink', 'Drinks', '/static/uploads/1751975114_images_27.jpg']
    ];

    for (const [name, price, desc, cat, img] of menuItems) {
        await query(
            `INSERT INTO menu_items (restaurant_id, name, price, description, category, image_url, available, preparation_time)
             VALUES ($1, $2, $3, $4, $5, $6, true, 15)`,
            [flavourId, name, price, desc, cat, img]
        );
    }

    await query(`
        INSERT INTO admin_users (username, password, full_name, role, restaurant_id, is_active) VALUES
            ('admin', 'admin123', 'Admin User', 'admin', $1, true),
            ('superadmin', 'superadmin123', 'Super Administrator', 'superadmin', NULL, true),
            ('kitchen', 'kitchen123', 'Kitchen Staff', 'kitchen', $1, true)
    `, [flavourId]);

    console.log('Seed data inserted successfully');
}

async function runMigration() {
    try {
        console.log('Running database migration...');
        await createTables();
        await seedData();
        console.log('Migration complete');
    } catch (err) {
        console.error('Migration error:', err.message);
        throw err;
    }
}

module.exports = { runMigration };
