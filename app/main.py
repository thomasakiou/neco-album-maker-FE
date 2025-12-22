from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.routers import students, schools, states, uploads, albums
from app.core.config import settings

app = FastAPI(
    title="NECO Photo Album API",
    description="FastAPI backend for NECO photo album generation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(students.router, prefix="/api/v1")
app.include_router(schools.router, prefix="/api/v1")
app.include_router(states.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(albums.router, prefix="/api/v1")

# Mount Static Files
media_path = Path(settings.media_root)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")


@app.get("/")
async def root():
    return {"message": "NECO Photo Album API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}