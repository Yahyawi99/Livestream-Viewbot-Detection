
from abc import ABC, abstractmethod


class BaseIngestion(ABC):

    @abstractmethod
    def ingest(self, records: list[dict], collection_timestamp: str):
        pass
