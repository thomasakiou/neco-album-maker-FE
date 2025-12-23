
import asyncio
import os
from pathlib import Path
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.domain.models.student import Student
from app.domain.models.school import School
from app.domain.models.state import State
from app.core.config import settings

# Need to use sync engine for simple script or run async
# converting to sync for simplicity if possible, but the app uses async.
# I will use async.

async def check_photos():
    from app.core.db import async_session_maker
    
    async with async_session_maker() as session:
        # Fetch first 5 students
        result = await session.execute(
            select(Student).limit(5)
        )
        students = result.scalars().all()
        
        print(f"Total students found in DB sample: {len(students)}")
        for s in students:
            print(f"Student: '{s.cand_name}', Reg No: '{s.reg_no}', Photo: '{s.photo_path}'")

        # Specific check for the known file
        target_reg = "2511250299JF"
        print(f"\nChecking for specific reg_no: {target_reg}")
        result = await session.execute(
            select(Student).where(Student.reg_no == target_reg)
        )
        target = result.scalar_one_or_none()
        if target:
            print(f"FOUND target student! ID: {target.id}, Photo: {target.photo_path}")
        else:
            print(f"Target student {target_reg} NOT FOUND in DB.")
        
        project_root = Path.cwd()
        print(f"Current Working Directory (Project Root): {project_root}")
        
        for s in students:
            print("-" * 50)
            print(f"Student: {s.cand_name} ({s.reg_no})")
            print(f"DB photo_path: '{s.photo_path}'")
            
            # Check raw path
            p_raw = Path(s.photo_path)
            print(f"Path(raw).is_absolute(): {p_raw.is_absolute()}")
            print(f"Path(raw).exists(): {p_raw.exists()}")
            
            # Check resolved path logic from disk_generator
            clean_path_str = s.photo_path.lstrip('/').lstrip('\\')
            p_clean = Path(clean_path_str)
            resolved = project_root / p_clean
            
            print(f"Clean relative path: '{p_clean}'")
            print(f"Resolved absolute path: '{resolved}'")
            print(f"Resolved exists: {resolved.exists()}")
            
            if resolved.exists():
                print("SUCCESS: File found via resolution.")
            elif p_raw.exists():
                print("SUCCESS: File found via raw path.")
            else:
                print("FAILURE: File NOT found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_photos())
