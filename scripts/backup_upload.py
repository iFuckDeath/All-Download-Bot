import os, sys, boto3
from botocore.config import Config

if len(sys.argv) != 3:
    raise SystemExit("Usage: backup_upload.py LOCAL_FILE OBJECT_NAME")
path, name = sys.argv[1], sys.argv[2]
s3 = boto3.client("s3", endpoint_url=os.getenv("BACKUP_S3_ENDPOINT_URL") or None,
    region_name=os.getenv("BACKUP_S3_REGION", "auto"),
    aws_access_key_id=os.environ["BACKUP_S3_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["BACKUP_S3_SECRET_ACCESS_KEY"],
    config=Config(signature_version="s3v4", retries={"max_attempts": 4, "mode": "standard"}))
bucket = os.environ["BACKUP_S3_BUCKET"]
key = f"{os.getenv('BACKUP_PREFIX','telegram-media-bot/postgres').strip('/')}/{name}"
s3.upload_file(path, bucket, key, ExtraArgs={"ServerSideEncryption":"AES256","ContentType":"application/gzip"})
print(f"Uploaded backup object s3://{bucket}/{key}")
