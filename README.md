# NECO Photo Album Backend

FastAPI backend for NECO photo album generation with Domain-Driven Design architecture.

## Features

- Parse DBF files (master.dbf, fin25.dbf, state.dbf)
- Upload and manage student photos
- Generate PDF photo albums
- CRUD operations for students, schools, and states
- Async SQLAlchemy with PostgreSQL
- Repository pattern with dependency injection

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database
- pip or poetry

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the server:
```bash
uvicorn app.main:app --reload
```

## Environment Variables

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
MEDIA_ROOT=./media
ALBUMS_DIR=${MEDIA_ROOT}/albums
PHOTOS_DIR=${MEDIA_ROOT}/photos
PAGE_SIZE_DEFAULT=50
MAX_PHOTO_UPLOAD_SIZE_MB=10
```

## API Endpoints

### Upload Endpoints

#### Upload DBF Files
```bash
curl -X POST "http://localhost:8000/api/v1/uploads/dbf" \
  -F "master_dbf=@master.dbf" \
  -F "fin25_dbf=@fin25.dbf" \
  -F "state_dbf=@state.dbf"
```

#### Upload Photos
```bash
curl -X POST "http://localhost:8000/api/v1/uploads/photos" \
  -F "photos_zip=@photos.zip"
```

### Students CRUD

#### List Students
```bash
curl "http://localhost:8000/api/v1/students?page=1&limit=50&batch=2025"
```

#### Get Student
```bash
curl "http://localhost:8000/api/v1/students/{student_id}"
```

#### Create Student
```bash
curl -X POST "http://localhost:8000/api/v1/students" \
  -H "Content-Type: application/json" \
  -d '{
    "batch": "2025",
    "schnm": "12345",
    "reg_no": "REG001",
    "ser_no": "SER001",
    "cand_name": "John Doe"
  }'
```

#### Delete All Students
```bash
curl -X DELETE "http://localhost:8000/api/v1/students?force=true"
```

### Schools CRUD

#### List Schools
```bash
curl "http://localhost:8000/api/v1/schools"
```

#### Create School
```bash
curl -X POST "http://localhost:8000/api/v1/schools" \
  -H "Content-Type: application/json" \
  -d '{
    "schnm": "12345",
    "sch_name": "Test School",
    "state_code": "NG",
    "state_name": "Nigeria"
  }'
```

### States CRUD

#### List States
```bash
curl "http://localhost:8000/api/v1/states"
```

#### Create State
```bash
curl -X POST "http://localhost:8000/api/v1/states" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "NG",
    "name": "Nigeria"
  }'
```

### Album Generation

#### Generate Album
```bash
curl -X POST "http://localhost:8000/api/v1/albums/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "school_id": "uuid-here",
    "batch": "2025",
    "layout": "grid_3x4"
  }'
```

#### Download Album
```bash
curl "http://localhost:8000/api/v1/albums/{album_id}/download" -o album.pdf
```

## Project Structure

```
app/
├── main.py                 # FastAPI application
├── core/
│   ├── config.py          # Configuration settings
│   └── db.py              # Database setup
├── api/v1/
│   ├── deps.py            # Dependency injection
│   └── routers/           # API route handlers
├── domain/
│   ├── models/            # SQLAlchemy models
│   ├── repositories/      # Repository interfaces
│   ├── services/          # Domain services
│   └── commands/          # Command handlers
├── infra/
│   ├── repositories/      # Repository implementations
│   └── pdf/              # PDF generation
└── schemas/              # Pydantic schemas
```

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## File Formats

### DBF Files
- **master.dbf**: Student records with BATCH, SCHNUM, REG_NO, SER_NO, CAND_NAME
- **fin25.dbf**: School records with SCHNUM, SCH_NAME, STATE_CODE, STATE_NAME
- **state.dbf**: State records with CODE, NAME

### Photo Files
- ZIP archive containing photos named by REG_NO (e.g., REG001.jpg)
- Supported formats: JPG, JPEG, PNG
- Photos stored in `MEDIA_ROOT/photos/`

### PDF Albums
- Generated albums stored in `MEDIA_ROOT/albums/`
- Configurable layouts (default: 3x4 grid)
- Includes student photo and details