import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import structlog
from app.config import settings

log = structlog.get_logger()


def get_r2_client():
    endpoint = settings.R2_ENDPOINT_URL
    if "{ACCOUNT_ID}" in endpoint:
        endpoint = endpoint.format(ACCOUNT_ID=settings.R2_ACCOUNT_ID)
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


async def upload_file_to_r2(local_path: str, r2_key: str, content_type: str = "application/octet-stream") -> str:
    client = get_r2_client()
    try:
        with open(local_path, "rb") as f:
            client.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType=content_type,
            )
        log.info("r2_upload.success", key=r2_key)
        return r2_key
    except ClientError as e:
        log.error("r2_upload.error", error=str(e), key=r2_key)
        raise


async def generate_presigned_url(r2_key: str, expiry_seconds: int = 86400) -> str:
    client = get_r2_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": r2_key},
        ExpiresIn=expiry_seconds,
    )
    return url


async def list_exports(prefix: str = "exports/") -> list[dict]:
    client = get_r2_client()
    response = client.list_objects_v2(Bucket=settings.R2_BUCKET_NAME, Prefix=prefix)
    return [
        {"key": obj["Key"], "size": obj["Size"], "last_modified": obj["LastModified"]}
        for obj in response.get("Contents", [])
    ]
