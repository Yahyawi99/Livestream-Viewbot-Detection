
import json
import logging

from confluent_kafka import Producer

from src.config.settings import Settings


logger = logging.getLogger(__name__)


class KafkaStreamProducer:

    def __init__(self):
        self.topic = Settings.KAFKA_STREAMS_TOPIC

        self.producer = Producer({
            "bootstrap.servers": Settings.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "twitch-stream-collector",
            "acks": "all",
            "enable.idempotence": True,
            "delivery.timeout.ms": 120000,
            "linger.ms": 10,
        })

    def publish(self, records: list[dict]) -> int:
        delivery_errors = []

        def delivery_callback(error, message):
            if error:
                delivery_errors.append(error)

        for record in records:
            stream_id = record["raw_data"]["id"]

            self.producer.produce(
                topic=self.topic,
                key=str(stream_id),
                value=json.dumps(record, ensure_ascii=False),
                callback=delivery_callback,
            )

            self.producer.poll(0)

        remaining = self.producer.flush(30)

        if remaining:
            raise TimeoutError(
                f"{remaining} Kafka messages were not delivered."
            )

        if delivery_errors:
            raise RuntimeError(
                f"Kafka delivery failed: {delivery_errors[0]}"
            )

        logger.info(
            "Published %d stream records to Kafka topic %s",
            len(records),
            self.topic,
        )

        return len(records)

    def close(self):
        remaining = self.producer.flush(30)

        if remaining:
            logger.warning(
                "%d Kafka messages remain undelivered.",
                remaining,
            )
