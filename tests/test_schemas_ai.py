import unittest
from pydantic import ValidationError
from app.schemas.ai import ImageAnalysisResult

class TestImageAnalysisResult(unittest.TestCase):
    def test_image_analysis_result_valid(self):
        data = {
            "summary": "This is a test summary",
            "extracted_data": {"key": "value"},
            "detected_language": "en"
        }
        result = ImageAnalysisResult(**data)
        self.assertEqual(result.summary, data["summary"])
        self.assertEqual(result.extracted_data, data["extracted_data"])
        self.assertEqual(result.detected_language, data["detected_language"])

    def test_image_analysis_result_missing_field(self):
        data = {
            "summary": "This is a test summary",
            "extracted_data": {"key": "value"}
            # missing detected_language
        }
        with self.assertRaises(ValidationError):
            ImageAnalysisResult(**data)

if __name__ == "__main__":
    unittest.main()
