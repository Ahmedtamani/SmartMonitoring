const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');
const mqtt = require('mqtt');
const crypto = require('crypto');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const app = express();
const PORT = Number(process.env.WEB_PORT || 3000);

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

const DB_HOST = process.env.DB_HOST || '127.0.0.1';
const DB_USER = process.env.DB_USER || 'fablab_user';
const DB_PASS = process.env.DB_PASS || process.env.MYSQL_PASSWORD || '';
const DB_NAME = process.env.DB_NAME || process.env.MYSQL_DATABASE || 'fablab_monitoring';

const MQTT_BROKER = process.env.MQTT_BROKER || 'mqtt.univ-cotedazur.fr';
const MQTT_PORT = Number(process.env.MQTT_PORT || 443);
const MQTT_USER = process.env.MQTT_USER || '';
const MQTT_PASS = process.env.MQTT_PASS || '';
const MQTT_COMMAND_DEFAULT_TOPIC = process.env.MQTT_COMMAND_TOPIC || 'FABLAB_21_22/CMD/default';

const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'admin123';
const ADMIN_TOKEN_TTL_MS = Number(process.env.ADMIN_TOKEN_TTL_MS || 8 * 60 * 60 * 1000);

const pool = mysql.createPool({
    host: DB_HOST,
    user: DB_USER,
    password: DB_PASS,
    database: DB_NAME,
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
});

const adminSessions = new Map();
const commandLogs = [];

const mqttOptions = {
    protocol: 'wss',
    host: MQTT_BROKER,
    port: MQTT_PORT,
    path: '/ws',
    reconnectPeriod: 2000,
};

if (MQTT_USER) {
    mqttOptions.username = MQTT_USER;
    mqttOptions.password = MQTT_PASS;
}

const mqttClient = mqtt.connect(mqttOptions);

mqttClient.on('connect', () => {
    console.log(`✅ MQTT connecté (${MQTT_BROKER}:${MQTT_PORT})`);
    mqttClient.subscribe('FABLAB_21_22/camera/#');
});

mqttClient.on('reconnect', () => {
    console.log('🔄 MQTT reconnexion en cours...');
});

mqttClient.on('error', (err) => {
    console.error('❌ MQTT erreur:', err.message);
});

// ── Stockage temps réel caméra ──────────────────────────────
let cameraData = {
    occupancy: null,
    in: null,
    out: null,
    fps: null,
    updated_at: null
};
let cameraLiveFrame = null;

mqttClient.on('message', (topic, payload) => {
    try {
        const msg = JSON.parse(payload.toString());
        if (topic.includes('camera') && topic.includes('comptage')) {
            if (msg.type === 'summary' || msg.type === 'event') {
                cameraData.occupancy  = msg.occupancy  ?? cameraData.occupancy;
                cameraData.in         = msg.in         ?? cameraData.in;
                cameraData.out        = msg.out        ?? cameraData.out;
                cameraData.fps        = msg.fps        ?? cameraData.fps;
                cameraData.updated_at = new Date().toISOString();
                console.log('📷 Camera update:', cameraData);
            }
        }
        if (topic.includes('camera') && topic.includes('live')) {
            cameraLiveFrame = {
                frame: msg.frame || payload.toString(),
                ts: new Date().toISOString()
            };
        }
    } catch (e) {}
});

// ── Helpers ──────────────────────────────────────────────────
function normalizeTopic(topic) {
    return String(topic || '').replace(/\/+/g, '/').toLowerCase().replace(/\/$/, '');
}

function parseNumeric(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
}

function computeAirQualityScore(pm25, pm10) {
    const p25 = parseNumeric(pm25);
    const p10 = parseNumeric(pm10);
    if (p25 === null && p10 === null) return null;
    if (p25 !== null && p10 === null) return Math.max(0, Math.min(500, Math.round(p25 * 2.0)));
    if (p25 === null && p10 !== null) return Math.max(0, Math.min(500, Math.round(p10 * 0.8)));
    const score = (p25 * 2.0) * 0.7 + (p10 * 0.8) * 0.3;
    return Math.max(0, Math.min(500, Math.round(score)));
}

