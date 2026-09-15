import io
import os
from typing import Dict, Any, Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

# Color definitions for ScanTrail Status Badges
STATUS_COLORS = {
    "New": HexColor("#1976D2"),       # Blue
    "Persistent": HexColor("#FBC02D"),# Yellow
    "Worsening": HexColor("#D32F2F"), # Red
    "Improving": HexColor("#388E3C"), # Green
    "Repaired": HexColor("#757575"),  # Gray
}

def draw_scantrail_logo(p: canvas.Canvas, x: float, y: float):
    """Draws ScanTrail brand icon: stylized road trail with waypoint marker."""
    p.saveState()
    p.translate(x, y)
    
    # Road trail trapezoid (dark slate)
    p.setFillColor(HexColor("#263238"))
    path = p.beginPath()
    path.moveTo(5, -25)
    path.lineTo(15, 10)
    path.lineTo(25, 10)
    path.lineTo(35, -25)
    path.close()
    p.drawPath(path, fill=1, stroke=0)

    # Center dash line (yellow)
    p.setStrokeColor(HexColor("#FFD54F"))
    p.setLineWidth(2)
    p.line(20, -20, 20, -10)
    p.line(20, -5, 20, 5)

    # Waypoint radar circle (teal/cyan)
    p.setFillColor(HexColor("#00ACC1"))
    p.circle(20, 14, 5, fill=1, stroke=0)
    
    p.restoreState()

def draw_multiline_text(p: canvas.Canvas, x: float, y: float, text: str, max_width: float, line_height: float = 14) -> float:
    """Draws wrapped text and returns the updated y position."""
    for paragraph in str(text).split("\n"):
        words = paragraph.split()
        if not words:
            y -= line_height
            continue
        line = ""
        for word in words:
            test_line = f"{line} {word}".strip()
            if p.stringWidth(test_line, p._fontname, p._fontsize) <= max_width:
                line = test_line
            else:
                p.drawString(x, y, line)
                y -= line_height
                line = word
        if line:
            p.drawString(x, y, line)
            y -= line_height
    return y

