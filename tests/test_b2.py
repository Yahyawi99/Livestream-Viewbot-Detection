
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.storage.b2_storage import B2Storage


def test_b2_upload():
    storage = B2Storage()

    with TemporaryDirectory() as temp_dir:
        archive = Path(temp_dir) / "test.jsonl.gz"

        records = [
            {"stream_id": "100", "viewers": 150},
            {"stream_id": "200", "viewers": 300},
        ]

        with gzip.open(archive, "wt", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record) + "\n")

        object_key = "tests/test-b2-upload.jsonl.gz"

        uploaded_key = storage.upload_archive(
            archive,
            object_key,
        )

        print(f"Successfully uploaded: {uploaded_key}")


if __name__ == "__main__":
    test_b2_upload()
