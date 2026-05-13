const { query } = require('./db');

const TABLES = {
    restaurants: 'restaurants',
    menu_items: 'menu_items',
    categories: 'categories',
    orders: 'orders',
    drivers: 'drivers',
    admin_users: 'admin_users',
    payment_transactions: 'payment_transactions',
    driver_documents: 'driver_documents',
    audit_logs: 'audit_logs'
};

function buildWhere(filter) {
    const entries = Object.entries(filter || {});
    if (entries.length === 0) return { clause: '', values: [] };
    const conditions = [];
    const values = [];
    for (const [key, val] of entries) {
        if (val !== undefined && val !== null && typeof val === 'object' && !Array.isArray(val) && '$gte' in val) {
            values.push(val['$gte']);
            conditions.push(`${key} >= $${values.length}`);
        } else {
            values.push(val);
            conditions.push(`${key} = $${values.length}`);
        }
    }
    return { clause: 'WHERE ' + conditions.join(' AND '), values };
}

function toSqlValue(val) {
    if (Array.isArray(val) || (val !== null && typeof val === 'object' && !(val instanceof Date))) {
        return JSON.stringify(val);
    }
    return val;
}

async function insertOne(collection, document) {
    const table = TABLES[collection];
    const doc = { ...document };
    delete doc.id;
    delete doc.created_at;
    delete doc.updated_at;

    const keys = Object.keys(doc);
    const values = keys.map(k => toSqlValue(doc[k]));
    const placeholders = keys.map((_, i) => `$${i + 1}`);

    const sql = `INSERT INTO ${table} (${keys.join(', ')}) VALUES (${placeholders.join(', ')}) RETURNING id`;
    const result = await query(sql, values);
    return result.rows[0].id;
}

async function findOne(collection, filter = {}) {
    const table = TABLES[collection];
    const { clause, values } = buildWhere(filter);
    const result = await query(`SELECT * FROM ${table} ${clause} LIMIT 1`, values);
    return result.rows[0] || null;
}

async function findById(collection, id) {
    return findOne(collection, { id });
}

async function findMany(collection, filter = {}, sortField = null, limit = null) {
    const table = TABLES[collection];
    const { clause, values } = buildWhere(filter);
    let sql = `SELECT * FROM ${table} ${clause}`;
    if (sortField) sql += ` ORDER BY ${sortField} ASC`;
    if (limit) sql += ` LIMIT ${parseInt(limit)}`;
    const result = await query(sql, values);
    return result.rows;
}

async function updateOne(collection, filter, update) {
    const table = TABLES[collection];
    const { clause, values: whereValues } = buildWhere(filter);
    if (!clause) return false;

    const entries = Object.entries(update || {}).filter(([k]) => k !== 'id' && k !== 'created_at');
    if (entries.length === 0) return false;

    const sets = [];
    const setValues = [];
    for (const [key, val] of entries) {
        setValues.push(toSqlValue(val));
        sets.push(`${key} = $${setValues.length}`);
    }
    sets.push(`updated_at = NOW()`);

    const offset = setValues.length;
    const adjustedWhere = clause.replace(/\$(\d+)/g, (_, n) => `$${parseInt(n) + offset}`);
    const sql = `UPDATE ${table} SET ${sets.join(', ')} ${adjustedWhere}`;
    await query(sql, [...setValues, ...whereValues]);
    return true;
}

async function updateById(collection, id, update) {
    return updateOne(collection, { id }, update);
}

async function deleteOne(collection, filter) {
    const table = TABLES[collection];
    const { clause, values } = buildWhere(filter);
    if (!clause) return false;
    await query(`DELETE FROM ${table} ${clause}`, values);
    return true;
}

async function countDocs(collection, filter = {}) {
    const table = TABLES[collection];
    const { clause, values } = buildWhere(filter);
    const result = await query(`SELECT COUNT(*) FROM ${table} ${clause}`, values);
    return parseInt(result.rows[0].count);
}

module.exports = { insertOne, findOne, findById, findMany, updateOne, updateById, deleteOne, count: countDocs };
