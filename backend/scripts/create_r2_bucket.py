"""Create the R2 bucket if it doesn't exist."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.r2_service import get_r2_client
from app.config import settings
from botocore.exceptions import ClientError


def main():
    client = get_r2_client()
    bucket = settings.R2_BUCKET_NAME
    try:
        client.head_bucket(Bucket=bucket)
        print(f"[OK] Bucket already exists: {bucket}")
        return
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket", "NoSuchKey"):
            print(f"[head_bucket error] {code}: {e}")

    try:
        client.create_bucket(Bucket=bucket)
        print(f"[OK] Created bucket: {bucket}")
    except ClientError as e:
        print(f"[create error] {e}")
        raise


if __name__ == "__main__":
    main()
