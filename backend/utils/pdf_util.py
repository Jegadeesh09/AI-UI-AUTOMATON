from fpdf import FPDF
import os

def generate_pdf_report(story_id, error_msg, screenshot, suite="Default"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Failure Report: {story_id}", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=f"Suite: {suite}")
    pdf.ln(5)
    pdf.multi_cell(0, 10, txt=f"Error Detail:\n{error_msg}")
    
    if screenshot and os.path.exists(screenshot):
        pdf.ln(10)
        pdf.cell(200, 10, txt="Reference Screenshot:", ln=True)
        pdf.image(screenshot, x=10, w=180)
    
    report_dir = os.path.join("backend/storage/suites", suite, "error_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{story_id}_error_report.pdf")
    pdf.output(report_path)
    return report_path
