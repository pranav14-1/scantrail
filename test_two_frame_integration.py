import unittest
import io
import os
import uuid
from datetime import datetime, timedelta
from backend.database import DefectRecord, DefectStatus
from backend.spatial_engine import (
    get_previous_and_classify,
    extract_visual_embedding
)
from backend.services import (
    analyze_civil_road_defect,
    create_scantrail_pdf_report
)
from backend.config import settings

class MockQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.records)

class MockDB:
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

class TestTwoFrameWorkflow(unittest.TestCase):

    def setUp(self):
        self.db = MockDB()

    def test_workflow_step_1_base_frame(self):
        """
        Phase 4.1: First Capture Test (Base Frame)
        Upload Image A at (Lat X, Lon Y). Verify backend records it as New in database.
        """
        lat, lon = 28.6139, 77.2090
        image_bytes = b"fake_pothole_image_data_A"
        area_a = 0.40

        visual_embedding = extract_visual_embedding(image_bytes)
        prev_rec, status, growth_rate, match_score, match_details = get_previous_and_classify(
            db_session=self.db,
            lat=lat,
            lon=lon,
            current_embedding=visual_embedding,
            current_area=area_a
        )

        self.assertIsNone(prev_rec)
        self.assertEqual(status, DefectStatus.NEW)
        self.assertEqual(growth_rate, 0.0)

        # Save record A
        record_a = DefectRecord(
            defect_id="defect-frame-A",
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow() - timedelta(days=7),
            visual_embedding=visual_embedding,
            bounding_box_area=area_a,
            status=status,
            severity_score=0.5
        )
        self.db.add(record_a)
        self.assertEqual(len(self.db.records), 1)

    def test_workflow_step_2_temporal_frame_progression(self):
        """
        Phase 4.2: Second Capture Test (Temporal Frame)
        Upload Image B at same location. Backend detects Image A as previous frame,
        calculates area delta, assigns evolution state (Worsening), and updates DB.
        """
        lat, lon = 28.6139, 77.2090
        image_bytes_a = b"fake_pothole_image_data_A"
        embedding_a = extract_visual_embedding(image_bytes_a)
        area_a = 0.40

        record_a = DefectRecord(
            defect_id="defect-frame-A",
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow() - timedelta(days=7),
            visual_embedding=embedding_a,
            bounding_box_area=area_a,
            status=DefectStatus.NEW,
            severity_score=0.5
        )
        self.db.add(record_a)

        # Now simulate Visit B 7 days later: area grew from 0.40 to 0.50 (+25%)
        image_bytes_b = b"fake_pothole_image_data_B"
        # Since it's the same defect photographed again, embedding is similar
        embedding_b = list(embedding_a)
        area_b = 0.50

        prev_rec, status, growth_rate, match_score, match_details = get_previous_and_classify(
            db_session=self.db,
            lat=lat,
            lon=lon,
            current_embedding=embedding_b,
            current_area=area_b
        )

        self.assertIsNotNone(prev_rec)
        self.assertEqual(prev_rec.defect_id, "defect-frame-A")
        self.assertEqual(status, DefectStatus.WORSENING)
        self.assertAlmostEqual(growth_rate, 25.0, delta=0.1)

        # Civil advisory generation
        advisory = analyze_civil_road_defect(
            latitude=lat,
            longitude=lon,
            status=status.value,
            area_delta_pct=growth_rate,
            current_area=area_b,
            previous_area=prev_rec.bounding_box_area,
            time_delta_str="7d 0h ago",
            severity_score=0.8
        )
        self.assertIn(advisory["severity_level"], ["High", "Critical", "Medium"])
        self.assertTrue(1 <= advisory["municipal_priority_rank"] <= 10)

        # PDF Report generation
        new_id = str(uuid.uuid4())
        pdf_buf = create_scantrail_pdf_report(
            defect_id=new_id,
            lat=lat,
            lon=lon,
            status=status.value,
            current_area=area_b,
            previous_area=prev_rec.bounding_box_area,
            growth_rate_pct=growth_rate,
            time_delta_str="7d 0h ago",
            scan_timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            advisory=advisory
        )
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Save record B
        record_b = DefectRecord(
            defect_id=new_id,
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow(),
            visual_embedding=embedding_b,
            bounding_box_area=area_b,
            status=status,
            severity_score=0.8
        )
        self.db.add(record_b)
        self.assertEqual(len(self.db.records), 2)

if __name__ == "__main__":
    unittest.main()

