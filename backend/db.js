const { Pool } = require('pg');

const connectionString = process.env.DATABASE_URL;

const pool = new Pool({
    connectionString,
    ssl: connectionString && connectionString.includes('sslmode=require')
        ? { rejectUnauthorized: false }
        : false
});

pool.on('error', (err) => {
    console.error('Unexpected PostgreSQL error:', err);
});

async function query(text, params) {
    const client = await pool.connect();
    try {
        const result = await client.query(text, params);
        return result;
    } finally {
        client.release();
    }
}

module.exports = { pool, query };
