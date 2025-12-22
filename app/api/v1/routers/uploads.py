import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.domain.commands.upload_dbf_command import UploadDbfCommand
from app.domain.commands.upload_photos_command import UploadPhotosCommand
from app.domain.commands.handlers.upload_dbf_handler import UploadDbfHandler
from app.domain.commands.handlers.upload_photos_handler import UploadPhotosHandler
from app.domain.commands.handlers.scan_photos_handler import ScanPhotosHandler
from app.schemas.upload_schema import ScanPhotosRequest
from app.api.v1.deps import get_student_repo, get_school_repo, get_state_repo

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/dbf/state")
async def upload_state_dbf(
    state_dbf: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    state_repo = Depends(get_state_repo)
):
    """Upload state DBF file (step 1 of 3)"""
    if not state_dbf.filename.lower().endswith('.dbf'):
        raise HTTPException(status_code=400, detail=f"Invalid file type: {state_dbf.filename}")
    
    with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as temp_file:
        temp_file.write(await state_dbf.read())
        temp_path = temp_file.name
    
    try:
        from dbfread import DBF
        from app.domain.models.state import State
        
        async with session.begin():
            states = []
            state_dbf_reader = DBF(temp_path, encoding='latin-1', char_decode_errors='ignore')
            
            for record in state_dbf_reader:
                state_name = record.get('STATE') or record.get('NAME')
                if not state_name:
                    raise ValueError("Missing 'STATE' or 'NAME' column in state DBF file")
                
                # Read schools count from DBF file
                schools_count = record.get('SCHOOLS') or record.get('SCHOOLS_COUNT') or 0
                
                states.append(State(
                    code=record['CODE'], 
                    state=state_name,
                    schools=int(schools_count) if schools_count else 0
                ))
            
            states_imported = await state_repo.bulk_upsert(states)
            
        return {
            "states_imported": states_imported,
            "message": "State data imported successfully. You can now upload fin25.dbf"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        os.unlink(temp_path)


@router.post("/dbf/school")
async def upload_school_dbf(
    fin25_dbf: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    """Upload school DBF file (step 2 of 3)"""
    if not fin25_dbf.filename.lower().endswith('.dbf'):
        raise HTTPException(status_code=400, detail=f"Invalid file type: {fin25_dbf.filename}")
    
    with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as temp_file:
        temp_file.write(await fin25_dbf.read())
        temp_path = temp_file.name
    
    try:
        from dbfread import DBF
        from app.domain.models.school import School
        import uuid
        
        from app.infra.repositories.sqlalchemy_repositories import SchoolRepository, StateRepository
        
        async with session.begin():
            state_repo = StateRepository(session)
            school_repo = SchoolRepository(session)
            
            existing_states = await state_repo.find_all()
            valid_state_codes = {s.code for s in existing_states}
            
            schools = []
            missing_states = set()
            fin25_dbf_reader = DBF(temp_path, encoding='latin-1', char_decode_errors='ignore')
            
            for record in fin25_dbf_reader:
                state_code = record.get('STATE_CODE') or record.get('STATE')
                if not state_code:
                    raise ValueError("Missing 'STATE_CODE' or 'STATE' column in school DBF file")
                
                if state_code not in valid_state_codes:
                    missing_states.add(state_code)
                
                school = School(
                    id=uuid.uuid4(),
                    schnum=record['SCHNUM'],
                    sch_name=record['SCH_NAME'],
                    state=state_code,
                    state_name=record['STATE_NAME'],
                    custodian=record.get('CUSTODIAN'),
                    town=record.get('TOWN')
                )
                schools.append(school)
            
            total_schools = len(schools)
            schools_imported = await school_repo.bulk_upsert(schools, valid_state_codes)
            skipped = total_schools - schools_imported
            
        return {
            "schools_imported": schools_imported,
            "schools_skipped": skipped,
            "missing_state_codes": list(missing_states),
            "message": f"School data imported: {schools_imported} imported, {skipped} skipped due to missing states. You can now upload master.dbf"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        os.unlink(temp_path)


@router.post("/dbf/student")
async def upload_student_dbf(
    master_dbf: UploadFile = File(...),
    session: AsyncSession = Depends(get_db)
):
    """Upload student/master DBF file (step 3 of 3)"""
    if not master_dbf.filename.lower().endswith('.dbf'):
        raise HTTPException(status_code=400, detail=f"Invalid file type: {master_dbf.filename}")
    
    import os
    print(f"Uploading master DBF: {master_dbf.filename}, size: {master_dbf.size if hasattr(master_dbf, 'size') else 'unknown'}")
    
    with tempfile.NamedTemporaryFile(suffix='.dbf', delete=False) as temp_file:
        temp_file.write(await master_dbf.read())
        temp_path = temp_file.name
    
    try:
        from dbfread import DBF
        from app.domain.models.student import Student
        import uuid
        
        master_dbf_reader = DBF(temp_path, encoding='latin-1', char_decode_errors='ignore')
        
        async with session.begin():
            from app.domain.models.school import School
            from app.infra.repositories.sqlalchemy_repositories import SchoolRepository
            
            school_repo = SchoolRepository(session)
            schools = await school_repo.find_all()
            school_map = {s.schnum: s for s in schools}
            
            students = []
            missing_school_matches = []
            
            for record in master_dbf_reader:
                schnum = record.get('SCHNUM')
                if not schnum:
                    continue
                    
                school = school_map.get(schnum)
                
                reg_no = record.get('REG_NO') or record.get('Reg_no')
                ser_no = record.get('SER_NO') or record.get('Ser_no')
                cand_name = record.get('CAND_NAME') or record.get('Cand_name')
                
                if not reg_no or not cand_name:
                    continue
                
                student = Student(
                    id=uuid.uuid4(),
                    batch=record.get('BATCH', '2025'),
                    schnum=schnum,
                    sch_name=school.sch_name if school else None,
                    reg_no=reg_no,
                    ser_no=ser_no,
                    cand_name=cand_name,
                    school_id=school.id if school else None
                )
                students.append(student)
                
                if not school:
                    missing_school_matches.append(record['REG_NO'])
            
            from app.infra.repositories.sqlalchemy_repositories import StudentRepository
            student_repo = StudentRepository(session)
            students_imported = await student_repo.bulk_add(students)
            
            # Update student counts for schools and states
            from sqlalchemy import select, func
            from app.domain.models.student import Student as StudentModel
            
            # Count students per school
            result = await session.execute(
                select(StudentModel.school_id, func.count(StudentModel.id))
                .where(StudentModel.school_id.isnot(None))
                .group_by(StudentModel.school_id)
            )
            school_student_counts = {school_id: count for school_id, count in result.fetchall()}
            
            # Update each school's student count (if you add a students field to School model)
            # For now, we'll just update state counts
            
            # Count students per state (via school relationship)
            result = await session.execute(
                select(School.state, func.count(StudentModel.id))
                .join(School, StudentModel.school_id == School.id)
                .group_by(School.state)
            )
            state_student_counts = {state_code: count for state_code, count in result.fetchall()}
            
            # Update state counts (you might want to add a students field to State model)
            # For now this is just for demonstration
            
        return {
            "students_imported": students_imported,
            "missing_school_matches": missing_school_matches,
            "message": "Student data imported successfully. All uploads complete!"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        os.unlink(temp_path)


@router.post("/photos")
async def upload_photos(
    photos_zip: Optional[UploadFile] = File(None),
    photos: List[UploadFile] = File(None),
    session: AsyncSession = Depends(get_db)
):
    """
    Upload photos either as a single ZIP/RAR file or as multiple individual files.
    This supports both "Upload ZIP File" and "Upload Unzipped Folder" UI options.
    """
    if not photos_zip and not photos:
        raise HTTPException(status_code=400, detail="Either photos_zip or photos list must be provided")

    individual_files = []
    temp_path = None

    try:
        # Case 1: Multiple individual files (Folder Upload)
        if photos:
            for file in photos:
                if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                content = await file.read()
                individual_files.append((file.filename, content))
        
        # Case 2: ZIP/RAR archive
        if photos_zip:
            if not photos_zip.filename.lower().endswith(('.zip', '.rar')):
                raise HTTPException(status_code=400, detail="photos_zip must be a ZIP or RAR archive")
            
            suffix = '.rar' if photos_zip.filename.lower().endswith('.rar') else '.zip'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(await photos_zip.read())
                temp_path = temp_file.name

        # Execute Command
        command = UploadPhotosCommand(
            zip_path=temp_path,
            individual_files=individual_files if individual_files else None
        )
        handler = UploadPhotosHandler(session)
        result = await handler.handle(command)
        
        return {
            "saved": result.saved,
            "missing_students": result.missing_students,
            "errors": result.errors
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        import os
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/scan-photos")
async def scan_photos(
    request: ScanPhotosRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    """
    Initiate a server-side background scan of a directory to match photos to candidates.
    Highly recommended for large datasets (1M+ photos).
    """
    path = Path(request.path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Invalid directory path: {request.path}")

    # Initialize handler
    handler = ScanPhotosHandler(session)
    
    # Add to background tasks to avoid timeout
    background_tasks.add_task(handler.handle_scan, request.path)
    
    return {
        "message": f"Photo scan initiated for path: {request.path}. This will run in the background.",
        "status": "started"
    }