@echo off
echo ==========================================================
echo  Starting GenAI Credit Risk & Compliance Copilot API...  
echo ==========================================================
set PYTHONPATH=.
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
pause
