import os
import logging
from pathlib import Path
from sqlalchemy import update, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.student import Student
from app.core.config import settings

logger = logging.getLogger(__name__)

class ScanPhotosHandler:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle_scan(self, scan_path: str):
        """
        Background task to scan a directory and match images to students by reg_no.
        Optimized for 1M+ photos.
        """
        logger.info(f"Starting photo scan for path: {scan_path}")
        path = Path(scan_path)
        
        if not path.exists() or not path.is_dir():
            logger.error(f"Invalid scan path: {scan_path}")
            return

        batch_size = 5000
        matches = []
        total_found = 0
        total_matched = 0

        try:
            # Use os.scandir for better performance on large directories
            for entry in os.scandir(scan_path):
                if entry.is_file() and entry.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    total_found += 1
                    filename = entry.name
                    reg_no = filename.split('.')[0].strip()
                    
                    # Store for bulk update
                    matches.append({
                        "r": reg_no,
                        "p": entry.path
                    })

                    if len(matches) >= batch_size:
                        matched = await self._bulk_update(matches)
                        total_matched += matched
                        matches = []
                        logger.info(f"Processed {total_found} files, matched {total_matched} so far...")

            # Process remaining
            if matches:
                matched = await self._bulk_update(matches)
                total_matched += matched

            logger.info(f"Scan complete. Total files: {total_found}, Total matched: {total_matched}")

        except Exception as e:
            logger.error(f"Error during photo scan: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def _bulk_update(self, matches: list) -> int:
        """Helper to perform bulk updates for a batch of matches."""
        try:
            # Optimized bulk update using bindparam
            stmt = (
                update(Student)
                .where(Student.reg_no == bindparam('r'))
                .values(photo_path=bindparam('p'))
            )
            
            result = await self.session.execute(stmt, matches)
            await self.session.commit()
            return result.rowcount
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            await self.session.rollback()
            return 0
