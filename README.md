# ScanTrail

> **AI-Based Road Surveillance & Spatial-Temporal Defect Change Detection**

ScanTrail is a multi-visit road defect monitoring system. Rather than detecting surface distress in static isolation, it tracks defects over repeated passes using high-accuracy GPS telemetry, PostGIS spatial queries, and multi-modal feature vectors to classify defect evolution (**New**, **Persistent**, **Worsening**, **Improving**, or **Repaired**).

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
| **New** | First-time defect logged at geodetic coordinates ($\le 2.0\,\text{m}$ radius). | Initial baseline established; schedule routine monitoring. |
| **Worsening** | Defect area growth $\Delta\% > +15.0\%$. | **Priority Work-Order**: Severe subgrade water intrusion or structural fatigue. Dispatch patching crew. |
| **Improving** | Defect area shrinkage $\Delta\% < -15.0\%$. | Surface stabilization or partial patch settling; verify compaction. |
| **Persistent** | Defect area delta within $[-15.0\%, +15.0\%]$. | Defect dimensions stable; monitor during subsequent inspection cycle. |
| **Repaired** | Previous defect coordinate inspected with zero defect detection. | Mark asset restored; archive historical progression record. |

---

## Tech Stack

- **Backend**: FastAPI (Python 3.10+), SQLAlchemy 2.0, GeoAlchemy2
- **Database**: PostgreSQL 15 + PostGIS 3.3
- **AI & Reporting**: Google Gemini 1.5 Flash (`google-generativeai`), ReportLab (PDF Engine)
- **Mobile Client**: Flutter 3.9+ (Dart), Geolocator, Flutter Map, Provider

---

## Local Setup

### Prerequisites
- Git, Python 3.10+, Flutter SDK 3.9+
- PostgreSQL 14+ with PostGIS extension (or Docker)

### 1. Clone
```bash
git clone https://github.com/pranav14-1/scantrail.git
cd ScanTrail
```

### 2. Backend (FastAPI + PostGIS)

#### Option A: Docker Compose (Recommended)
```bash
cp .env.example .env
# Set GEMINI_API_KEY in .env
docker compose up --build
```
Backend runs at `http://localhost:8000` (docs at `http://localhost:8000/docs`).

#### Option B: Manual Setup
```bash
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Run server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend (Flutter App)
```bash
flutter pub get

# Configure backend IP if needed in lib/services/api_service.dart (default: http://10.0.2.2:8000 for Android emulator)
flutter run
```

---

## Testing

```bash
# Run backend test suite
python3 -m unittest discover -s backend/tests -p "test_*.py" -v

# Run Flutter tests
flutter test
```

---

## License

MIT
