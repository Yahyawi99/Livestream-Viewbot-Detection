
import os
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv


load_dotenv()


class B2Storage:
    def __init__(self):
        required_variables = [
            "B2_ENDPOINT_URL",
            "B2_REGION",
            "B2_BUCKET",
            "B2_ACCESS_KEY_ID",
            "B2_SECRET_ACCESS_KEY",
        ]

        missing = [
            variable
            for variable in required_variables
            if not os.getenv(variable)
        ]

        if missing:
            raise ValueError(
                f"Missing B2 environment variables: {', '.join(missing)}"
            )

        self.bucket = os.getenv("B2_BUCKET")

        self.s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("B2_ENDPOINT_URL"),
            region_name=os.getenv("B2_REGION"),
            aws_access_key_id=os.getenv("B2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("B2_SECRET_ACCESS_KEY"),
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def upload_archive(self, file_path: str | Path, object_key: str):
        file_path = Path(file_path)

        if not file_path.is_file():
            raise FileNotFoundError(file_path)

        self.s3.upload_file(
            str(file_path),
            self.bucket,
            object_key,
            ExtraArgs={
                "ContentType": "application/x-ndjson",
                "ContentEncoding": "gzip",
            },
        )

        return object_key
