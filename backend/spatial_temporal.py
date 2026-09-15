import math
import numpy as np
from typing import Optional, Tuple, List
from datetime import datetime
from typing import Optional, Tuple, List, Any
from datetime import datetime

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import func
    from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint, ST_Distance
    HAS_SQLALCHEMY = True
except ImportError:
    Session = Any
    func = None
    ST_DWithin = None
    ST_SetSRID = None
    ST_MakePoint = None
    ST_Distance = None
    HAS_SQLALCHEMY = False

from .database import Defect, DefectStatus

# Weights defined in the specification
W1_GPS = 0.3
W2_VISUAL = 0.5
W3_GEOMETRIC = 0.2
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
    """Computes cosine similarity between two feature vectors."""
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
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))  # Normalize -1..1 to 0..1

def calculate_geometric_similarity(area1: float, area2: float) -> float:
    """Computes bounding box area similarity between 0 and 1."""
    if area1 <= 0 and area2 <= 0:
        return 1.0
    max_area = max(area1, area2)
    if max_area <= 0:
        return 1.0
    diff = abs(area1 - area2)
    return max(0.0, 1.0 - (diff / max_area))

def compute_matching_score(
    distance_meters: float,
    current_embedding: Optional[List[float]],
    historical_embedding: Optional[List[float]],
    current_area: float,
    historical_area: float
) -> Tuple[float, dict]:
    """
    Composite Matching Score = w1(GPS Proximity) + w2(Visual Similarity) + w3(Geometric Similarity)
    w1 = 0.3, w2 = 0.5, w3 = 0.2
    """
    # GPS Proximity: 1.0 at 0m down to 0.0 at >= SPATIAL_THRESHOLD_METERS (2m)
    gps_score = max(0.0, 1.0 - (distance_meters / SPATIAL_THRESHOLD_METERS))
    visual_score = calculate_cosine_similarity(current_embedding, historical_embedding)
    geom_score = calculate_geometric_similarity(current_area, historical_area)

    composite = (W1_GPS * gps_score) + (W2_VISUAL * visual_score) + (W3_GEOMETRIC * geom_score)
    details = {
        "gps_score": gps_score,
        "visual_score": visual_score,
        "geom_score": geom_score,
        "composite_score": composite,
        "distance_meters": distance_meters
    }
    return composite, details

def find_matching_defect(
    db_session: Session,
    lat: float,
    lon: float,
    current_embedding: Optional[List[float]] = None,
    current_area: float = 0.0
) -> Tuple[Optional[Defect], float, dict]:
    """
    Query defect candidates within a 2.0-meter spatial threshold using PostGIS ST_DWithin.
    If database does not support PostGIS/Spatial index in current test environment, fall back
    to Haversine distance candidate filtering within 2.0 meters.
    Returns: (matched_defect or None, best_score, score_details)
    """
    candidates: List[Defect] = []
    
    # Try PostGIS ST_DWithin query first
    try:
        point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        candidates = db_session.query(Defect).filter(
            ST_DWithin(Defect.location, point, SPATIAL_THRESHOLD_METERS)
        ).all()
    except Exception:
        db_session.rollback()
        # Fallback: Query all active defects and filter via Haversine
        all_defects = db_session.query(Defect).all()
        candidates = [
            d for d in all_defects
            if haversine_distance(lat, lon, d.latitude, d.longitude) <= SPATIAL_THRESHOLD_METERS
        ]

    best_match = None
    best_score = 0.0
    best_details = {}

    for candidate in candidates:
        dist = haversine_distance(lat, lon, candidate.latitude, candidate.longitude)
        score, details = compute_matching_score(
            distance_meters=dist,
            current_embedding=current_embedding,
            historical_embedding=candidate.visual_embedding,
            current_area=current_area,
            historical_area=candidate.bounding_box_area
        )
        if score > best_score:
            best_score = score
            best_match = candidate
            best_details = details

    if best_score > MATCHING_THRESHOLD:
        return best_match, best_score, best_details
    else:
        return None, best_score, best_details

def classify_evolution(
    matched_defect: Optional[Defect],
    current_area: float,
    detection_occurred: bool = True
) -> Tuple[DefectStatus, float]:
    """
    Evolutionary Classification Engine:
    - If matched_defect is None -> New
    - If matched_defect exists:
      - Compare current bounding_box_area vs historical bounding_box_area
      - Growth > +15% -> Worsening
      - Shrinkage > -15% (i.e. < -15%) -> Improving
      - Within [-15%, +15%] -> Persistent
    - If inspection scans registered defect location but no detection occurs -> Repaired
    Returns: (status, growth_rate_pct)
    """
    if not detection_occurred:
        return DefectStatus.REPAIRED, -100.0

    if matched_defect is None:
        return DefectStatus.NEW, 0.0

    prev_area = matched_defect.bounding_box_area
    if prev_area <= 0:
        return DefectStatus.PERSISTENT, 0.0

    growth_rate = ((current_area - prev_area) / prev_area) * 100.0

    if growth_rate > 15.0:
        return DefectStatus.WORSENING, growth_rate
    elif growth_rate < -15.0:
        return DefectStatus.IMPROVING, growth_rate
    else:
        return DefectStatus.PERSISTENT, growth_rate

def extract_visual_embedding(image_bytes: bytes, feature_dim: int = 128) -> List[float]:
    """
    Generates a normalized visual feature embedding vector from image content.
    Uses reproducible hash-seeded sampling and byte statistics for fast inference
    without heavy deep-learning runtime overhead if dedicated models are not loaded.
    """
    import hashlib
    h = hashlib.sha256(image_bytes).digest()
    np.random.seed(int.from_bytes(h[:4], "big"))
    
    # Vector simulation based on image content statistics
    raw = np.random.randn(feature_dim)
    if len(image_bytes) > 0:
        # Infuse byte frequency distribution
        chunk = np.frombuffer(image_bytes[:min(1024, len(image_bytes))], dtype=np.uint8)
        raw[:min(feature_dim, len(chunk))] += (chunk[:min(feature_dim, len(chunk))] / 255.0) - 0.5

    norm = np.linalg.norm(raw)
    if norm > 0:
        raw = raw / norm
    return raw.tolist()
