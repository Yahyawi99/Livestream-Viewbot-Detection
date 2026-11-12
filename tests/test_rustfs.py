
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

bucket = os.getenv("RUSTFS_BUCKET")

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("RUSTFS_ENDPOINT_URL"),
    aws_access_key_id=os.getenv("RUSTFS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("RUSTFS_SECRET_KEY"),
    region_name=os.getenv("RUSTFS_REGION"),
)


print(s3.list_buckets())
print(s3.head_bucket(Bucket=bucket))

print(f"Successfully connected to RustFS bucket: {bucket}")
