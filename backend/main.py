import os
import uuid
from datetime import datetime
from typing import Optional, List, Any

try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
    from fastapi.responses import FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    from sqlalchemy.orm import Session
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    class FastAPI:
        def __init__(self, *args, **kwargs): pass
        def add_middleware(self, *args, **kwargs): pass
        def post(self, *args, **kwargs): return lambda f: f
        def get(self, *args, **kwargs): return lambda f: f
    class UploadFile: pass
    File = lambda *args, **kwargs: None
    Form = lambda *args, **kwargs: None
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail
    class BackgroundTasks: pass
    Depends = lambda f: None
    CORSMiddleware = None
    class FileResponse:
        def __init__(self, path, media_type=None, filename=None):
            self.path = path
            self.media_type = media_type
            self.filename = filename
    Session = Any

try:
    from geoalchemy2.elements import WKTElement
except ImportError:
    WKTElement = lambda geom, srid=4326: None

from .config import settings
from .database import get_db, DefectRecord, Survey, DefectStatus
from .spatial_engine import (
    get_previous_and_classify,
    extract_visual_embedding
)
from .services import (
    analyze_civil_road_defect,
    create_scantrail_pdf_report
)
from .mqtt_service import publish_mqtt_notification

app = FastAPI(
    title="ScanTrail Backend",
    description="Two-frame spatial-temporal road defect monitoring backend",
    version="2.1.0"
)

if HAS_FASTAPI:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.post("/scan/analyze")
async def scan_analyze(
    image: Any = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: Optional[str] = Form(None),
    bounding_box_area: float = Form(0.1),
    severity_score: float = Form(0.5),
    db: Any = Depends(get_db)
):
    """
    Accepts: image, latitude, longitude, timestamp, and bounding_box_area.
    - Runs spatial lookup against the last image at this location (within 2.0m).
    - Computes spatial-temporal classification (New, Persistent, Worsening, Improving, Repaired).
    - Runs Gemini civil analysis.
    - Saves new record to PostGIS.
    - Returns JSON containing spatial-temporal analysis metrics, structured advice, and PDF download URL.
    """
    try:
        image_bytes = await image.read()
        current_time = datetime.utcnow()
        if timestamp:
            try:
                current_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                current_time = datetime.utcnow()

        # Save uploaded image to disk for two-frame archival
        image_filename = f"scan_{uuid.uuid4().hex[:12]}_{getattr(image, 'filename', 'frame.jpg')}"
        saved_image_path = os.path.join(settings.TEMP_UPLOADS_DIR, image_filename)
        with open(saved_image_path, "wb") as f:
            f.write(image_bytes)

        # 1. Feature extraction
        visual_embedding = extract_visual_embedding(image_bytes)

        # 2. Two-Frame Comparative Matching Engine
        previous_record, status, growth_rate, match_score, match_details = get_previous_and_classify(
            db_session=db,
            lat=latitude,
            lon=longitude,
            current_embedding=visual_embedding,
            current_area=bounding_box_area
        )

        previous_area = previous_record.bounding_box_area if previous_record else None
        time_delta_str = "Initial Scan (Base Frame)"
        if previous_record and previous_record.timestamp:
            delta = current_time - previous_record.timestamp
            days = delta.days
            hours, rem = divmod(delta.seconds, 3600)
            minutes, _ = divmod(rem, 60)
            if days > 0:
                time_delta_str = f"{days}d {hours}h ago"
            elif hours > 0:
                time_delta_str = f"{hours}h {minutes}m ago"
            else:
                time_delta_str = f"{minutes}m ago"

        # 3. Generative Civil AI Advisory (Gemini 1.5 Flash)
        advisory = analyze_civil_road_defect(
            latitude=latitude,
            longitude=longitude,
            status=status.value,
            area_delta_pct=growth_rate,
            current_area=bounding_box_area,
            previous_area=previous_area,
            time_delta_str=time_delta_str,
            severity_score=severity_score
        )

        # 4. Save current entry to DB as latest reference frame for future scans
        new_defect_id = str(uuid.uuid4())
        location_point = None
        try:
            location_point = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        except Exception:
            pass

        new_record = DefectRecord(
            defect_id=new_defect_id,
            location=location_point,
            latitude=latitude,
            longitude=longitude,
            timestamp=current_time,
            visual_embedding=visual_embedding,
            bounding_box_area=bounding_box_area,
            status=status,
            severity_score=severity_score,
            image_path=saved_image_path
        )
        if db:
            db.add(new_record)
            db.commit()

        # 5. Render ReportLab PDF Report
        pdf_buf = create_scantrail_pdf_report(
            defect_id=new_defect_id,
            lat=latitude,
            lon=longitude,
            status=status.value,
            current_area=bounding_box_area,
            previous_area=previous_area,
            growth_rate_pct=growth_rate,
            time_delta_str=time_delta_str,
            scan_timestamp=current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            advisory=advisory
        )
        report_filename = f"ScanTrail_Report_{new_defect_id}.pdf"
        report_path = os.path.join(settings.REPORTS_DIR, report_filename)
        with open(report_path, "wb") as f:
            f.write(pdf_buf.getvalue())

        return {
            "defect_id": new_defect_id,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current_time.isoformat(),
            "evolution_status": status.value,
            "area_change_percentage": round(growth_rate, 2),
            "current_area": bounding_box_area,
            "previous_area": previous_area,
            "time_delta_str": time_delta_str,
            "severity_score": severity_score,
            "severity_level": advisory.get("severity_level", "Medium"),
            "engineering_analysis": advisory,
            "pdf_report_url": f"/reports/{new_defect_id}"
        }

    except Exception as e:
        if db:
            db.rollback()
        print(f"Error processing defect scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Serves the generated PDF file."""
    report_path = os.path.join(settings.REPORTS_DIR, f"ScanTrail_Report_{report_id}.pdf")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found or not yet generated.")
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"ScanTrail_Report_{report_id}.pdf"
    )
