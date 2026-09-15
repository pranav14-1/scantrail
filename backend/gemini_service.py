import json
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    genai = None
    HAS_GENAI = False

from typing import Dict, Any, Optional
from .config import settings

if HAS_GENAI and settings.GEMINI_API_KEY:
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        print(f"Warning: Could not configure Gemini model: {e}")
        gemini_model = None
else:
    gemini_model = None

DEFAULT_ADVISORY = {
    "severity_level": "Medium",
    "root_cause_analysis": "Asphalt fatigue cracking due to cyclic traffic loading and environmental weathering.",
    "recommended_remediation": "Clean crack debris, apply polymerized hot-pour crack sealant and localized patching.",
    "municipal_priority_rank": 5
}

def get_gemini_road_defect_analysis(
    latitude: float,
    longitude: float,
    current_status: str,
    temporal_evolution: str,
    area_delta_pct: float,
    bounding_box_area: float,
    severity_score: float
) -> Dict[str, Any]:
    """
    Pass spatial coordinates, historical status, temporal evolution, area delta, and priority
    parameters into Gemini 1.5 Flash.
    Returns structured JSON containing:
      - severity_level (Low, Medium, High, Critical)
      - root_cause_analysis
      - recommended_remediation
      - municipal_priority_rank (Scale 1-10)
    """
    if not gemini_model:
        return DEFAULT_ADVISORY

    prompt = (
        "You are an expert civil and transportation infrastructure engineer specializing in road asset management. "
        "Analyze the following detected road defect data collected by a mobile rover:\n"
        f"- GPS Coordinates: Latitude {latitude:.6f}, Longitude {longitude:.6f}\n"
        f"- Status Classification: {current_status}\n"
        f"- Temporal Evolution: {temporal_evolution}\n"
        f"- Bounding Box Area: {bounding_box_area:.4f} sq meters\n"
        f"- Area Growth Delta: {area_delta_pct:+.2f}%\n"
        f"- Initial Severity Score: {severity_score:.2f} (0.0 to 1.0 scale)\n\n"
        "Provide an engineering analysis and remediation recommendation. "
        "Your entire output must be a single, valid JSON object with EXACTLY these four keys:\n"
        '{\n'
        '  "severity_level": "<Low | Medium | High | Critical>",\n'
        '  "root_cause_analysis": "<concise description of civil engineering root cause, e.g., asphalt fatigue, sub-grade water seepage, thermal expansion>",\n'
        '  "recommended_remediation": "<actionable municipal maintenance action, e.g., hot-mix asphalt patching, full-depth patch, crack sealing>",\n'
        '  "municipal_priority_rank": <integer between 1 and 10>\n'
        '}\n'
        "Do not include markdown wrappers (such as ```json) or any extra commentary."
    )

    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        # Validate keys
        return {
            "severity_level": data.get("severity_level", "Medium"),
            "root_cause_analysis": data.get("root_cause_analysis", DEFAULT_ADVISORY["root_cause_analysis"]),
            "recommended_remediation": data.get("recommended_remediation", DEFAULT_ADVISORY["recommended_remediation"]),
            "municipal_priority_rank": int(data.get("municipal_priority_rank", 5))
        }
    except Exception as e:
        print(f"Gemini API execution error or fallback triggered: {e}")
        # Dynamic fallback matching status
        fallback = dict(DEFAULT_ADVISORY)
        if current_status == "Worsening":
            fallback["severity_level"] = "High"
            fallback["municipal_priority_rank"] = 8
            fallback["root_cause_analysis"] = "Accelerated pavement distress exacerbated by sub-surface water intrusion."
            fallback["recommended_remediation"] = "Full-depth asphalt patching and edge drainage inspection."
        elif current_status == "Improving":
            fallback["severity_level"] = "Low"
            fallback["municipal_priority_rank"] = 3
            fallback["root_cause_analysis"] = "Recent partial maintenance or natural detritus compaction observed."
            fallback["recommended_remediation"] = "Monitor during next routine survey cycle."
        elif current_status == "Repaired":
            fallback["severity_level"] = "Low"
            fallback["municipal_priority_rank"] = 1
            fallback["root_cause_analysis"] = "Defect filled or surfaced successfully."
            fallback["recommended_remediation"] = "Mark asset as restored."
        return fallback
