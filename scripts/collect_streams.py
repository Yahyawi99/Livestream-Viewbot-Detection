
import logging

from src.collectors.stream_collector import StreamCollector


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():

    collector = StreamCollector(
        interval_seconds=60
    )

    collector.start()


if __name__ == "__main__":
    main()
