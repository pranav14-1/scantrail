import os

# Try loading .env if python-dotenv is present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Settings:
    PROJECT_NAME: str = "ScanTrail Road Defect Tracking System"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/scantrail_db"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MQTT_HOSTNAME: str = os.getenv("MQTT_HOSTNAME", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", 1883))
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")
    
    TEMP_UPLOADS_DIR: str = os.getenv("TEMP_UPLOADS_DIR", "temp_uploads")
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "reports")

settings = Settings()

os.makedirs(settings.TEMP_UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)