def create_pdf_report(defect_data: Dict[str, Any], advisory_data: Dict[str, Any]) -> io.BytesIO:
    """
    Renders ScanTrail Road Inspection & Defect Evolution Report:
    - Header: ScanTrail Branding, Map Coordinates, Timestamp
    - Status Badge: Color-coded indicator (New, Persistent, Worsening, Improving, Repaired)
    - Metrics Section: Area delta, growth rate %, severity score
    - Gemini Sections: Engineering Analysis, Recommended Remediation, Maintenance Priority
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # 1. Header & Branding
    draw_scantrail_logo(p, 0.6 * inch, height - 0.75 * inch)
    p.setFont("Helvetica-Bold", 20)
    p.setFillColor(HexColor("#1A237E"))
    p.drawString(1.3 * inch, height - 0.65 * inch, "ScanTrail")

    p.setFont("Helvetica", 11)
    p.setFillColor(HexColor("#546E7A"))
    p.drawString(1.3 * inch, height - 0.85 * inch, "Spatial-Temporal Road Defect Evolution Report")

    # Header horizontal line
    p.setStrokeColor(HexColor("#CFD8DC"))
    p.setLineWidth(1)
    p.line(0.6 * inch, height - 1.05 * inch, width - 0.6 * inch, height - 1.05 * inch)

    # 2. Status Badge
    status = defect_data.get("current_status", "New")
    status_color = STATUS_COLORS.get(status, HexColor("#1976D2"))
    
    badge_x = width - 2.3 * inch
    badge_y = height - 0.9 * inch
    p.setFillColor(status_color)
    p.roundRect(badge_x, badge_y, 1.7 * inch, 0.35 * inch, 4, fill=1, stroke=0)
    
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(HexColor("#FFFFFF"))
    p.drawCentredString(badge_x + 0.85 * inch, badge_y + 0.1 * inch, f"STATUS: {status.upper()}")

    y = height - 1.35 * inch

    # 3. Location & Survey Telemetry Box
    p.setFillColor(HexColor("#F8F9FA"))
    p.roundRect(0.6 * inch, y - 1.0 * inch, width - 1.2 * inch, 1.0 * inch, 4, fill=1, stroke=0)
    
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(HexColor("#37474F"))
    p.drawString(0.8 * inch, y - 0.25 * inch, "TELEMETRY & SPATIAL DATA")

    p.setFont("Helvetica", 9)
    p.setFillColor(HexColor("#263238"))
    lat = defect_data.get("latitude", 0.0)
    lon = defect_data.get("longitude", 0.0)
    rover_id = defect_data.get("rover_id", "Unknown")
    defect_id = defect_data.get("defect_id", "N/A")
    timestamp = defect_data.get("timestamp", "N/A")

    p.drawString(0.8 * inch, y - 0.5 * inch, f"Defect ID: {defect_id}")
    p.drawString(0.8 * inch, y - 0.7 * inch, f"GPS: {lat:.6f}, {lon:.6f}")
    p.drawString(4.0 * inch, y - 0.5 * inch, f"Rover ID: {rover_id}")
    p.drawString(4.0 * inch, y - 0.7 * inch, f"Timestamp: {timestamp}")

    y -= 1.3 * inch

    # 4. Metrics & Temporal Evolution Section
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(HexColor("#1A237E"))
    p.drawString(0.6 * inch, y, "Defect Metrics & Temporal Evolution")
    y -= 0.1 * inch

    p.setStrokeColor(HexColor("#ECEFF1"))
    p.line(0.6 * inch, y, width - 0.6 * inch, y)
    y -= 0.25 * inch

    area = defect_data.get("bounding_box_area", 0.0)
    growth_rate = defect_data.get("growth_rate_pct", 0.0)
    severity_score = defect_data.get("severity_score", 0.0)
    historical_area = defect_data.get("historical_area", area)

    # Draw 3 metric boxes side by side
    box_w = (width - 1.2 * inch - 0.4 * inch) / 3.0
    for i, (label, val, sub) in enumerate([
        ("CURRENT AREA", f"{area:.3f} m²", f"Prev: {historical_area:.3f} m²"),
        ("GROWTH RATE", f"{growth_rate:+.1f}%", f"Evolution: {status}"),
        ("SEVERITY SCORE", f"{severity_score:.2f} / 1.0", f"Rank: {advisory_data.get('severity_level', 'Medium')}")
    ]):
        bx = 0.6 * inch + i * (box_w + 0.2 * inch)
        p.setFillColor(HexColor("#ECEFF1"))
        p.roundRect(bx, y - 0.65 * inch, box_w, 0.65 * inch, 4, fill=1, stroke=0)
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(HexColor("#78909C"))
        p.drawString(bx + 10, y - 0.2 * inch, label)
        p.setFont("Helvetica-Bold", 13)
        p.setFillColor(HexColor("#263238"))
        p.drawString(bx + 10, y - 0.42 * inch, val)
        p.setFont("Helvetica", 8)
        p.setFillColor(HexColor("#546E7A"))
        p.drawString(bx + 10, y - 0.58 * inch, sub)

    y -= 0.95 * inch

    # 5. Generative AI Civil Engineering Advisory
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(HexColor("#1A237E"))
    p.drawString(0.6 * inch, y, "Civil Engineering Advisory (Gemini 1.5 Flash)")
    y -= 0.1 * inch

    p.setStrokeColor(HexColor("#ECEFF1"))
    p.line(0.6 * inch, y, width - 0.6 * inch, y)
    y -= 0.3 * inch

    sections = [
        ("Municipal Priority Rank", f"{advisory_data.get('municipal_priority_rank', 5)} / 10  (Severity: {advisory_data.get('severity_level', 'Medium')})"),
        ("Root Cause Analysis", advisory_data.get("root_cause_analysis", "N/A")),
        ("Recommended Remediation", advisory_data.get("recommended_remediation", "N/A"))
    ]

    for title, content in sections:
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(HexColor("#0D47A1"))
        p.drawString(0.6 * inch, y, title)
        y -= 0.2 * inch

        p.setFont("Helvetica", 9)
        p.setFillColor(HexColor("#37474F"))
        y = draw_multiline_text(p, 0.8 * inch, y, content, width - 1.4 * inch)
        y -= 0.15 * inch

    # 6. Footer
    p.setFont("Helvetica", 8)
    p.setFillColor(HexColor("#90A4AE"))
    p.drawCentredString(width / 2.0, 0.5 * inch, "ScanTrail Autonomous Spatial-Temporal Road Infrastructure Monitoring")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

