
import logging

from datetime import datetime, timezone

from src.ingestion.base import BaseIngestion
from src.ingestion.hourly_batcher import HourlyBatcher
from src.storage.b2_storage import B2Storage

logger = logging.getLogger(__name__)


class DirectIngestion(BaseIngestion):
    def __init__(self, batcher=None, storage=None):
        self.batcher = batcher or HourlyBatcher()
        self.storage = storage or B2Storage()

    def _upload_pending_archives(self):
        uploaded_objects = []

        pending_archives = sorted(
            self.batcher.base_dir.glob("*/*.jsonl.gz")
        )

        for archive in pending_archives:
            relative_path = archive.relative_to(
                self.batcher.base_dir
            )

            object_key = f"streams/{relative_path.as_posix()}"

            try:
                self.storage.upload_archive(archive, object_key)

                archive.unlink()

                uploaded_objects.append(object_key)

                logger.info(
                    "Uploaded and archived: %s",
                    object_key
                )

            except Exception:
                logger.exception(
                    "Failed to upload %s. Local archive preserved.",
                    archive
                )

        return uploaded_objects

    def recover(self):
        # Compress completed batches left behind by a previous run.
        self.batcher.compress_completed_batches(
            datetime.now(timezone.utc)
        )

        # Retry archives that were not uploaded successfully.
        return self._upload_pending_archives()

    def ingest(self, records: list[dict], collection_timestamp: str):
        self.batcher.append(records, collection_timestamp)

        return self._upload_pending_archives()
