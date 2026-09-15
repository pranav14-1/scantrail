from .config import settings

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    mqtt = None
    HAS_MQTT = False

def publish_mqtt_notification(topic: str, message: str):
    """Connects to MQTT broker and publishes a message."""
    if not HAS_MQTT or not settings.MQTT_HOSTNAME:
        print(f"[MQTT Stub] Published notification on '{topic}': {message}")
        return
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        client.connect(settings.MQTT_HOSTNAME, settings.MQTT_PORT, 60)
        client.publish(topic, message)
        client.disconnect()
        print(f"[MQTT] Published '{message}' to topic '{topic}'")
    except Exception as e:
        print(f"[MQTT] Failed to publish message: {e}")
