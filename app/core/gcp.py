from google.cloud import vision
from typing import Optional

_vision_client: Optional[vision.ImageAnnotatorClient] = None

def get_vision_client() -> vision.ImageAnnotatorClient:
    """Returns a singleton Google Cloud Vision client."""
    global _vision_client
    if _vision_client is None:
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client
