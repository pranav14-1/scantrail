import unittest
import numpy as np
from datetime import datetime, timedelta
from backend.database import DefectRecord, DefectStatus
from backend.spatial_engine import (
    haversine_distance,
    calculate_cosine_similarity,
    calculate_area_ratio,
    compute_composite_score,
    classify_two_frame_evolution,
    get_previous_and_classify,
    MATCHING_THRESHOLD
)
from backend.services import analyze_civil_road_defect, create_scantrail_pdf_report

class MockQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self.records

class MockSession:
    def __init__(self, records):
        self.records = records

    def query(self, model):
        return MockQuery(self.records)

    def rollback(self):
        pass

class TestTwoFrameSpatialEngine(unittest.TestCase):

    def test_two_frame_first_capture(self):
        # First capture test: No historical record -> New
        db = MockSession(records=[])
        lat, lon = 28.6139, 77.2090
        current_embedding = [0.1] * 128
        current_area = 0.5

        prev_rec, status, growth_rate, score, details = get_previous_and_classify(
            db, lat, lon, current_embedding, current_area
        )
        self.assertIsNone(prev_rec)
        self.assertEqual(status, DefectStatus.NEW)
        self.assertEqual(growth_rate, 0.0)

    def test_two_frame_second_capture_worsening(self):
        # Second capture test: Image B at same location with +25% area growth (> +15%) -> Worsening
        lat, lon = 28.6139, 77.2090
        v = [0.2] * 128
        norm = np.linalg.norm(v)
        v = (np.array(v) / norm).tolist()

        base_frame = DefectRecord(
            defect_id="base-defect-001",
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow() - timedelta(days=7),
            visual_embedding=v,
            bounding_box_area=0.40,
            status=DefectStatus.NEW,
            severity_score=0.4
        )
        db = MockSession(records=[base_frame])

        # Current scan: area 0.50 (+25% growth)
        prev_rec, status, growth_rate, score, details = get_previous_and_classify(
            db, lat, lon, current_embedding=v, current_area=0.50
        )
        self.assertIsNotNone(prev_rec)
        self.assertEqual(prev_rec.defect_id, "base-defect-001")
        self.assertEqual(status, DefectStatus.WORSENING)
        self.assertAlmostEqual(growth_rate, 25.0, delta=0.1)
        self.assertTrue(score > MATCHING_THRESHOLD)

    def test_two_frame_second_capture_improving(self):
        # Current scan: area shrinks from 0.50 to 0.35 (-30%) -> Improving
        lat, lon = 28.6139, 77.2090
        v = [0.2] * 128
        norm = np.linalg.norm(v)
        v = (np.array(v) / norm).tolist()

        base_frame = DefectRecord(
            defect_id="base-defect-002",
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow() - timedelta(days=2),
            visual_embedding=v,
            bounding_box_area=0.50,
            status=DefectStatus.WORSENING,
            severity_score=0.7
        )
        db = MockSession(records=[base_frame])

        prev_rec, status, growth_rate, score, details = get_previous_and_classify(
            db, lat, lon, current_embedding=v, current_area=0.35
        )
        self.assertIsNotNone(prev_rec)
        self.assertEqual(status, DefectStatus.IMPROVING)
        self.assertAlmostEqual(growth_rate, -30.0, delta=0.1)

    def test_civil_engineering_advisory_and_pdf(self):
        advisory = analyze_civil_road_defect(
            latitude=28.6139,
            longitude=77.2090,
            status="Worsening",
            area_delta_pct=25.0,
            current_area=0.50,
            previous_area=0.40,
            time_delta_str="7d 0h ago",
            severity_score=0.8
        )
        self.assertIn("severity_level", advisory)
        self.assertIn("root_cause_analysis", advisory)
        self.assertIn("recommended_remediation", advisory)
        self.assertIn("municipal_priority_rank", advisory)

        pdf_buf = create_scantrail_pdf_report(
            defect_id="defect-test-123",
            lat=28.6139,
            lon=77.2090,
            status="Worsening",
            current_area=0.50,
            previous_area=0.40,
            growth_rate_pct=25.0,
            time_delta_str="7d 0h ago",
            scan_timestamp="2026-09-15 21:00:00 UTC",
            advisory=advisory
        )
        self.assertTrue(pdf_buf.getvalue().startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()

