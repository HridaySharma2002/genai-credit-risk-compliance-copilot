# PowerShell script to launch the FastAPI server
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting GenAI Credit Risk & Compliance Copilot API...   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
