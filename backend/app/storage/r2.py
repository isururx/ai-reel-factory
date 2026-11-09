"""Private Cloudflare R2 storage adapter using its S3-compatible API."""
from __future__ import annotations

from typing import BinaryIO
import boto3
from botocore.client import BaseClient
from app.core.settings import settings


def get_r2_client() -> BaseClient:
    required = {
        "R2_ACCOUNT_ID": settings.r2_account_id,
        "R2_ACCESS_KEY_ID": settings.r2_access_key_id,
        "R2_SECRET_ACCESS_KEY": settings.r2_secret_access_key,
        "R2_BUCKET_NAME": settings.r2_bucket_name,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Cloudflare R2 is not configured; missing: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def upload_fileobj(fileobj: BinaryIO, object_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload a private object and return its key for storage in PostgreSQL."""
    if not object_key or object_key.startswith("/"):
        raise ValueError("object_key must be a non-empty relative key")
    get_r2_client().upload_fileobj(
        fileobj,
        settings.r2_bucket_name,
        object_key,
        ExtraArgs={"ContentType": content_type},
    )
    return object_key


def create_download_url(object_key: str, expires_in: int = 900) -> str:
    """Create a short-lived URL for a private object (15 minutes by default)."""
    if not 1 <= expires_in <= 604800:
        raise ValueError("expires_in must be between 1 second and 7 days")
    return get_r2_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": object_key},
        ExpiresIn=expires_in,
    )



def download_file(object_key: str, destination: str) -> None:
    """Download a private R2 object to a local temporary path."""
    if not object_key or object_key.startswith("/"):
        raise ValueError("object_key must be a non-empty relative key")
    get_r2_client().download_file(settings.r2_bucket_name, object_key, destination)
