const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.static(path.join(__dirname, 'public')));

const DB_HOST = process.env.DB_HOST || '127.0.0.1';
const DB_USER = process.env.DB_USER || 'fablab_user';
const DB_PASS = process.env.DB_PASS || process.env.MYSQL_PASSWORD || '';
const DB_NAME = process.env.DB_NAME || process.env.MYSQL_DATABASE || 'fablab_monitoring';

const pool = mysql.createPool({
    host: DB_HOST,
    user: DB_USER,
    password: DB_PASS,
    database: DB_NAME,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

// API: retourne les 50 dernières mesures
app.get('/api/mesures', async (req, res) => {
    try {
        const [rows] = await pool.query(
            'SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT 50'
        );
        res.json(rows);

    } catch (error) {
        console.error('Erreur base de données:', error);
        res.status(500).json({ error: 'Impossible de récupérer les données' });
    }
});

app.listen(PORT, () => {
    console.log(`🌐 Serveur Web (API) démarré sur http://localhost:${PORT}`);
});