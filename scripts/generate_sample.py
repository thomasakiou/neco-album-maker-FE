import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.infra.pdf.disk_generator import DiskPDFGenerator

class MockSchool:
    def __init__(self):
        self.schnum = "0010017"
        self.sch_name = "IHIE HIGH SCHOOL, IHIE"
        self.town = "ISIALANGWA NORTH"
        self.custodian = "A.I.E., ISIALANGWA NORTH"

class MockStudent:
    def __init__(self, i):
        self.reg_no = f"2511321071BF" if i == 1 else f"251132107{i:03d}AZ"
        self.ser_no = f"{i:04d}"
        self.cand_name = "NWANKWO DARLINGTON UDOCHUKWU" if i == 1 else f"CANDIDATE NAME {i}"
        self.photo_path = None # Using the "No Passport" placeholder from the logic

def test_pdf_gen():
    school = MockSchool()
    students = [MockStudent(i) for i in range(1, 19)] # 18 students (2 pages of 9)
    
    generator = DiskPDFGenerator()
    output_path = "sample_album.pdf"
    
    print(f"Generating sample PDF to {output_path}...")
    generator.generate_school_album(
        school=school,
        students=students,
        exam_title="2025 SSCE (Internal)",
        output_path=output_path
    )
    print("Done!")

if __name__ == "__main__":
    test_pdf_gen()
