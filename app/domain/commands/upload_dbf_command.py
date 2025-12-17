from dataclasses import dataclass
from typing import Optional


@dataclass
class UploadDbfCommand:
    master_path: str
    fin25_path: str
    state_path: str


@dataclass
class UploadDbfResult:
    students_imported: int
    schools_imported: int
    states_imported: int
    missing_fields: list[str]
    missing_school_matches: list[str]
