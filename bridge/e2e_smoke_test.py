"""Smoke test E2E: MQTT -> MySQL -> API MQTT.

Pré-requis:
- MySQL démarré (docker compose up -d)
- bridge/main.py lancé
- bridge/api_mqtt.py lancé
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time

import mysql.connector
import paho.mqtt.client as mqtt


MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.univ-cotedazur.fr")
MQTT_PORT = int(os.getenv("MQTT_PORT", "443"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")

TOPIC_REQUETE = os.getenv("TOPIC_REQUETE", "FABLAB_21_22/WEB/REQUETE")
TOPIC_REPONSE = os.getenv("TOPIC_REPONSE", "FABLAB_21_22/WEB/REPONSE")
TEST_TOPIC_ROOT = os.getenv("TEST_TOPIC_ROOT", "FABLAB_21_22/e2e")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_USER = os.getenv("DB_USER", "fablab_user")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "fablab_monitoring")


class E2ESmokeState:
    def __init__(self, expected_capteur: str):
        self.expected_capteur = expected_capteur
        self.response_event = threading.Event()
        self.response_payload: dict | None = None


def _normalize_topic(topic: str) -> str:
    normalized = str(topic)
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized.rstrip("/")


def _build_mqtt_client(state: E2ESmokeState) -> mqtt.Client:
    client = mqtt.Client(transport="websockets")
    client.ws_set_options(path="/ws", headers=None)
    client.tls_set()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(c, userdata, flags, rc):
        if rc != 0:
            print(f"❌ Connexion MQTT échouée rc={rc}")
            return
        print(f"✅ Connexion MQTT OK rc={rc}")
        c.subscribe(TOPIC_REPONSE)
        print(f"📡 Subscribe: {TOPIC_REPONSE}")

    def on_message(c, userdata, msg):
        if msg.topic != TOPIC_REPONSE:
            return
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return

        capteur = _normalize_topic(payload.get("capteur", ""))
        if capteur != _normalize_topic(state.expected_capteur):
            return

        state.response_payload = payload
        state.response_event.set()

    client.on_connect = on_connect
    client.on_message = on_message
    return client


def _wait_db_insert(topic: str, timeout_s: int = 20) -> bool:
    deadline = time.time() + timeout_s
    sql = "SELECT value, created_at FROM sensor_data WHERE topic = %s ORDER BY created_at DESC LIMIT 1"

    while time.time() < deadline:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                database=DB_NAME,
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (topic,))
            row = cursor.fetchone()
            if row is not None:
                print(f"✅ Insert DB détecté: topic={topic}, value={row['value']}")
                return True
        except Exception as err:
            print(f"⏳ DB pas prête ({err}), retry...")
        finally:
            if "conn" in locals() and conn.is_connected():
                cursor.close()
                conn.close()
        time.sleep(1)

    print("❌ Aucun insert DB détecté dans le délai")
    return False


def main() -> int:
    timestamp = int(time.time())
    test_topic = f"{TEST_TOPIC_ROOT}/temp/{timestamp}"
    test_value = 23.5

    print("=== E2E SMOKE TEST (Étudiant 4) ===")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Topic test: {test_topic}")

    state = E2ESmokeState(expected_capteur=test_topic)
    client = _build_mqtt_client(state)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(1.5)

        # Etape 1: publier une valeur capteur pour main.py
        sensor_msg = mqtt.MQTTMessage()
        sensor_msg.payload = str(test_value).encode("utf-8")
        sensor_msg.topic = test_topic.encode("utf-8")
        client.publish(test_topic, str(test_value))
        print(f"📤 Publish capteur: {test_topic} => {test_value}")

        # Etape 2: vérifier insert DB
        if not _wait_db_insert(test_topic):
            return 2

        # Etape 3: requête API MQTT
        request_payload = json.dumps({"capteur": test_topic, "limite": 1})
        client.publish(TOPIC_REQUETE, request_payload)
        print(f"📤 Publish requête API: {TOPIC_REQUETE} => {request_payload}")

        if not state.response_event.wait(timeout=10):
            print("❌ Pas de réponse API MQTT reçue")
            return 3

        response = state.response_payload or {}
        statut = response.get("statut")
        donnees = response.get("donnees", [])
        print(f"📩 Réponse API reçue: statut={statut}, points={len(donnees)}")

        if statut not in {"succes", "vide"}:
            print(f"❌ Statut API inattendu: {statut}")
            return 4

        if not donnees:
            print("❌ Réponse API vide alors qu'un insert DB est attendu")
            return 5

        print("🎉 E2E OK: MQTT -> MySQL -> API MQTT validé")
        return 0

    except Exception as err:
        print(f"❌ Erreur smoke test: {err}")
        return 1
    finally:
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
