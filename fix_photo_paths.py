
import asyncio
import os
from pathlib import Path
from sqlalchemy import select, update, bindparam
from app.domain.models.student import Student
from app.domain.models.school import School
from app.domain.models.state import State
from app.core.config import settings
from app.core.db import async_session_maker

async def fix_photo_paths():
    print("Starting photo path repair...")
    
    # 1. Identify Photos Directory
    # Ensure we use absolute path based on project root if settings.media_root is relative
    project_root = Path.cwd()
    photos_dir = project_root / settings.photos_dir
    
    # Handle case where settings might already be absolute (unlikely based on previous checks but good practice)
    if settings.photos_dir.is_absolute():
        photos_dir = settings.photos_dir
        
    print(f"Scanning directory: {photos_dir}")
    
    if not photos_dir.exists():
        print("ERROR: Photos directory not found!")
        return

    # 2. Collect files
    matches = []
    found_files = 0
    
    for entry in os.scandir(photos_dir):
        if entry.is_file() and entry.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            found_files += 1
            filename = entry.name
            reg_no = filename.split('.')[0].strip()
            
            # Use absolute path or relative path?
            # The app seems to store relative paths usually (e.g. media/photos/...) based on config,
            # but uploads handle uses absolute path str(photo_path).
            # Let's stick to what the upload handler TRIED to do:
            # photo_path = photos_dir / f"{reg_no}.jpg" -> which is absolute if photos_dir is absolute?
            # Wait, in upload handler photos_dir was settings.photos_dir (relative).
            # So let's store the path relative to project root for consistency if we want "portable" paths,
            # OR just store what the code was trying to store.
            # The code was doing: photo_path = photos_dir / filename -> "media/photos/XYZ.jpg"
            
            # Since my logic in disk_generator now handles both, let's store the relative path "media/photos/XYZ.jpg"
            # which is cleaner.
            
            # Construct relative path string "media/photos/filename"
            # settings.media_root is "./media" -> "media"
            rel_path = Path("media") / "photos" / filename
            
            matches.append({
                "r": reg_no,
                "p": str(rel_path)
            })

    print(f"Found {found_files} images. Attempting to match {len(matches)} potential students.")
    
    if not matches:
        print("No images found to process.")
        return

    # 3. Bulk Update DB
    async with async_session_maker() as session:
        # Check one student first to see if they exist
        first_reg = matches[0]['r']
        check = await session.execute(select(Student).where(Student.reg_no == first_reg))
        if not check.scalar_one_or_none():
            print(f"WARNING: First student in list {first_reg} not found in DB. Are reg numbers matching?")
        
        batch_size = 1000
        total_updated = 0
        
        for i in range(0, len(matches), batch_size):
            batch = matches[i:i + batch_size]
            
            # Use Core Table Update to avoid ORM PK requirements
            stmt = (
                update(Student.__table__)
                .where(Student.reg_no == bindparam('r'))
                .values(photo_path=bindparam('p'))
            )
            
            try:
                # synchronize_session=False is irrelevant for Core updates but harmless
                result = await session.execute(
                    stmt, 
                    batch
                )
                await session.commit()
                total_updated += result.rowcount
                print(f"Processed batch {i//batch_size + 1}: Updated {result.rowcount} records.")
            except Exception as e:
                print(f"Error updating batch: {e}")
                await session.rollback()
                
        print(f"Repair complete. Total students updated: {total_updated}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_photo_paths())
