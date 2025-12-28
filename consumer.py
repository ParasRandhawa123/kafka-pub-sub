import json
from confluent_kafka import Consumer

from configs import KAFKA_HOST

consumer_config = {
    "bootstrap.servers": KAFKA_HOST,
    "group.id": "order-tracker",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False
}

TOPICS_TO_SUBSCRIBE = ['orders']

consumer = Consumer(consumer_config)

consumer.subscribe(TOPICS_TO_SUBSCRIBE)

print(f"🟢 Consumer is running and subscribed to {', '.join(TOPICS_TO_SUBSCRIBE)}")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        
        if msg.error():
            print(f"❌ Error : {msg.error()}")
            continue
        
        value = msg.value().decode('utf-8')
        order = json.loads(value)
        consumer.commit()
        print(f"📦 Recived Order : {order}")
except KeyboardInterrupt:
    print("\n🔴 Consumer is stopped")

finally:
    consumer.close()