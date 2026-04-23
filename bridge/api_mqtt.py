"""API MQTT <-> Web pour l'accès aux données historiques (Étudiant 4)."""

import json
import os

import mysql.connector
import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.univ-cotedazur.fr")
MQTT_PORT = int(os.getenv("MQTT_PORT", "443"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

TOPIC_REQUETE = os.getenv("TOPIC_REQUETE", "FABLAB_21_22/WEB/REQUETE")
TOPIC_REPONSE = os.getenv("TOPIC_REPONSE", "FABLAB_21_22/WEB/REPONSE")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "fablab_user")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "fablab_monitoring")


def normalize_topic(topic):
    """Uniformise les topics pour compatibilité historique (slash multiples)."""
    if not topic:
        return ""
    normalized = str(topic)
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.rstrip("/")


def sanitize_limit(value, default=15, minimum=1, maximum=200):
    """Valide la limite demandée par le front."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def get_data_from_db(cible_topic, limit=15):
    normalized_topic = normalize_topic(cible_topic)
    limit = sanitize_limit(limit)

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT value, created_at
            FROM sensor_data
            WHERE REPLACE(REPLACE(topic, '//', '/'), '//', '/') = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        cursor.execute(sql, (normalized_topic, limit))
        rows = cursor.fetchall()
        for row in rows:
            row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        rows.reverse()  # ordre chronologique pour le front
        return rows
    except Exception as err:
        print(f"❌ Erreur MySQL : {err}")
        return []
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def publish_response(client, capteur, donnees, statut="succes", message=None):
    payload = {
        "capteur": normalize_topic(capteur),
        "donnees": donnees,
        "statut": statut,
    }
    if message:
        payload["message"] = message

    client.publish(TOPIC_REPONSE, json.dumps(payload))


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ API Web connectée. Code {rc}")
        client.subscribe(TOPIC_REQUETE)
        print(f"📡 En écoute sur {TOPIC_REQUETE}")
    else:
        print(f"❌ Erreur connexion code: {rc}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        print(f"📩 Requête reçue: {payload}")
        req = json.loads(payload)

        capteur = normalize_topic(req.get("capteur"))
        limite = sanitize_limit(req.get("limite", 15))

        if not capteur:
            publish_response(client, "", [], statut="erreur", message="Champ 'capteur' manquant")
            return

        db_results = get_data_from_db(capteur, limite)
        status = "succes" if db_results else "vide"
        publish_response(client, capteur, db_results, statut=status)

        print(f"📤 Réponse envoyée: {len(db_results)} point(s) -> {capteur}")
    except json.JSONDecodeError:
        publish_response(client, "", [], statut="erreur", message="JSON de requête invalide")
        print("❌ Requête JSON invalide")
    except Exception as err:
        publish_response(client, "", [], statut="erreur", message="Erreur interne API")
        print(f"❌ Erreur API: {err}")


if __name__ == "__main__":
    client = mqtt.Client(transport="websockets")
    client.ws_set_options(path="/ws", headers=None)
    client.tls_set()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print("🚀 Démarrage API MQTT...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt de l'API MQTT.")
    except Exception as err:
        print(f"❌ Erreur de connexion MQTT: {err}")
