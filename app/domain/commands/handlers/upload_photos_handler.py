import os
import zipfile
import rarfile
from pathlib import Path
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.commands.upload_photos_command import UploadPhotosCommand, UploadPhotosResult
from app.domain.models.student import Student
from app.core.config import settings


class UploadPhotosHandler:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def handle(self, command: UploadPhotosCommand) -> UploadPhotosResult:
        photos_dir = settings.photos_dir
        photos_dir.mkdir(parents=True, exist_ok=True)
        
        saved = 0
        missing_students = []
        errors = []
        
        try:
            is_rar = command.zip_path.lower().endswith('.rar')
            archive = rarfile.RarFile(command.zip_path, 'r') if is_rar else zipfile.ZipFile(command.zip_path, 'r')
            
            with archive:
                file_list = archive.infolist()
                print(f"Total files in archive: {len(file_list)}")
                
                for file_info in file_list:
                    filename = file_info.filename if is_rar else file_info.filename
                    print(f"Processing: {filename}")
                    
                    if file_info.is_dir() if hasattr(file_info, 'is_dir') else filename.endswith('/'):
                        print(f"Skipping directory: {filename}")
                        continue
                    
                    filename = Path(filename).name
                    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        print(f"Skipping non-image: {filename}")
                        continue
                    
                    reg_no = filename.split('.')[0].strip()
                    print(f"Looking for student with reg_no: {reg_no}")
                    
                    result = await self.session.execute(
                        select(Student).where(Student.reg_no.ilike(reg_no))
                    )
                    student = result.scalar_one_or_none()
                    
                    if not student:
                        print(f"Student not found: {reg_no}")
                        missing_students.append(reg_no)
                        continue
                    
                    photo_path = photos_dir / f"{reg_no}.jpg"
                    print(f"Saving photo to: {photo_path}")
                    
                    with archive.open(file_info.filename if is_rar else file_info) as source, open(photo_path, 'wb') as target:
                        target.write(source.read())
                    
                    await self.session.execute(
                        update(Student)
                        .where(Student.id == student.id)
                        .values(photo_path=str(photo_path))
                    )
                    saved += 1
                    print(f"Saved photo for: {reg_no}")
            
            await self.session.commit()
            print(f"Committed {saved} photos")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            errors.append(str(e))
            await self.session.rollback()
        
        return UploadPhotosResult(
            saved=saved,
            missing_students=missing_students,
            errors=errors
        )