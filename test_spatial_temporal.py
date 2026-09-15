import unittest
import numpy as np
from backend.spatial_temporal import (
    haversine_distance,
    calculate_cosine_similarity,
    calculate_geometric_similarity,
    compute_matching_score,
    classify_evolution,
    extract_visual_embedding,
    MATCHING_THRESHOLD
)
from backend.database import DefectStatus

class MockDefect:
    def __init__(self, bounding_box_area, visual_embedding=None):
        self.bounding_box_area = bounding_box_area
        self.visual_embedding = visual_embedding

class TestSpatialTemporalEngine(unittest.TestCase):

    def test_haversine_distance(self):
        # Coordinates approx 111 meters apart in latitude (0.001 deg ~ 111m)
        dist = haversine_distance(28.6139, 77.2090, 28.6149, 77.2090)
        self.assertAlmostEqual(dist, 111.19, delta=5.0)

        # Same point distance should be 0
        dist_same = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
        self.assertEqual(dist_same, 0.0)

    def test_cosine_similarity(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [1.0, 0.0, 0.0]
        # Identical vectors normalized to 1.0
        self.assertAlmostEqual(calculate_cosine_similarity(v1, v2), 1.0, delta=1e-4)

        # Orthogonal vectors normalized to 0.5
        v3 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(calculate_cosine_similarity(v1, v3), 0.5, delta=1e-4)

    def test_geometric_similarity(self):
        # Identical areas
        self.assertAlmostEqual(calculate_geometric_similarity(0.5, 0.5), 1.0)
        # Differing areas: diff = 0.25, max = 0.5 -> similarity = 1 - (0.25/0.5) = 0.5
        self.assertAlmostEqual(calculate_geometric_similarity(0.5, 0.25), 0.5)

    def test_composite_matching_score(self):
        v = [0.5, 0.5]
        # Exact match at 0m distance, identical embedding, identical area
        score, details = compute_matching_score(
            distance_meters=0.0,
            current_embedding=v,
            historical_embedding=v,
            current_area=0.4,
            historical_area=0.4
        )
        # Expected: 0.3*1.0 + 0.5*1.0 + 0.2*1.0 = 1.0
        self.assertAlmostEqual(score, 1.0, delta=1e-4)
        self.assertTrue(score > MATCHING_THRESHOLD)

        # Divergent match at 2.5m (> 2.0m threshold -> gps_score = 0)
        score_far, details_far = compute_matching_score(
            distance_meters=2.5,
            current_embedding=[1.0, 0.0],
            historical_embedding=[0.0, 1.0],
            current_area=0.8,
            historical_area=0.1
        )
        # Visual sim: 0.5, Geometric sim: 1 - 0.7/0.8 = 0.125
        # Total = 0.3*0 + 0.5*0.5 + 0.2*0.125 = 0.25 + 0.025 = 0.275
        self.assertTrue(score_far < MATCHING_THRESHOLD)

    def test_evolutionary_classification(self):
        # Test 1: No match -> New
        status, rate = classify_evolution(None, current_area=0.2)
        self.assertEqual(status, DefectStatus.NEW)
        self.assertEqual(rate, 0.0)

        # Test 2: Growth > +15% -> Worsening
        prev = MockDefect(bounding_box_area=0.2)
        status, rate = classify_evolution(prev, current_area=0.25) # +25%
        self.assertEqual(status, DefectStatus.WORSENING)
        self.assertAlmostEqual(rate, 25.0)

        # Test 3: Shrinkage < -15% -> Improving
        status, rate = classify_evolution(prev, current_area=0.15) # -25%
        self.assertEqual(status, DefectStatus.IMPROVING)
        self.assertAlmostEqual(rate, -25.0)

        # Test 4: Within [-15%, +15%] -> Persistent
        status, rate = classify_evolution(prev, current_area=0.21) # +5%
        self.assertEqual(status, DefectStatus.PERSISTENT)
        self.assertAlmostEqual(rate, 5.0)

        # Test 5: Repaired (no detection occurred)
        status, rate = classify_evolution(prev, current_area=0.0, detection_occurred=False)
        self.assertEqual(status, DefectStatus.REPAIRED)

    def test_visual_embedding_extraction(self):
        img1 = b"test_jpeg_bytes_for_defect_1"
        emb1 = extract_visual_embedding(img1, feature_dim=64)
        self.assertEqual(len(emb1), 64)
        norm = np.linalg.norm(emb1)
        self.assertAlmostEqual(norm, 1.0, delta=1e-4)

if __name__ == "__main__":
    unittest.main()

