import paho.mqtt.client as mqtt
import mysql.connector
from datetime import datetime
import json

# ==========================================
# CONFIGURATION
# ==========================================
MQTT_BROKER = "127.0.0.1" # Mettre l'IP du Raspberry Pi du FabLab plus tard
MQTT_PORT = 1883
MQTT_TOPIC = "FABLAB_21_22/#" # Le # permet de s'abonner à tous les sous-topics

# Configuration de la base de données locale
DB_HOST = "127.0.0.1"
DB_USER = "fablab_user"
DB_PASS = "fablab_password"
DB_NAME = "fablab_monitoring"

# ==========================================
# FONCTIONS MQTT
# ==========================================
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté au broker MQTT avec le code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Écoute sur le topic : {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    
    print(f"🔔 Message reçu sur [{topic}] : {payload}")
    
    # Ici, nous ajouterons plus tard le code pour insérer la donnée dans MySQL
    # save_to_db(topic, payload)

# ==========================================
# INITIALISATION
# ==========================================
if __name__ == "__main__":
    print("🚀 Démarrage du Bridge MQTT -> MySQL...")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever() # Garde le script en vie pour écouter en continu
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bridge.")
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
