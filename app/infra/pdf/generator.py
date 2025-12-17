from pathlib import Path
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from PIL import Image as PILImage
from app.domain.models.student import Student


class PDFGenerator:
    def __init__(self):
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
    
    def generate_album(self, students: List[Student], output_path: str, 
                      layout: str = "grid_3x4") -> str:
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        story = []
        
        # Parse layout
        cols, rows = map(int, layout.split('_')[1].split('x'))
        students_per_page = cols * rows
        
        # Process students in batches
        for i in range(0, len(students), students_per_page):
            batch = students[i:i + students_per_page]
            
            # Create table data
            table_data = []
            for row in range(rows):
                row_data = []
                for col in range(cols):
                    idx = row * cols + col
                    if idx < len(batch):
                        student = batch[idx]
                        cell_content = self._create_student_cell(student)
                        row_data.append(cell_content)
                    else:
                        row_data.append("")
                table_data.append(row_data)
            
            # Create table
            table = Table(table_data, colWidths=[2*inch]*cols, rowHeights=[2.5*inch]*rows)
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(table)
        
        doc.build(story)
        return output_path
    
    def _create_student_cell(self, student: Student) -> List:
        content = []
        
        # Add photo
        if student.photo_path and Path(student.photo_path).exists():
            try:
                # Resize image
                img = PILImage.open(student.photo_path)
                img.thumbnail((120, 120))
                temp_path = f"/tmp/{student.reg_no}_thumb.jpg"
                img.save(temp_path)
                content.append(Image(temp_path, width=1.2*inch, height=1.2*inch))
            except:
                content.append(Paragraph("No Photo", self.styles['Normal']))
        else:
            content.append(Paragraph("No Photo", self.styles['Normal']))
        
        # Add student info
        info = f"""
        <b>{student.cand_name}</b><br/>
        Reg: {student.reg_no}<br/>
        Ser: {student.ser_no}
        """
        content.append(Paragraph(info, self.styles['Normal']))
        
        return content