const TOPIC_PATTERNS = {
    salle1: {
        temperature: ['%fablab_21_22/envir/salle_104/temperature%'],
        humidite:    ['%fablab_21_22/envir/salle_104/humidite%'],
        lumiere:     ['%fablab_21_22/envir/salle_104/lux%', '%fablab_21_22/environ/salle_104/lux%'],
        pm25:        ['%fablab_21_22/envir/salle_104/pm25%'],
        pm10:        ['%fablab_21_22/envir/salle_104/pm10%'],
        cameraIa:    []
    },
    salle2: {
        temperature: ['%fablab_21_22/salle12/all/temperature%'],
        humidite:    ['%fablab_21_22/salle12/all/humidite%'],
        lumiere:     ['%fablab_21_22/salle12/all/lux%'],
        pm25:        ['%fablab_21_22/salle12/all/pm25%'],
        pm10:        ['%fablab_21_22/salle12/all/pm10%'],
        co2:         [],
        air:         [],
        radarNb:       ['%fablab_21_22/radar/salle104/nb%'],
        radarPresence: ['%fablab_21_22/radar/salle104/presence%'],
        radarDist:     ['%fablab_21_22/radar/salle104/c1_dist_cm%'],
        radarSpeed:    ['%fablab_21_22/radar/salle104/c1_vitesse%'],
        cameraInfra: []
    }
};

function classifyAirQuality(score) {
    const s = parseNumeric(score);
    if (s === null) return 'indisponible';
    if (s <= 50)  return 'excellent';
    if (s <= 100) return 'bon';
    if (s <= 150) return 'moyen';
    if (s <= 200) return 'degrade';
    return 'critique';
}

async function fetchLatestMetricByPatterns(patterns) {
    if (!patterns || patterns.length === 0) return null;
    try {
        const sql = `
            SELECT topic, value, created_at
            FROM sensor_data
            WHERE value IS NOT NULL
              AND (${patterns.map(() => 'LOWER(topic) LIKE ?').join(' OR ')})
            ORDER BY created_at DESC
            LIMIT 1
        `;
        const [rows] = await pool.query(sql, patterns.map(p => p.toLowerCase()));
        return rows[0] || null;
    } catch (error) {
        console.warn('⚠️ Metric query fallback:', error.code || error.message);
        return null;
    }
}

async function fetchLatestTextByPatterns(patterns) {
    if (!patterns || patterns.length === 0) return null;
    try {
        const sql = `
            SELECT topic, value_text AS value, created_at
            FROM sensor_data
            WHERE value_text IS NOT NULL
              AND (${patterns.map(() => 'LOWER(topic) LIKE ?').join(' OR ')})
            ORDER BY created_at DESC
            LIMIT 1
        `;
        const [rows] = await pool.query(sql, patterns.map(p => p.toLowerCase()));
        return rows[0] || null;
    } catch (error) {
        console.warn('⚠️ Metric texte fallback:', error.code || error.message);
        return null;
    }
}

async function fetchHistoryByPatterns(patterns, hours = 24, limit = 120) {
    if (!patterns || patterns.length === 0) return [];
    try {
        const since = new Date(Date.now() - hours * 60 * 60 * 1000);
        const sql = `
            SELECT value, created_at
            FROM sensor_data
            WHERE value IS NOT NULL
              AND created_at >= ?
              AND (${patterns.map(() => 'LOWER(topic) LIKE ?').join(' OR ')})
            ORDER BY created_at DESC
            LIMIT ?
        `;
        const values = [since, ...patterns.map(p => p.toLowerCase()), Number(limit)];
        const [rows] = await pool.query(sql, values);
        return rows.reverse().map(row => ({ t: row.created_at, v: parseNumeric(row.value) }));
    } catch (error) {
        console.warn('⚠️ History query fallback:', error.code || error.message);
        return [];
    }
}

