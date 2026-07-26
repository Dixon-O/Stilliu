@echo off
cd /d "%~dp0"
set WATSONX_API_KEY=REDACTED_ROTATED_KEY
set WATSONX_PROJECT_ID=REDACTED_PROJECT_ID
set WATSONX_URL=https://eu-gb.ml.cloud.ibm.com
set EMBEDDING_MODEL_ID=ibm/granite-embedding-278m-multilingual
set GENERATION_MODEL_ID=meta-llama/llama-3-3-70b-instruct
set DEMO_MODE=false
set SCORE_TIMEOUT=45
set ANALYZE_TIMEOUT=120
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --log-level warning
