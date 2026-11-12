
from src.ingestion.base import BaseIngestion
from src.storage.rustfs_storage import RustFSStorage


class DirectIngestion(BaseIngestion):

    def __init__(self):
        self.storage = RustFSStorage()

    def ingest(self, records: list[dict], collection_timestamp: str):

        if not records:
            return None

        object_key = (
            f"streams/"
            f"{collection_timestamp[:10]}/"
            f"{collection_timestamp.replace(':', '-').replace('.', '-')}.jsonl"
        )

        return self.storage.upload_jsonl(records, object_key)
