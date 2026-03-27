import paho.mqtt.client as mqtt
import mysql.connector
from datetime import datetime
import json
import time

# ==========================================
# CONFIGURATION
# ==========================================
# Configuration du serveur MQTT de l'Université
MQTT_BROKER = "mqtt.univ-cotedazur.fr" 
MQTT_PORT = 443
MQTT_USER = "fablab2122"
MQTT_PASS = "2122"
MQTT_TOPIC = "FABLAB_21_22/#"

# Configuration de la base de données locale
DB_HOST = "127.0.0.1"
DB_USER = "fablab_user"
DB_PASS = "fablab_password"
DB_NAME = "fablab_monitoring"

# ==========================================
# GESTION DU CACHE (SMART SAVING)
# ==========================================
# Variable pour mémoriser quand a eu lieu le dernier enregistrement pour CHAQUE capteur
last_saved_time = {}
# Intervalle de sauvegarde en base de données en secondes
SAVE_INTERVAL_SECONDS = 60 

# ==========================================
# FONCTIONS MQTT
# ==========================================
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connecté au broker MQTT avec le code {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"📡 Écoute sur le topic : {MQTT_TOPIC}")

def save_to_db(topic, value):
    # Logique d'économie de la base de données
    current_time = time.time()
    
    # Si le capteur n'est jamais venu, on l'initialise à 0
    if topic not in last_saved_time:
        last_saved_time[topic] = 0
        
    # Vérification : Est-ce que le délai est écoulé ?
    time_since_last_save = current_time - last_saved_time[topic]
    if time_since_last_save < SAVE_INTERVAL_SECONDS:
        print(f"⏳ Sauvegarde ignorée : Le capteur {topic} a été écrit il y a {int(time_since_last_save)}s.")
        return

    try:
        float_value = float(value)
    except (ValueError, TypeError):
        print(f"⚠️ Impossible de convertir '{value}' en nombre pour le topic {topic}. Sauvegarde annulée.")
        return

    try:
        # On se connecte à la base
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # On insère la donnée (la date se mettra toute seule grâce à CURRENT_TIMESTAMP)
        sql = "INSERT INTO sensor_data (topic, value) VALUES (%s, %s)"
        val = (topic, float_value)
        
        cursor.execute(sql, val)
        conn.commit()
        print(f"💾 Donnée sauvegardée dans MySQL : {topic} = {value}")
        
        # On met à jour l'horloge interne pour ce capteur
        last_saved_time[topic] = current_time
        
    except mysql.connector.Error as err:
        print(f"❌ Erreur MySQL : {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        
        print(f"🔔 Message MQTT brut reçu sur [{topic}] : {payload}")
        
        # Cas 1 : Si c'est un simple chiffre (comme '320'), on le sauvegarde direct.
        try:
            # On essaie d'abord de voir si c'est bêtement un chiffre (entier ou flottant)
            val = float(payload)
            print(f"✅ Valeur numérique brute détectée : {val}")
            save_to_db(topic, val)
            return 
        except ValueError:
            pass # Ce n'est pas un nombre pur, ça doit être du texte ou du JSON. On continue.

        # Cas 2 : Si c'est du JSON 
        try:
            data = json.loads(payload)
            
            if isinstance(data, dict):
                print(f"✅ JSON détecté sur {topic}. Analyse des champs...")
                for key, value in data.items():
                    # On ignore les horodatages ou les données trop complexes (sous-dossiers)
                    if key in ["ts", "timestamp_ms"] or isinstance(value, dict):
                        continue
                    
                    # Si c'est un nombre ou un booléen (True/False)
                    if isinstance(value, (int, float, bool)) and not isinstance(value, str):
                        # Convertit les booléens en 1.0 ou 0.0, et garde les nombres
                        float_val = float(value) 
                        sub_topic = f"{topic}/{key}"
                        save_to_db(sub_topic, float_val)

            return # On a fini de traiter le JSON

        except json.JSONDecodeError:
            # Cas 3 : Ni un chiffre, ni un JSON valide (comme les messages cassés de Distrikase)
            print(f"⚠️ Donnée inexploitable ou mal formatée ignorée sur [{topic}] : {payload}")
            return
            
    except Exception as e:
        print(f"❌ Erreur inattendue lors du traitement du message sur {msg.topic} : {e}")

# ==========================================
# INITIALISATION
# ==========================================
if __name__ == "__main__":
    print("🚀 Démarrage du Bridge MQTT -> MySQL...")
    
    # IMPORTANT: L'université utilise un protocole WebSockets via le port 443 pour contourner les pare-feu
    client = mqtt.Client(transport="websockets")
    client.ws_set_options(path="/ws", headers=None)
    
    # L'université a activé TLS (Chiffrement SSL) et requiert une authentification
    client.tls_set()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print(f"🔗 Tentative de connexion à {MQTT_BROKER} sur le port {MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever() # Garde le script en vie pour écouter en continu
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bridge.")
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
