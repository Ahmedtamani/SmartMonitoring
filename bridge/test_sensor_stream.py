import json
import time
import paho.mqtt.client as mqtt

MQTT_BROKER = "mqtt.univ-cotedazur.fr"
MQTT_PORT = 443
MQTT_USER = "fablab2122"
MQTT_PASS = "2122"
TOPIC = "FABLAB_21_22/#"
MAX_MESSAGES = 8
TIMEOUT_SECONDS = 20

received = 0


def on_connect(client, userdata, flags, rc):
    print(f"[TEST] Connected rc={rc}")
    client.subscribe(TOPIC)
    print(f"[TEST] Subscribed to {TOPIC}")


def on_message(client, userdata, msg):
    global received
    payload = msg.payload.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(payload)
        kind = "json"
    except Exception:
        parsed = payload
        kind = "raw"

    received += 1
    print(f"[TEST] #{received} topic={msg.topic} kind={kind} payload={parsed}")


if __name__ == "__main__":
    client = mqtt.Client(transport="websockets")
    client.ws_set_options(path="/ws", headers=None)
    client.tls_set()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    start = time.time()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    try:
        while (time.time() - start) < TIMEOUT_SECONDS and received < MAX_MESSAGES:
            time.sleep(0.25)
    finally:
        client.loop_stop()
        client.disconnect()

    if received == 0:
        print("[TEST] No messages received in time window")
    else:
        print(f"[TEST] Done, received {received} messages")
