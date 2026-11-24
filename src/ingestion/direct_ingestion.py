
from src.ingestion.base import BaseIngestion
from src.ingestion.hourly_batcher import HourlyBatcher


class DirectIngestion(BaseIngestion):
    def __init__(self, batcher=None):
        self.batcher = batcher or HourlyBatcher()

    def ingest(self, records: list[dict], collection_timestamp: str):
        return self.batcher.append(records, collection_timestamp)
