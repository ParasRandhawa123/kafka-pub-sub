import json
import uuid
from confluent_kafka import Producer

from configs import KAFKA_HOST

# ================ CallBack Functions ===================
def delivery_report(error, msg):
    if error:
        print(f"Error ❌ : {error}")
    else:
        print(f"Msg Sent Successfully ✅ : {msg.value().decode('utf-8')}")
        print(f"Delivered to topic : {msg.topic()} and Partition : {msg.partition()} and at offset : {msg.offset()}")

# =======================================================

producer_config = {
    'bootstrap.servers': KAFKA_HOST
}

producer = Producer(producer_config)

# Event to send
order = {
    "order_id": str(uuid.uuid4()),
    "username": "indu",
    "product_id": 23,
    "product_name": "yogurt"
}

value = json.dumps(order).encode('utf-8')
producer.produce(topic='orders', value=value, callback=delivery_report)
producer.flush()