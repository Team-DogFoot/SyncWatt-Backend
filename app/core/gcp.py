import logging
from google.cloud import vision
from typing import Optional

logger = logging.getLogger(__name__)
_vision_client: Optional[vision.ImageAnnotatorClient] = None

def get_vision_client() -> vision.ImageAnnotatorClient:
    """Returns a singleton Google Cloud Vision client."""
    global _vision_client
    if _vision_client is None:
        logger.info("[GCP] Initializing Vision API client (singleton)")
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client
