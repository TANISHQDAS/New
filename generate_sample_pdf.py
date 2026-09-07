import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

def create_sample_pdf(filename="sample_quarterly_report.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "Sample Tech Logistics - Q4 FY24 Earnings Report")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "Document ID: STL-Q4-2024 | Published: May 2024 | Author: Abhi Pandey (23BAI10909)")

    # Divider line
    c.setLineWidth(1)
    c.line(50, height - 80, width - 50, height - 80)

    # Section 1: Executive Summary
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 110, "1. Executive Summary & Financial Highlights")

    c.setFont("Helvetica", 11)
    text_lines = [
        "Sample Tech Logistics demonstrated strong operational scaling during Q4 FY24.",
        "Revenue from Operations for Q4 FY24 reached ₹2,500 Cr, up 15% year-over-year.",
        "For full year FY24, total Revenue from Operations stood at ₹9,200 Cr.",
        "Adjusted EBITDA margin improved to 4.2% with positive operating cash flow.",
        "The company delivered 820 million express parcel shipments in FY24.",
        "Network presence expanded across 19,100 PIN codes covering 95% of India."
    ]

    y = height - 135
    for line in text_lines:
        c.drawString(60, y, f"• {line}")
        y -= 20

    # Section 2: Operational Benchmarks
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y - 15, "2. Key Operational Metrics & Macroeconomic Indicators")

    y -= 40
    metrics_lines = [
        "Headline CPI Inflation for FY24 averaged 5.4 per cent according to official data.",
        "Real GDP Growth for FY25 is projected at 7.0 per cent supported by consumer demand.",
        "Total direct workforce stood at 32,000 employees as of March 31, 2024.",
        "Foreign exchange reserves reached USD 648.2 billion in Q4 FY24."
    ]

    for line in metrics_lines:
        c.drawString(60, y, f"• {line}")
        y -= 20

    # Save
    c.save()
    print(f"Sample PDF created successfully: {filename}")

if __name__ == "__main__":
    create_sample_pdf(r"C:\Users\tanis\.gemini\antigravity\scratch\fact-knowledge-layer\sample_quarterly_report.pdf")
