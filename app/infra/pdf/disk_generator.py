import os
import textwrap
from pathlib import Path
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import code128, qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.platypus import Table, TableStyle, Image, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage
from app.domain.models.student import Student
from app.domain.models.school import School


class DiskPDFGenerator:
    def __init__(self):
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self.neco_green = colors.Color(0, 0.506, 0.212)
        self.neco_yellow = colors.Color(1, 0.808, 0)
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        # Custom styles for the album
        self.center_style = ParagraphStyle(
            'Center',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=10
        )
        self.header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=14,
            leading=16,
            fontName='Helvetica-Bold'
        )
        self.title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontSize=24,
            leading=28,
            fontName='Helvetica-Bold'
        )
        self.meta_style = ParagraphStyle(
            'Metadata',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=14,
            fontName='Helvetica-Bold'
        )
        self.cell_label_style = ParagraphStyle(
            'CellLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=10,
            fontName='Helvetica-Bold'
        )
        self.cell_value_style = ParagraphStyle(
            'CellValue',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=10,
            fontName='Helvetica'
        )

    def generate_school_album(self, school: School, students: List[Student], exam_title: str, output_path: str):
        """Generates a PDF album for a single school."""
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # 1. Page 1: Front Page
        self._draw_front_page(c, school, exam_title)
        c.showPage()
        
        # 2. Student Grid Pages
        students_per_page = 9
        total_pages = (len(students) + students_per_page - 1) // students_per_page
        
        for i in range(0, len(students), students_per_page):
            batch = students[i:i + students_per_page]
            page_num = (i // students_per_page) + 1
            self._draw_grid_page(c, school, batch, page_num, total_pages)
            c.showPage()
            
        c.save()

    def _draw_front_page(self, c: canvas.Canvas, school: School, exam_title: str):
        # Draw L-shaped borders (Green and Yellow) - Left and Bottom ONLY
        border_width = 15 * mm 
        green_thickness = 5 * mm
        yellow_thickness = 4 * mm 
        
        # 1. Left Vertical Line 
        c.setStrokeColor(self.neco_green)
        c.setLineWidth(green_thickness)
        # Vertical Green: Extending slightly below border_width to overlap with horizontal line
        c.line(border_width, border_width - 5*mm, border_width, self.height - border_width)
        
        c.setStrokeColor(self.neco_yellow)
        c.setLineWidth(yellow_thickness)
        yellow_x = border_width + green_thickness/2 + yellow_thickness/2 - 1*mm
        # Vertical Yellow: Same extension
        c.line(yellow_x, border_width - 5*mm, yellow_x, self.height - border_width)
        
        # 2. Bottom Horizontal Line
        c.setStrokeColor(self.neco_green)
        c.setLineWidth(green_thickness)
        # Horizontal Green: Extending slightly left of border_width to overlap with vertical line
        c.line(border_width - 5*mm, border_width, self.width - border_width, border_width)
        
        c.setStrokeColor(self.neco_yellow)
        c.setLineWidth(yellow_thickness)
        yellow_y = border_width + green_thickness/2 + yellow_thickness/2 - 1*mm
        # Horizontal Yellow: Same extension
        c.line(border_width - 5*mm, yellow_y, self.width - border_width, yellow_y)

        # Logo - Moved a little to the right
        project_root = Path(__file__).parent.parent.parent.parent
        logo_path = project_root / "public" / "image" / "neco.png"
        if logo_path.exists():
            # Shifted right by 3mm (from -15mm to -12mm)
            c.drawImage(str(logo_path), border_width - 12*mm, self.height - 75*mm, width=30*mm, height=30*mm, preserveAspectRatio=True, mask='auto')

        # Header - Bolder and Centered
        c.setFillColor(self.neco_green)
        c.setFont("Helvetica-Bold", 16) # Slightly bigger/bolder
        c.drawCentredString(self.width/2 + 10*mm, self.height - 35*mm, "NATIONAL EXAMINATIONS COUNCIL (NECO)")
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 26) # Bigger/Bolder
        c.drawCentredString(self.width/2 + 10*mm, self.height - 65*mm, exam_title)
        
        # Center Text - Bolder
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(self.width/2 + 10*mm, self.height/2 + 65*mm, "SCHOOL")
        c.drawCentredString(self.width/2 + 10*mm, self.height/2 + 48*mm, "PHOTO ALBUM")
        
        # School Info - Bolder
        c.setFont("Helvetica-Bold", 16)
        school_name = school.sch_name.upper()
        lines = textwrap.wrap(school_name, width=42)
        
        y_pos = self.height/2 - 20*mm
        for line in lines:
            c.drawCentredString(self.width/2 + 10*mm, y_pos, line)
            y_pos -= 6*mm # Spacing between lines
        
        # School Number - Positioned relative to school name lines
        schnum_y = y_pos - 10*mm 
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(self.width/2 + 10*mm, schnum_y, f"[{school.schnum}]")
        
        # Metadata - Smaller, closer, left-aligned
        meta_x = border_width + 15*mm
        meta_y = border_width + 50*mm
        c.setFont("Helvetica-Bold", 9) # Smaller
        c.drawString(meta_x, meta_y, "LGA:")
        c.setFont("Helvetica", 9)
        c.drawString(meta_x + 25*mm, meta_y, school.town.upper() if school.town else "")
        
        meta_y -= 10*mm # Closer together
        c.setFont("Helvetica-Bold", 9)
        c.drawString(meta_x, meta_y, "CUSTODIAN:")
        c.setFont("Helvetica", 9)
        c.drawString(meta_x + 25*mm, meta_y, school.custodian.upper() if school.custodian else "")
        
        # Footer Badge - Moved under the bottom border and removed yellow
        c.setFillColor(self.neco_green)
        badge_w = 45*mm
        badge_h = 9*mm
        badge_x = self.width/2 - badge_w/2 + 10*mm
        badge_y = border_width - badge_h - 2*mm # Under the border
        c.rect(badge_x, badge_y, badge_w, badge_h, fill=1, stroke=0) # No yellow stroke
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(badge_x + badge_w/2, badge_y + 3*mm, "SCHOOL COPY")

    def _draw_grid_page(self, c: canvas.Canvas, school: School, students: List[Student], page_num: int, total_pages: int):
        c.setFillColor(colors.black)
        
        # Header: labels match 112.png
        c.setFont("Helvetica-Bold", 9)
        c.drawString(15*mm, self.height - 10*mm, "SCHOOL NUMBER:")
        c.setFont("Helvetica", 9)
        c.drawString(50*mm, self.height - 10*mm, f"[{school.schnum}]")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(15*mm, self.height - 15*mm, "NAME OF SCHOOL:")
        c.setFont("Helvetica", 9)
        c.drawString(50*mm, self.height - 15*mm, school.sch_name.upper())
        
        # Grid settings
        margin_left = 10*mm
        margin_top = 22*mm
        cell_width = 63*mm
        cell_height = 65*mm
        
        for idx, student in enumerate(students):
            row = idx // 3
            col = idx % 3
            
            x = margin_left + col * cell_width
            y = self.height - margin_top - (row + 1) * cell_height
            
            self._draw_student_cell(c, student, x, y, cell_width, cell_height)
            
        # Footer
        footer_y = 25*mm
        c.setFont("Helvetica-Bold", 8)
        c.drawString(15*mm, footer_y, "PRINCIPAL'S SIGNATURE & STAMP: ________________________________")
        c.drawString(15*mm, footer_y - 10*mm, "DATE: _______________________")
        
        # Page Number
        c.setFont("Helvetica", 8)
        c.drawRightString(self.width - 15*mm, 10*mm, f"{page_num} of {total_pages}")

    def _draw_student_cell(self, c: canvas.Canvas, student: Student, x: float, y: float, w: float, h: float):
        # Cell border
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.0)
        c.rect(x, y, w, h)
        
        # Layout: Passport on left, QR on right
        photo_size = 35*mm
        photo_x = x + 2*mm
        photo_y = y + h - photo_size - 2*mm
        
        photo_drawn = False
        project_root = Path(__file__).parent.parent.parent.parent
        placeholder_path = project_root / "public" / "image" / "null.jpg"
        
        if student.photo_path:
            p_path = Path(student.photo_path)
            
            # If not absolute, it's relative to project root (e.g., media/photos/...)
            if not p_path.is_absolute():
                # No need to prepend if it already exists or if it already starts with media
                # Just trust the path as stored
                pass
            
            if p_path.exists():
                try:
                    c.drawImage(str(p_path), photo_x, photo_y, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    photo_drawn = True
                except Exception as e:
                    print(f"Error drawing photo {student.photo_path}: {e}")
                    pass
            else:
                print(f"Photo path does not exist: {p_path}")
        
        if not photo_drawn and placeholder_path.exists():
            try:
                c.drawImage(str(placeholder_path), photo_x, photo_y, width=photo_size, height=photo_size, preserveAspectRatio=True)
                photo_drawn = True
            except:
                pass

        if not photo_drawn:
            # Fallback if both photo and placeholder fail
            c.setStrokeColor(colors.lightgrey)
            c.rect(photo_x, photo_y, photo_size, photo_size)
            c.setFont("Helvetica", 14)
            c.drawCentredString(photo_x + photo_size/2, photo_y + photo_size/2, "No Photo")

        # QR Code on the right of the photo
        qr_size = 18*mm  # Compact size
        qr_x = x + photo_size + 3*mm
        qr_y = photo_y + (photo_size - qr_size)/2
        
        qr_code = qr.QrCodeWidget("https://neco.gov.ng/")
        qr_code.barLevel = 'M'  # Medium error correction for better scanning
        bounds = qr_code.getBounds()
        qr_w = bounds[2] - bounds[0]
        qr_h = bounds[3] - bounds[1]
        d = Drawing(qr_size, qr_size, transform=[qr_size/qr_w, 0, 0, qr_size/qr_h, 0, 0])
        d.add(qr_code)
        renderPDF.draw(d, c, qr_x, qr_y)
        
        # Details below matching 112.png
        details_y = photo_y - 4*mm  # Adjusted spacing
        line_h = 4*mm  # Bigger line height for larger text
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 2*mm, details_y, "Serial No.")
        c.setFont("Helvetica", 9)
        c.drawString(x + 20*mm, details_y, student.ser_no)
        
        details_y -= line_h
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 2*mm, details_y, "Exam No.")
        c.setFont("Helvetica", 9)
        c.drawString(x + 20*mm, details_y, student.reg_no)
        
        details_y -= line_h
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 2*mm, details_y, "Name")
        
        # Wrap name
        p = Paragraph(student.cand_name.upper(), self.cell_value_style)
        aw, ah = p.wrap(w - 20*mm, 15*mm)
        p.drawOn(c, x + 18*mm, details_y - ah + 2*mm)
        
        # Barcode (Code128) - Compact size
        barcode = code128.Code128(
            student.reg_no, 
            barHeight=8*mm,  # Compact height
            barWidth=0.4*mm,  # Standard bar width
            humanReadable=False  # No text below barcode
        )
        barcode_y = y + 2*mm  # Slightly more padding from bottom
        barcode.drawOn(c, x + (w - barcode.width)/2, barcode_y)
