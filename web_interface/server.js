const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');
const path = require('path');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.static(path.join(__dirname, 'public')));

const pool = mysql.createPool({
    host: '127.0.0.1',
    user: 'fablab_user',
    password: 'fablab_password',
    database: 'fablab_monitoring',
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