"""Bridge MQTT -> MySQL (Étudiant 4).

Rôle:
- écouter les topics MQTT du projet,
- extraire les valeurs numériques utiles,
- stocker en base avec un throttling par topic.
"""

import json
import os
import re
import time

import mysql.connector
import paho.mqtt.client as mqtt

# MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.univ-cotedazur.fr")
MQTT_PORT = int(os.getenv("MQTT_PORT", "443"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "FABLAB_21_22/#")

# MySQL
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "fablab_user")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "fablab_monitoring")

# Throttling par topic
SAVE_INTERVAL_SECONDS = max(0, int(os.getenv("SAVE_INTERVAL_SECONDS", "60")))
last_saved_time = {}
MAX_TEXT_PAYLOAD = max(1000, int(os.getenv("MAX_TEXT_PAYLOAD", "1000000")))
CAMERA_KEYWORDS = ("camera", "cam", "infra", "ir", "image", "frame")


def ensure_db_schema():
    """Crée la table `sensor_data` si elle n'existe pas."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_data (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                topic VARCHAR(255) NOT NULL,
                value DOUBLE NULL,
                value_text LONGTEXT NULL,
                value_type VARCHAR(12) DEFAULT 'num',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_topic_created_at (topic, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute("SHOW COLUMNS FROM sensor_data LIKE 'value_text'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sensor_data ADD COLUMN value_text LONGTEXT NULL")

        cursor.execute("SHOW COLUMNS FROM sensor_data LIKE 'value_type'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sensor_data ADD COLUMN value_type VARCHAR(12) DEFAULT 'num'")

        cursor.execute("ALTER TABLE sensor_data MODIFY value DOUBLE NULL")
        conn.commit()
        print("🧱 Schéma DB prêt (table sensor_data).")
    except mysql.connector.Error as err:
        print(f"❌ Erreur init schéma MySQL : {err}")
        raise
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté au broker MQTT avec le code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Écoute sur le topic : {MQTT_TOPIC}")


def normalize_key(key):
    """Normalise une clé de payload en suffixe de topic stable."""
    clean = key.strip().lower().replace("°", "deg")
    clean = re.sub(r"\s+", "_", clean)
    clean = re.sub(r"[^a-z0-9_]+", "", clean)
    return clean or "field"


def build_sub_topic(base_topic, key):
    """Construit un sous-topic sans slash en double."""
    return f"{base_topic.rstrip('/')}/{normalize_key(key)}"


def is_camera_topic(topic, key=None):
    target = f"{topic}/{key or ''}".lower()
    return any(keyword in target for keyword in CAMERA_KEYWORDS)


def extract_numeric_pairs_from_broken_payload(payload):
    """Récupère des paires numériques depuis un pseudo-JSON cassé."""
    pairs = {}
    for key, raw_value in re.findall(r'"([^"]+)"\s*:\s*([^,}\{]*)', payload):
        value = raw_value.strip().strip('"')
        if value == "":
            continue

        lowered = value.lower()
        if lowered in ("true", "false"):
            pairs[key] = 1.0 if lowered == "true" else 0.0
            continue

        try:
            pairs[key] = float(value)
        except ValueError:
            continue

    return pairs


def flatten_numeric_points(topic, data):
    """Extrait les valeurs numériques d'un dict JSON (niveau 1 + sous-objets numériques)."""
    numeric_points = []

    for key, value in data.items():
        if key in {"ts", "timestamp_ms"}:
            continue

        if isinstance(value, dict):
            # Compatibilité capteurs qui publient des objets (ex: stats.avg, radar.c1.x)
            for child_key, child_value in value.items():
                if isinstance(child_value, (int, float, bool)) and not isinstance(child_value, str):
                    numeric_points.append((build_sub_topic(topic, f"{key}_{child_key}"), float(child_value)))
            continue

        if isinstance(value, (int, float, bool)) and not isinstance(value, str):
            numeric_points.append((build_sub_topic(topic, key), float(value)))

    return numeric_points


def extract_numeric_points(topic, payload):
    """Retourne une liste [(topic, value)] à partir d'un payload MQTT."""
    # 1) valeur brute
    try:
        return [(topic, float(payload))], "raw"
    except ValueError:
        pass

    # 2) JSON valide
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            points = flatten_numeric_points(topic, data)
            return points, "json"
        return [], "json-non-dict"
    except json.JSONDecodeError:
        pass

    # 3) JSON cassé mais récupérable
    recovered = extract_numeric_pairs_from_broken_payload(payload)
    if recovered:
        points = [(build_sub_topic(topic, key), value) for key, value in recovered.items()]
        return points, "broken-json"

    return [], "unusable"


