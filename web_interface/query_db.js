const mysql = require('mysql2/promise');
require('dotenv').config({ path: '../.env' });
async function run() {
  try {
    const pool = mysql.createPool({ host: '127.0.0.1', user: process.env.DB_USER || 'fablab_user', password: process.env.DB_PASS || process.env.MYSQL_PASSWORD || '', database: process.env.DB_NAME || process.env.MYSQL_DATABASE || 'fablab_monitoring' });
    const [rows] = await pool.query('SELECT topic, COUNT(*) as count FROM sensor_data GROUP BY topic ORDER BY count DESC LIMIT 20;');
    console.log(rows);
    process.exit(0);
  } catch (e) { console.error(e); process.exit(1); }
}
run();
