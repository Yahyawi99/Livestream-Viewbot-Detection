
import logging
import time

from datetime import datetime, timezone

from src.clients.twitch_helix import TwitchHelixClient
from src.storage.jsonl_storage import JsonlStreamStorage


logger = logging.getLogger(__name__)


class StreamCollector:

    def __init__(self, interval_seconds=60):

        self.client = TwitchHelixClient()
        self.storage = JsonlStreamStorage()

        self.interval_seconds = interval_seconds

    def collect_once(self):
        """
        Retrieve all currently live streams
        and store their raw API responses.
        """

        # One timestamp for this collection cycle.
        collected_at = datetime.now(timezone.utc)

        logger.info("Starting Twitch collection cycle")

        # Retrieve all pages of live streams.
        streams = self.client.get_all_streams()

        records = []

        for stream in streams:

            records.append({
                "collected_at": collected_at.isoformat(),
                "platform": "twitch",
                "raw_data": stream
            })

        # Use the UTC date to partition the output file.
        collection_date = collected_at.strftime("%Y-%m-%d")

        file_path = self.storage.save(
            records,
            collection_date
        )

        logger.info(
            "Collected %d streams. Saved to %s",
            len(records),
            file_path
        )

    def start(self):
        """
        Run collection continuously.
        """

        logger.info(
            "Starting collector. Interval: %d seconds",
            self.interval_seconds
        )

        try:
            while True:

                cycle_start = time.monotonic()

                try:
                    self.collect_once()

                except Exception:
                    logger.exception("Collection cycle failed")

                # Avoid starting cycles faster than the configured interval.
                elapsed = time.monotonic() - cycle_start

                sleep_time = max(
                    30,
                    self.interval_seconds - elapsed
                )

                time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Collector stopped by user")

        finally:
            self.client.close()
