"""
ScanTrail (formerly AgriSense backend)
Spatial-Temporal Road Defect Tracking System
Entrypoint exposing the refactored ScanTrail FastAPI application.
"""
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backendfilemain:app", host="0.0.0.0", port=8000, reload=True)