async function buildOverviewData() {
    const metrics = {
        salle1: {
            temperature: await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle1.temperature),
            humidite:    await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle1.humidite),
            lumiere:     await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle1.lumiere),
            cameraIa:    await fetchLatestTextByPatterns(TOPIC_PATTERNS.salle1.cameraIa)
        },
        salle2: {
            temperature: await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.temperature),
            humidite:    await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.humidite),
            lumiere:     await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.lumiere),
            co2:         await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.co2),
            air:         await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.air),
            pm25:        await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.pm25),
            pm10:        await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.pm10),
            radarNb:     await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.radarNb),
            radarDist:   await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.radarDist),
            radarSpeed:  await fetchLatestMetricByPatterns(TOPIC_PATTERNS.salle2.radarSpeed),
            cameraInfra: await fetchLatestTextByPatterns(TOPIC_PATTERNS.salle2.cameraInfra)
        }
    };

    const airValue    = parseNumeric(metrics.salle2.air?.value);
    const pm25        = parseNumeric(metrics.salle2.pm25?.value);
    const pm10        = parseNumeric(metrics.salle2.pm10?.value);
    const computedAir = computeAirQualityScore(pm25, pm10);
    const airScore    = airValue ?? computedAir;

    const publicData = {
        generated_at: new Date().toISOString(),
        salle1: {
            temperature: parseNumeric(metrics.salle1.temperature?.value),
            humidite:    parseNumeric(metrics.salle1.humidite?.value),
            lumiere:     parseNumeric(metrics.salle1.lumiere?.value),
            camera: {
                occupancy:  cameraData.occupancy,
                in:         cameraData.in,
                out:        cameraData.out,
                updated_at: cameraData.updated_at
            },
            updated_at: metrics.salle1.temperature?.created_at || metrics.salle1.humidite?.created_at || null
        },
        salle2: {
            temperature:       parseNumeric(metrics.salle2.temperature?.value),
            humidite:          parseNumeric(metrics.salle2.humidite?.value),
            lumiere:           parseNumeric(metrics.salle2.lumiere?.value),
            co2:               parseNumeric(metrics.salle2.co2?.value),
            qualite_air_score: airScore,
            qualite_air_label: classifyAirQuality(airScore),
            updated_at: metrics.salle2.temperature?.created_at || metrics.salle2.humidite?.created_at || null
        }
    };

    const adminData = {
        ...publicData,
        salle1: {
            ...publicData.salle1,
            camera_ia:    metrics.salle1.cameraIa?.value ?? null,
            camera_topic: metrics.salle1.cameraIa?.topic ?? null
        },
        salle2: {
            ...publicData.salle2,
            radar: {
                nb:          parseNumeric(metrics.salle2.radarNb?.value),
                distance_cm: parseNumeric(metrics.salle2.radarDist?.value),
                vitesse_ms:  parseNumeric(metrics.salle2.radarSpeed?.value)
            },
            camera_infra:       metrics.salle2.cameraInfra?.value ?? null,
            camera_infra_topic: metrics.salle2.cameraInfra?.topic ?? null
        }
    };

    return { publicData, adminData };
}

function generateAdminToken() {
    return crypto.randomBytes(24).toString('hex');
}

function authAdmin(req, res, next) {
    const header = req.headers.authorization || '';
    const token  = header.startsWith('Bearer ') ? header.slice(7) : null;
    if (!token) return res.status(401).json({ error: 'Token admin manquant' });
    const session = adminSessions.get(token);
    if (!session || Date.now() > session.expiresAt) {
        adminSessions.delete(token);
        return res.status(401).json({ error: 'Session admin expirée ou invalide' });
    }
    req.adminUser = session.username;
    return next();
}

// ── Endpoints publics ────────────────────────────────────────

app.get('/api/mesures', async (req, res) => {
    try {
        const [rows] = await pool.query('SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT 50');
        res.json(rows);
    } catch (error) {
        res.status(500).json({ error: 'Impossible de récupérer les données' });
    }
});

