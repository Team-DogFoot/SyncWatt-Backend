import logging
import json
from google.cloud import vision
from google.oauth2 import service_account
from app.core.config import settings

logger = logging.getLogger(__name__)
_vision_client: vision.ImageAnnotatorClient | None = None

def get_vision_client() -> vision.ImageAnnotatorClient:
    """Returns a singleton Google Cloud Vision client with support for JSON SA Key string."""
    global _vision_client
    if _vision_client is None:
        logger.info("[GCP] Initializing Vision API client (singleton)")
        
        # esgo-korea style: JSON string in environment variable
        if settings.GCP_SA_KEY:
            try:
                logger.info("[GCP] Using Service Account JSON string from GCP_SA_KEY")
                info = json.loads(settings.GCP_SA_KEY)
                
                # PEM 파일의 \n 문자열을 실제 줄바꿈으로 치환 (가장 중요한 부분)
                if "private_key" in info:
                    info["private_key"] = info["private_key"].replace("\\n", "\n")
                
                credentials = service_account.Credentials.from_service_account_info(info)
                _vision_client = vision.ImageAnnotatorClient(credentials=credentials)
            except Exception as e:
                logger.error(f"[GCP] Failed to parse GCP_SA_KEY as JSON: {e}")
                # Fallback to default credentials if JSON parsing fails
                _vision_client = vision.ImageAnnotatorClient()
        else:
            # Default behavior (uses GOOGLE_APPLICATION_CREDENTIALS path if set)
            _vision_client = vision.ImageAnnotatorClient()
            
    return _vision_client
