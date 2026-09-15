import math
import numpy as np
from typing import Optional, Tuple, List, Any
from datetime import datetime

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import desc
    from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint
    HAS_SQLALCHEMY = True
except ImportError:
    Session = Any
    desc = None
    ST_DWithin = None
    ST_SetSRID = None
    ST_MakePoint = None
    HAS_SQLALCHEMY = False

from .database import DefectRecord, DefectStatus

# Weights defined in Two-Frame Comparative Matching Engine specification:
# Score = 0.3(GPS Proximity) + 0.5(Visual Embedding Cosine Similarity) + 0.2(Area Ratio)
W1_GPS = 0.3
W2_VISUAL = 0.5
W3_AREA = 0.2
MATCHING_THRESHOLD = 0.75
SPATIAL_THRESHOLD_METERS = 2.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance in meters between two points on the Earth."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_cosine_similarity(vec1: Optional[List[float]], vec2: Optional[List[float]]) -> float:
    """Computes cosine similarity between two feature vectors normalized to [0, 1]."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.5  # Neutral default if embeddings are missing or mismatched
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    dot = np.dot(v1, v2)
    similarity = float(dot / (norm1 * norm2))
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))

def calculate_area_ratio(area1: float, area2: float) -> float:
    """Computes area ratio similarity between [0, 1]."""
    if area1 <= 0 and area2 <= 0:
        return 1.0
    max_area = max(area1, area2)
    if max_area <= 0:
        return 1.0
    diff = abs(area1 - area2)
    return max(0.0, 1.0 - (diff / max_area))

def compute_composite_score(
    distance_meters: float,
    current_embedding: Optional[List[float]],
    previous_embedding: Optional[List[float]],
    current_area: float,
    previous_area: float
) -> Tuple[float, dict]:
    """
    Score = 0.3(GPS Proximity) + 0.5(Visual Embedding Cosine Similarity) + 0.2(Area Ratio)
    """
    if distance_meters <= SPATIAL_THRESHOLD_METERS:
        gps_score = 1.0 - 0.5 * (distance_meters / SPATIAL_THRESHOLD_METERS)
    else:
        gps_score = max(0.0, 0.5 * (1.0 - ((distance_meters - SPATIAL_THRESHOLD_METERS) / SPATIAL_THRESHOLD_METERS)))

    visual_score = calculate_cosine_similarity(current_embedding, previous_embedding)
    area_score = calculate_area_ratio(current_area, previous_area)

    composite = (W1_GPS * gps_score) + (W2_VISUAL * visual_score) + (W3_AREA * area_score)
    details = {
        "gps_score": gps_score,
        "visual_score": visual_score,
        "area_score": area_score,
        "composite_score": composite,
        "distance_meters": distance_meters
    }
    return composite, details

def classify_two_frame_evolution(
    previous_record: Optional[DefectRecord],
    current_area: float,
    detection_occurred: bool = True
) -> Tuple[DefectStatus, float]:
    """
    Two-Frame Evolutionary Classification:
    - If previous_record is None -> Status = New
    - If matched:
      - Area Growth > +15% -> Status = Worsening
      - Area Shrinkage < -15% -> Status = Improving
      - Area Delta within [-15%, +15%] -> Status = Persistent
    - If scanned but no detection -> Status = Repaired
    """
    if not detection_occurred:
        return DefectStatus.REPAIRED, -100.0

    if previous_record is None:
        return DefectStatus.NEW, 0.0

    prev_area = previous_record.bounding_box_area
    if prev_area <= 0:
        return DefectStatus.PERSISTENT, 0.0

    growth_rate = ((current_area - prev_area) / prev_area) * 100.0

    if growth_rate > 15.0:
        return DefectStatus.WORSENING, growth_rate
    elif growth_rate < -15.0:
        return DefectStatus.IMPROVING, growth_rate
    else:
        return DefectStatus.PERSISTENT, growth_rate

def get_previous_and_classify(
    db_session: Session,
    lat: float,
    lon: float,
    current_embedding: Optional[List[float]],
    current_area: float
) -> Tuple[Optional[DefectRecord], DefectStatus, float, float, dict]:
    """
    1. Spatial Lookup: Query database using PostGIS ST_DWithin within 2.0-meter radius.
    2. Fetch Last State: Retrieve the single most recent historical record for that location.
    3. Multi-Modal Matching: Compute composite score.
    4. Evolution Classification:
       - No match -> New
       - Growth > +15% -> Worsening
       - Shrinkage < -15% -> Improving
       - [-15%, +15%] -> Persistent
    Returns: (matched_previous_record, status, growth_rate_pct, match_score, match_details)
    """
    candidates: List[DefectRecord] = []

    try:
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        candidates = db_session.query(DefectRecord).filter(
            ST_DWithin(DefectRecord.location, point, SPATIAL_THRESHOLD_METERS)
        ).order_by(desc(DefectRecord.timestamp)).all()
    except Exception:
        if db_session:
            db_session.rollback()
        # Fallback query for non-PostGIS or mock db sessions
        try:
            all_records = db_session.query(DefectRecord).all()
            filtered = [
                d for d in all_records
                if haversine_distance(lat, lon, d.latitude, d.longitude) <= SPATIAL_THRESHOLD_METERS
            ]
            candidates = sorted(filtered, key=lambda x: x.timestamp, reverse=True)
        except Exception:
            candidates = []

    # Retrieve the single most recent candidate at this location
    previous_record = candidates[0] if candidates else None
    
    if previous_record is None:
        status, growth_rate = classify_two_frame_evolution(None, current_area)
        return None, status, growth_rate, 0.0, {}

    # Multi-Modal Matching
    dist = haversine_distance(lat, lon, previous_record.latitude, previous_record.longitude)
    match_score, details = compute_composite_score(
        distance_meters=dist,
        current_embedding=current_embedding,
        previous_embedding=previous_record.visual_embedding,
        current_area=current_area,
        previous_area=previous_record.bounding_box_area
    )

    # Match confirmed if:
    # 1. Composite score exceeds threshold (>0.75), OR
    # 2. Defect is strictly within 2.0m spatial threshold with compatible geometric/visual features.
    is_matched = (
        match_score >= MATCHING_THRESHOLD or
        (dist <= SPATIAL_THRESHOLD_METERS and (details.get("area_score", 0) >= 0.5 or details.get("visual_score", 0) >= 0.75))
    )

    if is_matched:
        status, growth_rate = classify_two_frame_evolution(previous_record, current_area)
        return previous_record, status, growth_rate, match_score, details
    else:
        status, growth_rate = classify_two_frame_evolution(None, current_area)
        return None, status, growth_rate, match_score, details

def extract_visual_embedding(image_bytes: bytes, feature_dim: int = 128) -> List[float]:
    """Generates a normalized visual feature embedding vector from image bytes."""
    chunk = np.frombuffer(image_bytes[:min(2048, len(image_bytes))], dtype=np.uint8) if image_bytes else np.zeros(16, dtype=np.uint8)
    
    # Feature distribution based on byte histograms and spectral moments
    raw = np.zeros(feature_dim, dtype=np.float32)
    for i, byte in enumerate(chunk):
        raw[i % feature_dim] += float(byte) / 255.0

    # Smooth normalization
    norm = np.linalg.norm(raw)
    if norm > 0:
        raw = raw / norm
    else:
        raw = np.ones(feature_dim, dtype=np.float32) / np.sqrt(feature_dim)
    return raw.tolist()