app.get('/api/public/overview', async (req, res) => {
    try {
        const topics = [
            'FABLAB_21_22/envir/salle_104/temperature',
            'FABLAB_21_22/envir/salle_104/humidite',
            'FABLAB_21_22/envir/salle_104/lux',
            'FABLAB_21_22/envir/salle_104/pm25',
            'FABLAB_21_22/envir/salle_104/pm10',
            'FABLAB_21_22/salle12/all/temperature',
            'FABLAB_21_22/salle12/all/humidite',
            'FABLAB_21_22/salle12/all/lux',
            'FABLAB_21_22/salle12/all/pm25',
            'FABLAB_21_22/salle12/all/pm10',
            'FABLAB_21_22/RADAR/salle104/nb',
            'FABLAB_21_22/RADAR/salle104/presence',
            'FABLAB_21_22/RADAR/salle104/c1_dist_cm',
            'FABLAB_21_22/RADAR/salle104/c1_vitesse'
        ];

        const [rows] = await pool.query(
            `SELECT topic, value, created_at
             FROM sensor_data
             WHERE topic IN (?)
             AND value IS NOT NULL
             ORDER BY created_at DESC`,
            [topics]
        );

        const latest = {};
        for (const row of rows) {
            if (!latest[row.topic]) latest[row.topic] = row.value;
        }

        const pm25_s2 = latest['FABLAB_21_22/salle12/all/pm25'];
        const pm10_s2 = latest['FABLAB_21_22/salle12/all/pm10'];

        res.json({
            generated_at: new Date().toISOString(),
            salle1: {
                temperature: latest['FABLAB_21_22/envir/salle_104/temperature'] || null,
                humidite:    latest['FABLAB_21_22/envir/salle_104/humidite']    || null,
                lumiere:     latest['FABLAB_21_22/envir/salle_104/lux']         || null,
                pm25:        latest['FABLAB_21_22/envir/salle_104/pm25']        || null,
                pm10:        latest['FABLAB_21_22/envir/salle_104/pm10']        || null,
                camera: {
                    occupancy:  cameraData.occupancy,
                    in:         cameraData.in,
                    out:        cameraData.out,
                    updated_at: cameraData.updated_at
                }
            },
            salle2: {
                temperature:       latest['FABLAB_21_22/salle12/all/temperature'] || null,
                humidite:          latest['FABLAB_21_22/salle12/all/humidite']    || null,
                lumiere:           latest['FABLAB_21_22/salle12/all/lux']         || null,
                pm25:              pm25_s2 || null,
                pm10:              pm10_s2 || null,
                co2: latest['FABLAB_21_22/salle12/all/pm25'] || null,                
                qualite_air_score: pm25_s2 ? Math.min(500, Math.round(pm25_s2 * 2.0)) : null,
                qualite_air_label: pm25_s2 ? (pm25_s2 < 12 ? 'Bon' : pm25_s2 < 35 ? 'Modéré' : 'Mauvais') : null,
                radar: {
                    nb:                latest['FABLAB_21_22/RADAR/salle104/nb'] ?? null,
                    presence:          latest['FABLAB_21_22/RADAR/salle104/presence'] ?? null,
                    distance_cm:      latest['FABLAB_21_22/RADAR/salle104/c1_dist_cm'] ?? null,
                    vitesse_ms:       latest['FABLAB_21_22/RADAR/salle104/c1_vitesse'] ?? null
                }
            }
        });
    } catch (err) {
        console.error('overview error:', err.message);
        res.status(500).json({ error: err.message });
    }
});

