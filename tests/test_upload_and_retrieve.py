
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

print("============================")
print(f"Uploaded successfully: {uploaded_key}")
print("============================")


response = storage.s3.get_object(
    Bucket=storage.bucket,
    Key=key
)
print("============================")
print("retrieved successfully")
print(response["Body"].read().decode("utf-8"))
print("============================")
