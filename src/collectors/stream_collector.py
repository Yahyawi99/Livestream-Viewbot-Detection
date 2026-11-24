
import logging
import time

from datetime import datetime, timezone

from src.clients.twitch_helix import TwitchHelixClient
from src.ingestion.direct_ingestion import DirectIngestion


logger = logging.getLogger(__name__)


class StreamCollector:

    def __init__(self, interval_seconds=60,ingestion=None):

        self.client = TwitchHelixClient()
        self.ingestion = ingestion or DirectIngestion()

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


        
        uploaded_objects = self.ingestion.ingest(
            records,
            collected_at.isoformat()
        )

        logger.info(
            "Collected %d streams and appended them to the hourly batch.",
            len(records)
        )

        for object_key in uploaded_objects:
            logger.info("Uploaded to Backblaze B2: %s", object_key)


    
    def start(self):
        logger.info(
            "Starting collector. Interval: %d seconds",
            self.interval_seconds
        )

        try:
            # Recover pending data before starting new collections.
            logger.info("Checking for pending Bronze archives...")

            try:
                recovered_objects = self.ingestion.recover()

                for object_key in recovered_objects:
                    logger.info(
                        "Recovered and uploaded to Backblaze B2: %s",
                        object_key
                    )

            except Exception:
                logger.exception("Startup recovery failed.")

            while True:
                cycle_start = time.monotonic()

                try:
                    self.collect_once()

                except Exception:
                    logger.exception("Collection cycle failed")

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

            logger.info(
                "Collector stopped. Any unfinished hourly JSONL batch "
                "has been retained locally."
            )