app.get('/api/public/history', async (req, res) => {
    try {
        const room  = String(req.query.room || 'overview').toLowerCase();
        const hours = Math.min(48, Math.max(1, Number(req.query.hours || 24)));
        const limit = Math.min(240, Math.max(20, Number(req.query.limit || 120)));

        if (room === 'salle1') {
    const [temperature, humidite, lumiere, pm25, pm10] = await Promise.all([
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.temperature, hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.humidite,    hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.lumiere,     hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.pm25,        hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.pm10,        hours, limit)
    ]);
    return res.json({ room: 'salle1', hours, series: { temperature, humidite, lumiere, pm25, pm10 } });
}

        if (room === 'salle2') {
    const [temperature, humidite, lumiere, pm25, pm10] = await Promise.all([
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.temperature, hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.humidite,    hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.lumiere,     hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.pm25,        hours, limit),
        fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.pm10,        hours, limit)
    ]);
    return res.json({ room: 'salle2', hours, series: { temperature, humidite, lumiere, pm25, pm10 } });
}

        const [salle1Temp, salle2Temp] = await Promise.all([
            fetchHistoryByPatterns(TOPIC_PATTERNS.salle1.temperature, hours, limit),
            fetchHistoryByPatterns(TOPIC_PATTERNS.salle2.temperature, hours, limit)
        ]);
        return res.json({
            room: 'overview', hours,
            series: { salle1Temperature: salle1Temp, salle2Temperature: salle2Temp }
        });
    } catch (error) {
        console.error('Erreur history public:', error);
        res.status(500).json({ error: 'Impossible de recuperer l historique public' });
    }
});

// ── Endpoints admin ──────────────────────────────────────────

app.post('/api/admin/login', (req, res) => {
    const { username, password } = req.body || {};
    if (username !== ADMIN_USER || password !== ADMIN_PASS) {
        return res.status(401).json({ error: 'Identifiants invalides' });
    }
    const token = generateAdminToken();
    adminSessions.set(token, {
        username,
        createdAt: Date.now(),
        expiresAt: Date.now() + ADMIN_TOKEN_TTL_MS
    });
    return res.json({ token, expires_in_ms: ADMIN_TOKEN_TTL_MS });
});

app.post('/api/admin/logout', authAdmin, (req, res) => {
    const header = req.headers.authorization || '';
    const token  = header.startsWith('Bearer ') ? header.slice(7) : null;
    if (token) adminSessions.delete(token);
    return res.json({ ok: true });
});

app.get('/api/admin/overview', authAdmin, async (req, res) => {
    try {
        const { adminData } = await buildOverviewData();
        res.json(adminData);
    } catch (error) {
        console.error('Erreur overview admin:', error);
        res.status(500).json({ error: 'Impossible de recuperer les metriques admin' });
    }
});

app.get('/api/admin/camera/live', authAdmin, (req, res) => {
    if (!cameraLiveFrame) {
        return res.status(404).json({ error: 'Aucune frame disponible' });
    }
    res.json(cameraLiveFrame);
});

app.get('/api/admin/commands', authAdmin, (req, res) => {
    res.json({ total: commandLogs.length, items: commandLogs.slice(-50).reverse() });
});

app.post('/api/admin/command', authAdmin, (req, res) => {
    const { topic, payload } = req.body || {};
    const publishTopic   = String(topic || MQTT_COMMAND_DEFAULT_TOPIC).trim();
    const publishPayload = typeof payload === 'string' ? payload : JSON.stringify(payload ?? {});

    if (!publishTopic) return res.status(400).json({ error: 'Topic MQTT requis' });
    if (!mqttClient.connected) return res.status(503).json({ error: 'Broker MQTT non connecte' });

    mqttClient.publish(publishTopic, publishPayload, { qos: 0 }, (err) => {
        if (err) return res.status(500).json({ error: 'Echec publication MQTT' });
        commandLogs.push({ at: new Date().toISOString(), by: req.adminUser, topic: publishTopic, payload: publishPayload });
        if (commandLogs.length > 500) commandLogs.shift();
        return res.json({ ok: true, topic: publishTopic, payload: publishPayload });
    });
});

app.listen(PORT, () => {
    console.log(`🌐 Serveur Web (public + admin) démarré sur http://localhost:${PORT}`);
});