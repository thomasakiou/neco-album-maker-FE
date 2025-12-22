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
            # 1. Process Archive if present
            if command.zip_path:
                is_rar = command.zip_path.lower().endswith('.rar')
                archive = rarfile.RarFile(command.zip_path, 'r') if is_rar else zipfile.ZipFile(command.zip_path, 'r')
                
                with archive:
                    file_list = archive.infolist()
                    for file_info in file_list:
                        filename = file_info.filename
                        if file_info.is_dir() if hasattr(file_info, 'is_dir') else filename.endswith('/'):
                            continue
                        
                        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                            continue
                        
                        with archive.open(filename) as source:
                            content = source.read()
                            if await self._process_photo(filename, content, photos_dir, missing_students):
                                saved += 1

            # 2. Process Individual Files if present
            if command.individual_files:
                for filename, content in command.individual_files:
                    if await self._process_photo(filename, content, photos_dir, missing_students):
                        saved += 1
            
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

    async def _process_photo(self, filename: str, content: bytes, photos_dir: Path, missing_students: list) -> bool:
        """Processes a single photo and updates the database. Returns True if saved."""
        try:
            basename = Path(filename).name
            reg_no = basename.split('.')[0].strip()
            
            # Find student
            result = await self.session.execute(
                select(Student).where(Student.reg_no.ilike(reg_no))
            )
            student = result.scalar_one_or_none()
            
            if not student:
                missing_students.append(reg_no)
                return False
            
            # Save to disk
            photo_path = photos_dir / f"{reg_no}.jpg"
            with open(photo_path, 'wb') as target:
                target.write(content)
            
            # Update DB
            await self.session.execute(
                update(Student)
                .where(Student.id == student.id)
                .values(photo_path=str(photo_path))
            )
            return True
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            return False