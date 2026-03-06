import logging
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


def upload_image_to_s3(image_bytes: bytes, chat_id: int, session_id: str) -> str | None:
    """
    이미지를 S3에 업로드합니다. 동기 함수 (BackgroundTasks에서 호출).
    경로: {chat_id}/{date}/{session_id}.jpg
    """
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        logger.warning("[S3] AWS credentials not configured. Skipping upload.")
        return None

    import boto3

    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"{chat_id}/{today}/{session_id}.jpg"

    try:
        client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
        s3_path = f"s3://{settings.AWS_S3_BUCKET}/{key}"
        logger.info(f"[S3] Image uploaded: {s3_path} ({len(image_bytes)} bytes)")
        return s3_path
    except Exception as e:
        logger.error(f"[S3] Upload failed: {str(e)}")
        return None
