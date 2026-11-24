
import gzip
import json

from pathlib import Path
from tempfile import TemporaryDirectory

from src.ingestion.hourly_batcher import HourlyBatcher


def test_hourly_batching():
    with TemporaryDirectory() as temp_dir:
        batcher = HourlyBatcher(temp_dir)

        # First collection: 14:59 UTC
        records_1 = [
            {"stream_id": "100", "viewers": 150},
            {"stream_id": "200", "viewers": 300},
        ]

        batcher.append(
            records_1,
            "2026-11-24T14:59:00+00:00"
        )

        # Second collection: 15:00 UTC
        records_2 = [
            {"stream_id": "100", "viewers": 175},
        ]

        compressed = batcher.append(
            records_2,
            "2026-11-24T15:00:00+00:00"
        )

        assert len(compressed) == 1

        archive = Path(temp_dir) / "2026-11-24" / "14.jsonl.gz"

        assert archive.exists()

        with gzip.open(archive, "rt", encoding="utf-8") as file:
            archived_records = [
                json.loads(line) for line in file
            ]

        assert len(archived_records) == 2
        assert archived_records[0]["stream_id"] == "100"
        assert archived_records[1]["viewers"] == 300

        # Current hour must remain uncompressed.
        current_file = Path(temp_dir) / "2026-11-24" / "15.jsonl"
        assert current_file.exists()

        print("Hourly batching test passed!")


if __name__ == "__main__":
    test_hourly_batching()
