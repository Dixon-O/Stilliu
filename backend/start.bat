@echo off
cd /d "%~dp0"
REM ── LIVE MODE ────────────────────────────────────────────────────────────────
REM Credentials are NOT set here. Put WATSONX_API_KEY and WATSONX_PROJECT_ID in
REM backend\.env (gitignored) — config.py loads them automatically. Never hardcode
REM secrets in this file; it is tracked in git.
set WATSONX_URL=https://eu-gb.ml.cloud.ibm.com
set EMBEDDING_MODEL_ID=ibm/granite-embedding-278m-multilingual
set GENERATION_MODEL_ID=meta-llama/llama-3-3-70b-instruct
set DEMO_MODE=false
set SCORE_TIMEOUT=45
set ANALYZE_TIMEOUT=120
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --log-level warning
