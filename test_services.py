import unittest
import os
from backend.pdf_service import create_pdf_report
from backend.gemini_service import get_gemini_road_defect_analysis, DEFAULT_ADVISORY

class TestPDFAndGeminiService(unittest.TestCase):

    def test_gemini_service_fallback(self):
        analysis = get_gemini_road_defect_analysis(
            latitude=28.6139,
            longitude=77.2090,
            current_status="Worsening",
            temporal_evolution="Worsening (+25.0%)",
            area_delta_pct=25.0,
            bounding_box_area=0.75,
            severity_score=0.85
        )
        self.assertIn("severity_level", analysis)
        self.assertIn("root_cause_analysis", analysis)
        self.assertIn("recommended_remediation", analysis)
        self.assertIn("municipal_priority_rank", analysis)
        self.assertTrue(1 <= analysis["municipal_priority_rank"] <= 10)

    def test_pdf_generation(self):
        defect_data = {
            "defect_id": "test-defect-uuid-1234",
            "current_status": "Worsening",
            "latitude": 28.613928,
            "longitude": 77.209021,
            "rover_id": "rover-alpha-01",
            "timestamp": "2026-09-15 21:00:00 UTC",
            "bounding_box_area": 0.450,
            "historical_area": 0.360,
            "growth_rate_pct": 25.0,
            "severity_score": 0.8
        }
        advisory_data = {
            "severity_level": "High",
            "root_cause_analysis": "Severe asphalt fatigue cracking with evidence of moisture intrusion.",
            "recommended_remediation": "Milling and replacement with hot-mix asphalt (HMA) patch.",
            "municipal_priority_rank": 8
        }
        pdf_buf = create_pdf_report(defect_data, advisory_data)
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(len(pdf_bytes) > 1000)
        # Verify PDF header magic bytes '%PDF'
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()

