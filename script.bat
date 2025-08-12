@echo off
cd /d "%~dp0"
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)
call venv\Scripts\activate
pip install --upgrade pip
pip install TTS pydub
python tts_script.py
pause
