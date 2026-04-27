@echo off
title JARVIS - Installer
echo.
echo  Installing J.A.R.V.I.S. dependencies...
echo  =========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install it from https://python.org
    pause
    exit /b 1
)

pip install SpeechRecognition pyttsx3 numpy requests

echo.
echo  Installing PyAudio (microphone support)...
pip install pyaudio
if %errorlevel% neq 0 (
    echo.
    echo  PyAudio failed via pip. Trying pipwin...
    pip install pipwin
    pipwin install pyaudio
)

echo.
echo  =========================================
echo  Installation complete!
echo  Run jarvis by double-clicking run.bat
echo  =========================================
pause
