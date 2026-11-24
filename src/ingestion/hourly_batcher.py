
import gzip
import json
import os
import shutil

from datetime import datetime, timezone
from pathlib import Path


class HourlyBatcher:
    def __init__(self, base_dir="data/buffer/twitch/streams"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        collected_at = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        if collected_at.tzinfo is None:
            raise ValueError("Collection timestamp must include a timezone.")

        return collected_at.astimezone(timezone.utc)

    def _get_hour_directory(self, timestamp: datetime) -> Path:
        return self.base_dir / timestamp.strftime("%Y-%m-%d")

    def append(self, records: list[dict], collection_timestamp: str):
        collected_at = self._parse_timestamp(collection_timestamp)

        if records:
            hour_dir = self._get_hour_directory(collected_at)
            hour_dir.mkdir(parents=True, exist_ok=True)

            hour_file = hour_dir / f"{collected_at:%H}.jsonl"

            with hour_file.open("a", encoding="utf-8") as file:
                for record in records:
                    file.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )

                file.flush()
                os.fsync(file.fileno())

        return self.compress_completed_batches(collected_at)

    def compress_completed_batches(self, current_timestamp: datetime):
        current_hour = current_timestamp.replace(
            minute=0, second=0, microsecond=0
        )

        compressed_files = []

        for jsonl_file in sorted(self.base_dir.glob("*/*.jsonl")):
            file_hour = datetime.strptime(
                f"{jsonl_file.parent.name} {jsonl_file.stem}",
                "%Y-%m-%d %H"
            ).replace(tzinfo=timezone.utc)

            if file_hour >= current_hour:
                continue

            gzip_file = jsonl_file.with_suffix(".jsonl.gz")
            temp_file = gzip_file.with_suffix(".jsonl.gz.tmp")

            try:
                with jsonl_file.open("rb") as source:
                    with gzip.open(temp_file, "wb") as destination:
                        shutil.copyfileobj(source, destination)

                temp_file.replace(gzip_file)
                jsonl_file.unlink()

                compressed_files.append(gzip_file)

            except Exception:
                if temp_file.exists():
                    temp_file.unlink()

                raise

        return compressed_files
