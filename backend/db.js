const { Pool } = require('pg');

const connectionConfig = process.env.DATABASE_URL
    ? { connectionString: process.env.DATABASE_URL, ssl: process.env.DATABASE_URL.includes('sslmode=require') ? { rejectUnauthorized: false } : false }
    : { host: process.env.PGHOST, port: process.env.PGPORT, user: process.env.PGUSER, password: process.env.PGPASSWORD, database: process.env.PGDATABASE };

const pool = new Pool(connectionConfig);

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
