@REM @echo off
@REM cd /d "C:\apps\neco-album-maker\neco-album-maker-BE"

@REM REM Activate virtual environment
@REM call .venv\Scripts\activate.bat

@REM REM Start backend
@REM start "" 
@REM uvicorn app.main:app --host 0.0.0.0 --port 8001


@echo off
cd /d "C:\apps\neco-album-maker\neco-album-maker-BE"

start "NECO Album Maker Backend" cmd /k ^
"venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

