# ScanTrail: AI-Based Road Surveillance & Spatial-Temporal Defect Change Detection

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791.svg)](https://postgis.net/)
[![Flutter](https://img.shields.io/badge/Flutter-3.9%2B-02569B.svg)](https://flutter.dev/)
[![Gemini 1.5 Flash](https://img.shields.io/badge/Google%20Gemini-1.5%20Flash-4285F4.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## System Abstract

Traditional road maintenance systems rely on single-pass, snapshot computer vision that detects potholes or surface cracks in isolation without temporal context. Consequently, municipal engineers cannot differentiate between newly formed defects and chronic, rapidly deteriorating structural failures.

**ScanTrail** is an AI-driven, multi-visit spatial-temporal road defect surveillance and change-detection system. By combining high-precision geodetic RTK/GPS telemetry, a PostGIS geospatial database, and multi-modal feature vector comparisons, ScanTrail matches newly photographed road defects against prior survey passes. 

Using a **Two-Frame Comparative Engine**, the system strictly evaluates the current defect geometry against the single most recent historical record at that exact coordinate ($\le 2.0\,\text{m}$ radius), classifying defects into five lifecycle states: **New**, **Persistent**, **Worsening**, **Improving**, or **Repaired**. The system then leverages **Google Gemini 1.5 Flash** for civil infrastructure root-cause analysis and automatically generates municipal-grade, two-page **ReportLab PDF audit reports** compliant with ASTM D6433 road evaluation standards.

---

## Key Architecture & Technical Highlights

```
+-----------------------------------------------------------------------------------+
|                           Mobile Rover / Field Surveyor                           |
|      (High-Accuracy GPS Telemetry + High-Resolution Pavement Defect Imagery)      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v  [POST /scan/analyze]
+-----------------------------------------------------------------------------------+
|                                FastAPI Backend                                    |
|  1. Visual Feature Vector Extraction (Normalized 128-d spectral histogram)        |
|  2. PostGIS Candidate Search: ST_DWithin(location, ST_MakePoint, 2.0 meters)      |
|  3. Fetch Single Most Recent Historical Entry (Strict Two-Frame Sequence)         |
+--------------------+------------------------------------+-------------------------+
                     |                                    |
                     v                                    v
+---------------------------------------+  +----------------------------------------+
|    Two-Frame Multi-Modal Matcher      |  |    Evolutionary State Classification   |
| Composite Matching Score Threshold    |  | Area Growth > +15%  --> Worsening      |
| Match if Score >= 0.75                |  | Area Shrink < -15%  --> Improving      |
| or within 2.0m with feature cohesion  |  | Delta in [-15%,15%] --> Persistent     |
+---------------------------------------+  | No Previous Match   --> New            |
                     |                     +-------------------+--------------------+
                     |                                         |
                     +--------------------+--------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         Generative AI & Municipal Reporting                       |
|  1. Google Gemini 1.5 Flash: Civil Engineering Advisory (Root Cause, Priority)    |
|  2. ReportLab PDF Engine: 2-Page AASHTO/ASTM Pavement Condition Certificate       |
|  3. PostGIS DefectRecord State Update (Acts as Base Frame for Next Survey)        |
+-----------------------------------------------------------------------------------+
```

### 1. Two-Frame Comparative Matching Engine
ScanTrail enforces a **strictly sequential temporal comparison**:
- Whenever an image is uploaded with GPS coordinates $(x, y)$, the spatial query inspects a circular buffer of radius $R = 2.0\,\text{m}$ around $(x, y)$ in the PostGIS database.
- It retrieves all previous visits and selects the **single most recent record** (ordered by `timestamp DESC`).
- It evaluates the composite matching score to confirm that the current camera capture represents the same physical defect.

### 2. Multi-Modal Composite Matching Formula
The candidate matching engine evaluates spatial proximity, visual feature similarity, and geometric area consistency using the weighted composite equation:

$$\text{Matching Score} = 0.3(\text{GPS Proximity}) + 0.5(\text{Visual Embedding Cosine Similarity}) + 0.2(\text{Area Ratio})$$

Where:
- **$\text{GPS Proximity}$**: Scaled smoothly inside the $2.0\,\text{m}$ threshold:
  $$\text{GPS Proximity} = 1.0 - 0.5 \left(\frac{\text{Distance}}{2.0}\right)$$
- **$\text{Visual Embedding Cosine Similarity}$**: Cosine similarity between normalized 128-dimensional image feature vectors $\vec{v}_1$ and $\vec{v}_2$:
  $$\text{Cosine Similarity} = \frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}$$
- **$\text{Area Ratio}$**: Dimensional consistency between present bounding area $A_{\text{curr}}$ and previous bounding area $A_{\text{prev}}$:
  $$\text{Area Ratio} = 1.0 - \frac{|A_{\text{curr}} - A_{\text{prev}}|}{\max(A_{\text{curr}}, A_{\text{prev}})}$$

### 3. Evolutionary Classification Rules
Once a physical defect match is verified against the immediately preceding frame, the system computes the percentage area expansion delta:

$$\Delta\% = \left(\frac{A_{\text{curr}} - A_{\text{prev}}}{A_{\text{prev}}}\right) \times 100\%$$

| Evolution State | Decision Rule | Recommended Municipal Action |
| :---: | :--- | :--- |
| <span style="color:#1976D2; font-weight:bold;">New</span> | First-time defect logged at geodetic coordinates ($\le 2.0\,\text{m}$ radius). | Initial baseline established; schedule routine monitoring. |
| <span style="color:#D32F2F; font-weight:bold;">Worsening</span> | Defect area growth $\Delta\% > +15.0\%$. | **Priority Work-Order**: Severe subgrade water intrusion or structural fatigue. Dispatch patching crew. |
| <span style="color:#388E3C; font-weight:bold;">Improving</span> | Defect area shrinkage $\Delta\% < -15.0\%$. | Surface stabilization or partial patch settling; verify compaction. |
| <span style="color:#FBC02D; font-weight:bold;">Persistent</span> | Defect area delta within $[-15.0\%, +15.0\%]$. | Defect dimensions stable; monitor during subsequent inspection cycle. |
| <span style="color:#757575; font-weight:bold;">Repaired</span> | Previous defect coordinate inspected with zero defect detection. | Mark asset restored; archive historical progression record. |

---

## Tech Stack Overview

### Backend & AI Infrastructure
- **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous Python 3.10+)
- **Spatial Database**: [PostgreSQL 15](https://www.postgresql.org/) with [PostGIS 3.3](https://postgis.net/) extension
- **Spatial ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [GeoAlchemy2](https://geoalchemy-2.readthedocs.io/)
- **Civil AI Advisory**: [Google Gemini 1.5 Flash](https://ai.google.dev/) via `google-generativeai`
- **PDF Generation Engine**: [ReportLab](https://www.reportlab.com/) (Vector canvas rendering, 2-page engineering audit certificate)
- **IoT & Telemetry Messaging**: [Paho-MQTT](https://eclipse.dev/paho/)

### Mobile Application
- **Framework**: [Flutter](https://flutter.dev/) (Dart 3.9+)
- **Location Services**: [Geolocator](https://pub.dev/packages/geolocator) (High-accuracy GPS telemetry capture)
- **Mapping**: [Flutter Map](https://pub.dev/packages/flutter_map) & [LatLong2](https://pub.dev/packages/latlong2)
- **State Management**: [Provider](https://pub.dev/packages/provider)
- **Document Viewing**: [Open File](https://pub.dev/packages/open_file) & [Path Provider](https://pub.dev/packages/path_provider)

---

## Step-by-Step Local Setup & Execution Guide

### Prerequisites
Before getting started, ensure you have the following installed on your machine:
- **Git** (`git --version`)
- **Python 3.10+** (`python3 --version`)
- **Flutter SDK 3.9+** (`flutter --version`)
- **PostgreSQL 14+ with PostGIS Extension** (or [Docker Desktop](https://www.docker.com/products/docker-desktop/))

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/YourUsername/ScanTrail.git
cd ScanTrail
```

---

### Step 2: Backend Setup (FastAPI + PostGIS)

#### Option A: Quickstart with Docker Compose (Recommended)
You can launch both the PostGIS database and the FastAPI service with a single command:

```bash
# 1. Copy environment variable template
cp .env.example .env

# 2. Add your Google Gemini API key to .env
# GEMINI_API_KEY=AIzaSy...

# 3. Start containers
docker compose up --build
```
The FastAPI backend will be live at `http://localhost:8000`.

---

#### Option B: Manual Local Setup

1. **Navigate to project root and create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate       # On Windows: venv\Scripts\activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://postgres:postgrespassword@localhost:5432/scantrail_db
   GEMINI_API_KEY=your_gemini_api_key_here
   MQTT_HOSTNAME=localhost
   MQTT_PORT=1883
   TEMP_UPLOADS_DIR=temp_uploads
   REPORTS_DIR=reports
   ```

4. **Initialize PostGIS Database**:
   In your PostgreSQL shell (`psql`):
   ```sql
   CREATE DATABASE scantrail_db;
   \c scantrail_db
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

5. **Start the FastAPI Server**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Interactive Swagger API documentation is available at `http://localhost:8000/docs`.

---

### Step 3: Frontend Setup (Flutter Mobile App)

1. **Open a new terminal window and navigate to the project directory**:
   ```bash
   cd /path/to/ScanTrail
   ```

2. **Install Flutter packages**:
   ```bash
   flutter pub get
   ```

3. **Configure the API Endpoint**:
   Open [`lib/services/api_service.dart`](lib/services/api_service.dart) and set `baseUrl` according to your test environment:
   ```dart
   // For Android Emulator:
   static const String baseUrl = "http://10.0.2.2:8000";

   // For iOS Simulator or Desktop:
   static const String baseUrl = "http://localhost:8000";

   // For physical device over Wi-Fi:
   static const String baseUrl = "http://192.168.x.x:8000";
   ```

4. **Launch the App**:
   ```bash
   # Check connected devices / emulators
   flutter devices

   # Run on connected target
   flutter run
   ```

---

## Automated Testing & Verification Suite

ScanTrail includes complete, non-manual regression and edge-case test suites. Run these commands to verify the entire system before evaluations or presentations:

### 1. Backend Spatial-Temporal & E2E Test Suite
Executes proximity boundary tests ($1.8\,\text{m}$ vs $2.2\,\text{m}$), temporal chain sequence rules, threshold matrix tests, Gemini civil AI mocking, and PDF validation:

```bash
# Run backend test suite
python3 -m unittest discover -s backend/tests -p "test_*.py" -v
```

**Expected Result**:
```
test_scan_analyze_endpoint_and_schema (test_api_and_pdf.TestApiAndPdfServiceMocking) ... ok
test_complete_spatial_temporal_lifecycle (test_e2e_spatial_temporal.TestE2ESpatialTemporalWorkflow) ... ok
test_classification_threshold_matrix (test_spatial_engine.TestSpatialEngineBoundariesAndTemporalChain) ... ok
test_proximity_boundary_outside_threshold_2_2m (test_spatial_engine.TestSpatialEngineBoundariesAndTemporalChain) ... ok
test_proximity_boundary_within_threshold_1_8m (test_spatial_engine.TestSpatialEngineBoundariesAndTemporalChain) ... ok
test_temporal_chain_two_frame_strictly_last_rule (test_spatial_engine.TestSpatialEngineBoundariesAndTemporalChain) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.061s

OK
```

### 2. Full Regression Suite
```bash
python3 -m unittest discover -p "test_*.py" -v
```

### 3. Flutter Unit & Widget Tests
Verifies JSON deserialization across all 5 evolution states and validates widget rendering of status badges, expansion deltas, and civil AI recommendation cards:

```bash
flutter test test/widget_test.dart
```

---

## Repository Structure

```
ScanTrail/
├── backend/
│   ├── Dockerfile                  # Multi-stage production container build
│   ├── config.py                   # Centralized configuration & environment loader
│   ├── database.py                 # SQLAlchemy PostGIS ORM schemas (DefectRecord, Survey)
│   ├── spatial_engine.py           # Two-frame matching engine, ST_DWithin query & formulas
│   ├── services.py                 # Gemini 1.5 Flash Civil AI & ReportLab 2-page PDF generator
│   ├── mqtt_service.py             # Telemetry & notification broker client
│   ├── main.py                     # FastAPI REST API endpoints (/scan/analyze, /reports/{id})
│   └── tests/
│       ├── test_spatial_engine.py  # Spatial boundary & temporal chain tests
│       ├── test_api_and_pdf.py     # Endpoint schema & PDF integrity tests
│       └── test_e2e_spatial_temporal.py # Complete 3-visit lifecycle E2E test
├── lib/
│   ├── main.dart                   # Flutter entrypoint & theme initialization
│   ├── models/
│   │   └── defect_analysis_result.dart # Dynamic spatial-temporal data model
│   ├── screens/
│   │   ├── capture_screen.dart     # Camera & Geolocator high-accuracy GPS capture
│   │   ├── report_screen.dart      # Color-coded status badge & 2-frame delta display
│   │   ├── main_screen.dart        # Core navigation shell
│   │   ├── rover_panel_screen.dart # IoT rover control & survey monitor
│   │   └── splash_screen.dart      # ScanTrail branded launcher
│   ├── services/
│   │   ├── api_service.dart        # Multipart HTTP client for /scan/analyze & PDF download
│   │   └── mqtt_service.dart       # Real-time MQTT telemetry listener
│   └── theme/
│       └── app_theme.dart          # Industrial infrastructure styling & status colors
├── test/
│   └── widget_test.dart            # Flutter unit & widget test suite
├── integration_test/
│   └── app_test.dart               # Automated end-to-end user flow simulation
├── docker-compose.yml              # Multi-container orchestration (FastAPI + PostGIS)
├── .env.example                    # Environment variable configuration template
├── requirements.txt                # Python backend dependencies
└── pubspec.yaml                    # Flutter project specification & dependencies
```

---

## API Reference Summary

### `POST /scan/analyze`
Submits a road defect capture with GPS coordinates and dimensions for spatial-temporal matching.
- **Payload**: `multipart/form-data`
  - `image`: Image file (JPEG/PNG)
  - `latitude`: Float (e.g., `12.8406`)
  - `longitude`: Float (e.g., `80.1534`)
  - `bounding_box_area`: Float in $\text{m}^2$ (e.g., `0.50`)
  - `severity_score`: Float `0.0` to `1.0` (optional, default `0.5`)
  - `timestamp`: ISO-8601 UTC timestamp (optional)
- **Response**:
  ```json
  {
    "defect_id": "7b0a70f6-2856-4c47-920f-04a441315b9c",
    "latitude": 12.8406,
    "longitude": 80.1534,
    "timestamp": "2026-09-15T12:00:00",
    "evolution_status": "Worsening",
    "area_change_percentage": 30.0,
    "current_area": 0.65,
    "previous_area": 0.50,
    "time_delta_str": "7d 0h ago",
    "severity_score": 0.85,
    "severity_level": "High",
    "engineering_analysis": {
      "severity_level": "High",
      "root_cause_analysis": "Asphalt fatigue cracking aggravated by subsurface water seepage.",
      "recommended_remediation": "Full-depth asphalt patching and edge drainage installation.",
      "municipal_priority_rank": 8
    },
    "pdf_report_url": "/reports/7b0a70f6-2856-4c47-920f-04a441315b9c"
  }
  ```

### `GET /reports/{report_id}`
Streams the generated, two-page ASTM D6433 compliant engineering evaluation report as `application/pdf`.

---
