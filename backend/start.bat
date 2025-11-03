@echo off
set PYTHONPATH=%CD%
uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload
