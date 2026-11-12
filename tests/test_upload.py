
from src.storage.rustfs_storage import RustFSStorage

storage = RustFSStorage()

records = [
    {
        "stream_id": "123",
        "platform": "twitch",
        "viewer_count": 1200
    },
    {
        "stream_id": "456",
        "platform": "twitch",
        "viewer_count": 850
    }
]

key = "streams/test/streams_test.jsonl"

uploaded_key = storage.upload_jsonl(records, key)

print(f"Uploaded successfully: {uploaded_key}")
