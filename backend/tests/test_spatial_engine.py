import unittest
import numpy as np
from datetime import datetime, timedelta
from backend.database import DefectRecord, DefectStatus
from backend.spatial_engine import (
    get_previous_and_classify,
    classify_two_frame_evolution,
    haversine_distance,
    MATCHING_THRESHOLD,
    SPATIAL_THRESHOLD_METERS
)

class MockQuery:
    def __init__(self, records):
        self.records = records

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        # Order by timestamp descending
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

class TestSpatialEngineBoundariesAndTemporalChain(unittest.TestCase):

    def setUp(self):
        # Normal feature embedding for defect testing
        v = [0.1] * 128
        norm = np.linalg.norm(v)
        self.embedding = (np.array(v) / norm).tolist()

    def test_proximity_boundary_within_threshold_1_8m(self):
        """
        Proximity Boundary Test:
        Prior defect at (28.6139, 77.2090).
        Query at 1.8m distance -> Must match prior defect frame.
        """
        lat0, lon0 = 28.6139, 77.2090
        # Latitude shift of ~0.000016 degrees is approx 1.78 meters
        # delta_lat = distance / 111139 meters
        lat_1_8m = lat0 + (1.8 / 111139.0)
        lon_1_8m = lon0
        actual_dist = haversine_distance(lat0, lon0, lat_1_8m, lon_1_8m)
        self.assertAlmostEqual(actual_dist, 1.8, delta=0.05)
        self.assertLess(actual_dist, SPATIAL_THRESHOLD_METERS)

        prior_record = DefectRecord(
            defect_id="defect-prior-001",
            latitude=lat0,
            longitude=lon0,
            timestamp=datetime(2026, 9, 15, 10, 0, 0),
            visual_embedding=self.embedding,
            bounding_box_area=0.30,
            status=DefectStatus.NEW,
            severity_score=0.5
        )
        db = MockDBSession([prior_record])

        matched, status, growth, score, details = get_previous_and_classify(
            db_session=db,
            lat=lat_1_8m,
            lon=lon_1_8m,
            current_embedding=self.embedding,
            current_area=0.30
        )

        self.assertIsNotNone(matched)
        self.assertEqual(matched.defect_id, "defect-prior-001")
        self.assertTrue(score > MATCHING_THRESHOLD)
        self.assertEqual(status, DefectStatus.PERSISTENT)

    def test_proximity_boundary_outside_threshold_2_2m(self):
        """
        Proximity Boundary Test:
        Prior defect at (28.6139, 77.2090).
        Query at 2.2m distance (> 2.0m threshold) -> Must return None and classify as New.
        """
        lat0, lon0 = 28.6139, 77.2090
        lat_2_2m = lat0 + (2.2 / 111139.0)
        lon_2_2m = lon0
        actual_dist = haversine_distance(lat0, lon0, lat_2_2m, lon_2_2m)
        self.assertAlmostEqual(actual_dist, 2.2, delta=0.05)
        self.assertGreater(actual_dist, SPATIAL_THRESHOLD_METERS)

        prior_record = DefectRecord(
            defect_id="defect-prior-002",
            latitude=lat0,
            longitude=lon0,
            timestamp=datetime(2026, 9, 15, 10, 0, 0),
            visual_embedding=self.embedding,
            bounding_box_area=0.30,
            status=DefectStatus.NEW,
            severity_score=0.5
        )
        db = MockDBSession([prior_record])

        matched, status, growth, score, details = get_previous_and_classify(
            db_session=db,
            lat=lat_2_2m,
            lon=lon_2_2m,
            current_embedding=self.embedding,
            current_area=0.30
        )

        self.assertIsNone(matched)
        self.assertEqual(status, DefectStatus.NEW)
        self.assertEqual(growth, 0.0)

    def test_temporal_chain_two_frame_strictly_last_rule(self):
        """
        Temporal Chain Verification (Two-Frame Strictly Last Rule):
        - Insert Frame 1 (10:00 AM, Area = 0.20m²).
        - Insert Frame 2 (11:00 AM, Area = 0.30m²).
        - Query Frame 3 (12:00 PM, Area = 0.35m²).
        Assert: Matching engine compares Frame 3 against Frame 2 only
        (Area Delta = (0.35 - 0.30)/0.30 = +16.67% -> Worsening). Verify it ignores Frame 1.
        """
        lat, lon = 28.6139, 77.2090

        frame_1 = DefectRecord(
            defect_id="frame-1-10am",
            latitude=lat,
            longitude=lon,
            timestamp=datetime(2026, 9, 15, 10, 0, 0),
            visual_embedding=self.embedding,
            bounding_box_area=0.20,
            status=DefectStatus.NEW,
            severity_score=0.4
        )
        frame_2 = DefectRecord(
            defect_id="frame-2-11am",
            latitude=lat,
            longitude=lon,
            timestamp=datetime(2026, 9, 15, 11, 0, 0),
            visual_embedding=self.embedding,
            bounding_box_area=0.30,
            status=DefectStatus.WORSENING,
            severity_score=0.6
        )

        # In DB, both frames exist at this location
        db = MockDBSession([frame_1, frame_2])

        # Query Frame 3 at 12:00 PM with area = 0.35m²
        matched, status, growth, score, details = get_previous_and_classify(
            db_session=db,
            lat=lat,
            lon=lon,
            current_embedding=self.embedding,
            current_area=0.35
        )

        # Assert matching against Frame 2 ONLY
        self.assertIsNotNone(matched)
        self.assertEqual(matched.defect_id, "frame-2-11am")
        self.assertNotEqual(matched.defect_id, "frame-1-10am")
        self.assertEqual(matched.bounding_box_area, 0.30)
        
        # Expected growth: (0.35 - 0.30) / 0.30 * 100 = 16.666...%
        expected_growth = ((0.35 - 0.30) / 0.30) * 100.0
        self.assertAlmostEqual(growth, expected_growth, delta=0.01)
        self.assertEqual(status, DefectStatus.WORSENING)

    def test_classification_threshold_matrix(self):
        """
        Classification Threshold Matrix:
        - Test Area Delta = +16% -> Assert Worsening (> +15%)
        - Test Area Delta = +14% -> Assert Persistent (<= +15%)
        - Test Area Delta = -14% -> Assert Persistent (>= -15%)
        - Test Area Delta = -16% -> Assert Improving (< -15%)
        """
        prev = DefectRecord(
            defect_id="threshold-base",
            latitude=28.6139,
            longitude=77.2090,
            timestamp=datetime.utcnow(),
            bounding_box_area=1.00
        )

        # Delta = +16% (current = 1.16)
        status_plus_16, rate_plus_16 = classify_two_frame_evolution(prev, current_area=1.16)
        self.assertEqual(status_plus_16, DefectStatus.WORSENING)
        self.assertAlmostEqual(rate_plus_16, 16.0, delta=0.01)

        # Delta = +14% (current = 1.14)
        status_plus_14, rate_plus_14 = classify_two_frame_evolution(prev, current_area=1.14)
        self.assertEqual(status_plus_14, DefectStatus.PERSISTENT)
        self.assertAlmostEqual(rate_plus_14, 14.0, delta=0.01)

        # Delta = -14% (current = 0.86)
        status_minus_14, rate_minus_14 = classify_two_frame_evolution(prev, current_area=0.86)
        self.assertEqual(status_minus_14, DefectStatus.PERSISTENT)
        self.assertAlmostEqual(rate_minus_14, -14.0, delta=0.01)

        # Delta = -16% (current = 0.84)
        status_minus_16, rate_minus_16 = classify_two_frame_evolution(prev, current_area=0.84)
        self.assertEqual(status_minus_16, DefectStatus.IMPROVING)
        self.assertAlmostEqual(rate_minus_16, -16.0, delta=0.01)

if __name__ == "__main__":
    unittest.main()

