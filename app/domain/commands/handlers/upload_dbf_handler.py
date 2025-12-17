import uuid
from dbfread import DBF
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.commands.upload_dbf_command import UploadDbfCommand, UploadDbfResult
from app.domain.models.student import Student
from app.domain.models.school import School
from app.domain.models.state import State
from app.domain.repositories.interfaces import IStudentRepository, ISchoolRepository, IStateRepository


class UploadDbfHandler:
    def __init__(self, student_repo: IStudentRepository, school_repo: ISchoolRepository, 
                 state_repo: IStateRepository, session: AsyncSession):
        self.student_repo = student_repo
        self.school_repo = school_repo
        self.state_repo = state_repo
        self.session = session
    
    async def handle(self, command: UploadDbfCommand) -> UploadDbfResult:
        try:
            async with self.session.begin():
                # Parse states
                states = []
                # Use latin-1 encoding with error handling for DBF files
                state_dbf = DBF(command.state_path, encoding='latin-1', char_decode_errors='ignore')
                
                for record in state_dbf:
                    state_name = record.get('STATE') or record.get('NAME')
                    if not state_name:
                        raise ValueError("Missing 'STATE' or 'NAME' column in state DBF file")
                    states.append(State(code=record['CODE'], state=state_name))
                
                states_imported = await self.state_repo.bulk_upsert(states)
                
                # Parse schools
                schools = []
                school_map = {}
                # Use latin-1 encoding with error handling for DBF files
                fin25_dbf = DBF(command.fin25_path, encoding='latin-1', char_decode_errors='ignore')
                
                for record in fin25_dbf:
                    state_code = record.get('STATE_CODE') or record.get('STATE')
                    if not state_code:
                        raise ValueError("Missing 'STATE_CODE' or 'STATE' column in school DBF file")
                    
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
                    school_map[record['SCHNUM']] = school
                
                schools_imported = await self.school_repo.bulk_upsert(schools)
                
                # Parse students
                students = []
                missing_school_matches = []
                # Use latin-1 encoding with error handling for DBF files
                master_dbf = DBF(command.master_path, encoding='latin-1', char_decode_errors='ignore')
                
                for record in master_dbf:
                    schnum = record['SCHNUM']
                    school = school_map.get(schnum)
                    
                    student = Student(
                        id=uuid.uuid4(),
                        batch=record.get('BATCH', '2025'),
                        schnum=schnum,
                        reg_no=record['REG_NO'],
                        ser_no=record['SER_NO'],
                        cand_name=record['CAND_NAME'],
                        school_id=school.id if school else None
                    )
                    students.append(student)
                    
                    if not school:
                        missing_school_matches.append(record['REG_NO'])
                
                students_imported = await self.student_repo.bulk_add(students)
                
                return UploadDbfResult(
                    students_imported=students_imported,
                    schools_imported=schools_imported,
                    states_imported=states_imported,
                    missing_fields=[],
                    missing_school_matches=missing_school_matches
                )
        except KeyError as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"Missing column in DBF file: {str(e)}") from e
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Check if it's an IntegrityError related to foreign key
            error_msg = str(e)
            if 'foreign key constraint' in error_msg.lower() or 'fk_' in error_msg.lower():
                raise ValueError(f"Foreign key constraint error: A school references a state code that doesn't exist in the states table. Error: {error_msg}") from e
            raise e