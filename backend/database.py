import uuid
from datetime import datetime
from enum import Enum
from .config import settings

class DefectStatus(str, Enum):
    NEW = "New"
    PERSISTENT = "Persistent"
    WORSENING = "Worsening"
    IMPROVING = "Improving"
    REPAIRED = "Repaired"

try:
    from sqlalchemy import (
        create_engine,
        Column,
        String,
        Float,
        DateTime,
        JSON,
        Enum as SQLEnum,
    )
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    from sqlalchemy.orm import declarative_base, sessionmaker
    from geoalchemy2 import Geometry

    Base = declarative_base()

    class Survey(Base):
        __tablename__ = "surveys"

        survey_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
        rover_id = Column(String, nullable=False, index=True)

    class DefectRecord(Base):
        __tablename__ = "defects"

        defect_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
        latitude = Column(Float, nullable=False)
        longitude = Column(Float, nullable=False)
        timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
        visual_embedding = Column(JSON, nullable=True)  # ARRAY of floats / JSON
        bounding_box_area = Column(Float, nullable=False, default=0.0)
        status = Column(
            SQLEnum(DefectStatus, name="defect_status_enum", values_callable=lambda obj: [e.value for e in obj]),
            default=DefectStatus.NEW,
            nullable=False,
        )
        severity_score = Column(Float, default=0.0, nullable=False)
        image_path = Column(String, nullable=True)

    # Maintain Defect as an alias for DefectRecord
    Defect = DefectRecord

    engine = None
    SessionLocal = None

    def init_db():
        global engine, SessionLocal
        try:
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except Exception as e:
            print(f"Warning: Could not initialize database engine with URL {settings.DATABASE_URL}: {e}")

    init_db()

    def get_db():
        if SessionLocal is None:
            init_db()
        if SessionLocal is None:
            raise RuntimeError("Database engine not configured or unavailable.")
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

except ImportError:
    # Minimal fallback objects if SQLAlchemy / GeoAlchemy2 are pending installation
    Base = None
    engine = None
    SessionLocal = None

    class Survey:
        def __init__(self, survey_id=None, rover_id="rover-01", timestamp=None):
            self.survey_id = survey_id or str(uuid.uuid4())
            self.rover_id = rover_id
            self.timestamp = timestamp or datetime.utcnow()

    class DefectRecord:
        def __init__(
            self,
            defect_id=None,
            location=None,
            latitude=0.0,
            longitude=0.0,
            timestamp=None,
            visual_embedding=None,
            bounding_box_area=0.0,
            status=DefectStatus.NEW,
            severity_score=0.0,
            image_path=None,
        ):
            self.defect_id = defect_id or str(uuid.uuid4())
            self.location = location
            self.latitude = latitude
            self.longitude = longitude
            self.timestamp = timestamp or datetime.utcnow()
            self.visual_embedding = visual_embedding
            self.bounding_box_area = bounding_box_area
            self.status = status
            self.severity_score = severity_score
            self.image_path = image_path

    Defect = DefectRecord

    def get_db():
        yield None
