@echo off
cd /d "%~dp0"
REM ── DEMO MODE ────────────────────────────────────────────────────────────────
REM Serves pre-computed fixtures — no real API calls, no network, no credentials.
REM Placeholder keys used to be set here purely to satisfy config validation;
REM config.py now defaults them to empty and turns demo mode on by itself when
REM they are absent, so there is nothing to fake.
set DEMO_MODE=true
set SCORE_TIMEOUT=45
set ANALYZE_TIMEOUT=120
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --log-level warning
