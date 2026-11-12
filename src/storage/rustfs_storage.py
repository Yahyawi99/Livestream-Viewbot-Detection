
import os
import json
import boto3

from io import BytesIO
from dotenv import load_dotenv
from botocore.config import Config


load_dotenv()


class RustFSStorage:

    def __init__(self):
        self.bucket = os.getenv("RUSTFS_BUCKET")

        self.s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("RUSTFS_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("RUSTFS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("RUSTFS_SECRET_KEY"),
            region_name=os.getenv("RUSTFS_REGION", "us-east-1"),
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"}
            )
        )

    def upload_jsonl(self, records: list[dict], object_key: str):

        if not records:
            raise ValueError("Cannot upload an empty collection.")

        content = "\n".join(
            json.dumps(record, ensure_ascii=False)
            for record in records
        ) + "\n"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=content.encode("utf-8"),
            ContentType="application/x-ndjson"
        )

        return object_key
