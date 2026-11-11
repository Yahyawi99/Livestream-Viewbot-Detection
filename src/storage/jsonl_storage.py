
import json
from pathlib import Path


class JsonlStreamStorage:

    def __init__(self, base_dir="data/raw/twitch/streams"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, records, collection_date):
        """
        Append stream observations to a daily JSONL file.
        """

        file_path = self.base_dir / f"{collection_date}.jsonl"

        with file_path.open("a", encoding="utf-8") as file:
            for record in records:
                file.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

        return file_path
