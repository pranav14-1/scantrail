import unittest
import io
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from backend.main import scan_analyze, get_report
from backend.database import DefectRecord, DefectStatus
from backend.services import create_scantrail_pdf_report
from backend.config import settings

class MockUploadFile:
    def __init__(self, filename="road_pothole_test.jpg", content=b"\xFF\xD8\xFF\xE0" + b"\x00" * 300 + b"\xFF\xD9"):
        self.filename = filename
        self.content = content

    async def read(self):
        return self.content

class MockQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return MockQuery(sorted(self.records, key=lambda x: x.timestamp, reverse=True))

    def all(self):
        return list(self.records)

class MockDBSession:
    def __init__(self, records=None):
        self.records = records if records is not None else []

    def query(self, model):
        return MockQuery(self.records)

    def add(self, record):
        self.records.append(record)

    def commit(self):
        pass

    def rollback(self):
        pass

class TestApiAndPdfServiceMocking(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.db = MockDBSession()

    @patch("backend.services.gemini_model")
    async def test_scan_analyze_endpoint_and_schema(self, mock_gemini):
        """
        Step 1.2: End-to-End Endpoint & Service Mocking
        - Mock Gemini API response (gemini_model.generate_content)
        - Send POST /scan/analyze with dummy image bytes and GPS telemetry
        - Assert Status Code / Output success
        - Assert JSON Schema: evolution_status, area_change_percentage, severity_level, engineering_analysis, pdf_report_url
        """
        # Configure mock Gemini return
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "severity_level": "High",
            "root_cause_analysis": "Severe asphalt fatigue and moisture seepage under heavy axle loading.",
            "recommended_remediation": "Full-depth asphalt patching and edge drainage restoration.",
            "municipal_priority_rank": 8
        })
        mock_gemini.generate_content.return_value = mock_response

        dummy_image = MockUploadFile()
        lat = 28.613928
        lon = 77.209021

        response = await scan_analyze(
            image=dummy_image,
            latitude=lat,
            longitude=lon,
            timestamp="2026-09-15T12:00:00Z",
            bounding_box_area=0.45,
            severity_score=0.8,
            db=self.db
        )

        # Assert response dictionary schema
        self.assertIsInstance(response, dict)
        self.assertIn("defect_id", response)
        self.assertIn("evolution_status", response)
        self.assertIn("area_change_percentage", response)
        self.assertIn("severity_level", response)
        self.assertIn("engineering_analysis", response)
        self.assertIn("pdf_report_url", response)

        # Assert schema contents
        self.assertEqual(response["evolution_status"], "New")
        self.assertEqual(response["area_change_percentage"], 0.0)
        self.assertEqual(response["severity_level"], "High")
        self.assertEqual(response["engineering_analysis"]["municipal_priority_rank"], 8)
        self.assertTrue(response["pdf_report_url"].startswith("/reports/"))

        # Verify DB entry
        self.assertEqual(len(self.db.records), 1)
        created_record = self.db.records[0]
        self.assertEqual(created_record.defect_id, response["defect_id"])

        # PDF File Integrity Check: Verify PDF generated and written to disk
        defect_id = response["defect_id"]
        pdf_path = os.path.join(settings.REPORTS_DIR, f"ScanTrail_Report_{defect_id}.pdf")
        self.assertTrue(os.path.exists(pdf_path))
        
        file_size = os.path.getsize(pdf_path)
        self.assertGreater(file_size, 1000)

        with open(pdf_path, "rb") as f:
            header_bytes = f.read(4)
            self.assertEqual(header_bytes, b"%PDF")

        # Verify get_report response
        file_response = await get_report(defect_id)
        self.assertEqual(file_response.media_type, "application/pdf")

if __name__ == "__main__":
    unittest.main()

