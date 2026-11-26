
import json

from confluent_kafka import Consumer

from src.producers.kafka_stream_producer import KafkaStreamProducer


def test_kafka_producer():
    producer = KafkaStreamProducer()

    record = {
        "collected_at": "2026-11-26T18:00:00+00:00",
        "platform": "twitch",
        "raw_data": {
            "id": "test-stream-123",
            "viewer_count": 1500
        }
    }

    producer.publish([record])
    producer.close()
    
    consumer = Consumer({
        "bootstrap.servers": "127.0.0.1:9092",
        "group.id": "kafka-producer-test",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    consumer.subscribe(["twitch.streams.raw"])


    try:
        message = consumer.poll(10)

        assert message is not None, "No message received"
        assert message.error() is None, message.error()

        received = json.loads(message.value())

        assert message.key().decode() == "test-stream-123"
        assert received == record

        print("Kafka producer test successful!")
        print("Received:", received)

    finally:
        consumer.close()


if __name__ == "__main__":
    test_kafka_producer()
