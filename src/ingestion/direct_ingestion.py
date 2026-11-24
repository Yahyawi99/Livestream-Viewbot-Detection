
import logging

from src.ingestion.base import BaseIngestion
from src.ingestion.hourly_batcher import HourlyBatcher
from src.storage.b2_storage import B2Storage

logger = logging.getLogger(__name__)


class DirectIngestion(BaseIngestion):
    def __init__(self, batcher=None, storage=None):
        self.batcher = batcher or HourlyBatcher()
        self.storage = storage or B2Storage()

    def ingest(self, records: list[dict], collection_timestamp: str):
        # Append new records and compress completed hourly batches.
        self.batcher.append(records, collection_timestamp)

        uploaded_objects = []

        # Retry all locally preserved compressed archives.
        pending_archives = sorted(
            self.batcher.base_dir.glob("*/*.jsonl.gz")
        )

        for archive in pending_archives:
            relative_path = archive.relative_to(self.batcher.base_dir)

            object_key = f"streams/{relative_path.as_posix()}"

            try:
                self.storage.upload_archive(archive, object_key)

                # Delete locally only after successful upload.
                archive.unlink()

                uploaded_objects.append(object_key)

                logger.info("Uploaded and archived: %s", object_key)

            except Exception:
                logger.exception(
                    "Failed to upload %s. Local archive preserved.",
                    archive
                )

        return uploaded_objects
