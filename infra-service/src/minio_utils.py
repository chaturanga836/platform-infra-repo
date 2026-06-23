"""S3/MinIO helpers for bucket bootstrap."""

from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError


def ensure_bucket(
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    bucket: str,
) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"404", "NoSuchBucket", "Not Found"}:
            client.create_bucket(Bucket=bucket)
            return
        raise
