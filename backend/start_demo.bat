@echo off
cd /d "%~dp0"
REM ── DEMO MODE ────────────────────────────────────────────────────────────────
REM Serves pre-computed fixtures — no real API calls, no network. The placeholder
REM credentials below only satisfy config validation; they are NOT real secrets.
set WATSONX_API_KEY=demo-placeholder-not-a-real-key
set WATSONX_PROJECT_ID=demo-placeholder-not-a-real-project
set WATSONX_URL=https://eu-gb.ml.cloud.ibm.com
set EMBEDDING_MODEL_ID=ibm/granite-embedding-278m-multilingual
set GENERATION_MODEL_ID=meta-llama/llama-3-3-70b-instruct
set DEMO_MODE=true
set SCORE_TIMEOUT=45
set ANALYZE_TIMEOUT=120
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --log-level warning
