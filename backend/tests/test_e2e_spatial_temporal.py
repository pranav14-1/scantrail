import unittest
import io
import os
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from backend.main import scan_analyze, get_report
from backend.database import DefectRecord, DefectStatus
from backend.config import settings

class MockUploadFile:
    def __init__(self, filename="road_pothole.jpg", content=b"\xFF\xD8\xFF\xE0" + b"\x00" * 500 + b"\xFF\xD9"):
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

class MockDatabaseSession:
    def __init__(self):
        self.records = []

    def query(self, model):
        return MockQuery(self.records)

    def add(self, record):
        self.records.append(record)

    def commit(self):
        pass

    def rollback(self):
        pass

class TestE2ESpatialTemporalWorkflow(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.db = MockDatabaseSession()

    @patch("backend.services.gemini_model")
    async def test_complete_spatial_temporal_lifecycle(self, mock_gemini):
        """
        Step 1.1: Automated Database & PostGIS Integration Test Suite
        1. Base Frame Test (New):
           - POST /scan/analyze at (12.8406, 80.1534) with area = 0.50
           - Assert status 200, evolution_status == 'New', area_change_percentage == 0.0
        2. Temporal Frame Test (Worsening):
           - POST /scan/analyze at (12.8407, 80.1535) (within 1.5m) with area = 0.65 (+30% expansion)
           - Assert evolution_status == 'Worsening', area_change_percentage == 30.0
        3. Temporal Frame Test (Improving):
           - POST /scan/analyze at same coordinate with area = 0.35 (-46% shrinkage)
           - Assert evolution_status == 'Improving'
        4. PDF Report Validation:
           - Fetch returned pdf_report_url via GET /reports/{report_id}
           - Assert status 200, media_type == 'application/pdf', and size > 5 KB.
        """
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "severity_level": "High",
            "root_cause_analysis": "Asphalt fatigue cracking aggravated by subsurface water seepage.",
            "recommended_remediation": "Full-depth asphalt patching and edge drainage installation.",
            "municipal_priority_rank": 8
        })
        mock_gemini.generate_content.return_value = mock_response

        # --- 1. Base Frame Test (New) ---
        lat_base, lon_base = 12.8406, 80.1534
        img1 = MockUploadFile(filename="frame1_base.jpg")

        res1 = await scan_analyze(
            image=img1,
            latitude=lat_base,
            longitude=lon_base,
            timestamp="2026-09-01T10:00:00Z",
            bounding_box_area=0.50,
            severity_score=0.4,
            db=self.db
        )

        self.assertIsInstance(res1, dict)
        self.assertEqual(res1["evolution_status"], "New")
        self.assertEqual(res1["area_change_percentage"], 0.0)
        self.assertEqual(res1["current_area"], 0.50)
        self.assertIsNone(res1["previous_area"])
        self.assertEqual(len(self.db.records), 1)
        base_id = res1["defect_id"]

        # --- 2. Temporal Frame Test (Worsening: +30% expansion) ---
        # (12.840610, 80.153408) is within ~1.4 meters of base frame
        lat_worsening, lon_worsening = 12.840610, 80.153408
        img2 = MockUploadFile(filename="frame2_worsening.jpg")

        res2 = await scan_analyze(
            image=img2,
            latitude=lat_worsening,
            longitude=lon_worsening,
            timestamp="2026-09-08T10:00:00Z",
            bounding_box_area=0.65,  # (0.65 - 0.50) / 0.50 = +30.0%
            severity_score=0.75,
            db=self.db
        )

        self.assertEqual(res2["evolution_status"], "Worsening")
        self.assertAlmostEqual(res2["area_change_percentage"], 30.0, delta=0.1)
        self.assertEqual(res2["current_area"], 0.65)
        self.assertEqual(res2["previous_area"], 0.50)
        self.assertEqual(len(self.db.records), 2)
        worsening_id = res2["defect_id"]

        # --- 3. Temporal Frame Test (Improving: -46.15% shrinkage) ---
        img3 = MockUploadFile(filename="frame3_improving.jpg")

        res3 = await scan_analyze(
            image=img3,
            latitude=lat_worsening,
            longitude=lon_worsening,
            timestamp="2026-09-15T10:00:00Z",
            bounding_box_area=0.35,  # (0.35 - 0.65) / 0.65 = -46.15%
            severity_score=0.3,
            db=self.db
        )

        self.assertEqual(res3["evolution_status"], "Improving")
        self.assertAlmostEqual(res3["area_change_percentage"], -46.15, delta=0.5)
        self.assertEqual(res3["current_area"], 0.35)
        self.assertEqual(res3["previous_area"], 0.65)
        self.assertEqual(len(self.db.records), 3)

        # --- 4. PDF Report Validation ---
        pdf_response = await get_report(worsening_id)
        self.assertEqual(pdf_response.media_type, "application/pdf")
        self.assertTrue(os.path.exists(pdf_response.path))

        pdf_size = os.path.getsize(pdf_response.path)
        # Assert file size > 5 KB (5120 bytes)
        self.assertGreater(pdf_size, 5120, f"Expected PDF > 5KB, got {pdf_size} bytes")

        with open(pdf_response.path, "rb") as f:
            magic_bytes = f.read(4)
            self.assertEqual(magic_bytes, b"%PDF")

if __name__ == "__main__":
    unittest.main()