def extract_text_points(topic, payload):
    """Extrait des payloads texte (base64, image) pour les topics caméra."""
    if not is_camera_topic(topic):
        return []

    points = []

    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and is_camera_topic(topic, key):
                    cleaned = value.strip()
                    if cleaned:
                        points.append((build_sub_topic(topic, key), cleaned))
            if points:
                return points
    except json.JSONDecodeError:
        pass

    raw = str(payload or "").strip()
    if raw:
        points.append((topic, raw))

    return points


def save_numeric_to_db(topic, value):
    """Insère une valeur numérique en DB si le throttle du topic est écoulé."""
    current_time = time.time()
    last_saved_time.setdefault(topic, 0)

    elapsed = current_time - last_saved_time[topic]
    if elapsed < SAVE_INTERVAL_SECONDS:
        print(f"⏳ Ignoré (throttle): {topic}, dernier insert il y a {int(elapsed)}s")
        return

    try:
        float_value = float(value)
    except (ValueError, TypeError):
        print(f"⚠️ Ignoré (non numérique): topic={topic}, value={value}")
        return

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_data (topic, value, value_text, value_type) VALUES (%s, %s, %s, 'num')",
            (topic, float_value, None),
        )
        conn.commit()
        last_saved_time[topic] = current_time
        print(f"💾 Sauvé: {topic} = {float_value}")
    except mysql.connector.Error as err:
        print(f"❌ Erreur MySQL : {err}")
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def save_text_to_db(topic, value):
    """Insère un payload texte en DB si le throttle du topic est écoulé."""
    text_key = f"{topic}|text"
    current_time = time.time()
    last_saved_time.setdefault(text_key, 0)

    elapsed = current_time - last_saved_time[text_key]
    if elapsed < SAVE_INTERVAL_SECONDS:
        print(f"⏳ Ignoré (throttle texte): {topic}, dernier insert il y a {int(elapsed)}s")
        return

    text_value = str(value or "").strip()
    if not text_value:
        print(f"⚠️ Ignoré (texte vide): topic={topic}")
        return

    if len(text_value) > MAX_TEXT_PAYLOAD:
        text_value = text_value[:MAX_TEXT_PAYLOAD]
        print(f"✂️ Payload texte tronqué à {MAX_TEXT_PAYLOAD} caractères: {topic}")

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sensor_data (topic, value, value_text, value_type) VALUES (%s, %s, %s, 'text')",
            (topic, None, text_value),
        )
        conn.commit()
        last_saved_time[text_key] = current_time
        print(f"🖼️ Sauvé (texte): {topic} ({len(text_value)} chars)")
    except mysql.connector.Error as err:
        print(f"❌ Erreur MySQL texte : {err}")
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        print(f"🔔 Message MQTT [{topic}] : {payload}")

        points, mode = extract_numeric_points(topic, payload)
        text_points = extract_text_points(topic, payload)

        if mode == "broken-json" and points:
            print(f"🛠️ JSON cassé récupéré partiellement sur [{topic}] ({len(points)} champs numériques).")
        elif mode == "json":
            print(f"✅ JSON détecté sur {topic}. Champs numériques extraits: {len(points)}")
        elif mode == "raw":
            print(f"✅ Valeur numérique brute détectée sur {topic}")

        if not points and not text_points:
            print(f"⚠️ Ignoré (inexploitable): topic={topic}")
            return

        for sub_topic, value in points:
            save_numeric_to_db(sub_topic, value)

        for sub_topic, value in text_points:
            save_text_to_db(sub_topic, value)

    except Exception as err:
        print(f"❌ Erreur inattendue sur {msg.topic}: {err}")


if __name__ == "__main__":
    print("🚀 Démarrage du bridge MQTT -> MySQL...")

    ensure_db_schema()

    client = mqtt.Client(transport="websockets")
    client.ws_set_options(path="/ws", headers=None)
    client.tls_set()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"🔗 Connexion à {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bridge.")
    except Exception as err:
        print(f"❌ Erreur de connexion : {err}")
