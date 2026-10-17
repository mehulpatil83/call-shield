@echo off
REM Starts call-shield and an https tunnel so a phone can join as Speaker.
REM Run it from the Command Prompt where your Python environment is active, from anywhere.
cd /d "%~dp0.."
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo cloudflared is not installed. Run:  winget install --id Cloudflare.cloudflared
  echo Then close this window, open a new Command Prompt and run this file again.
  pause
  exit /b 1
)
if not exist app\frontend\dist\index.html (
  echo The web page is not built yet. Run these in app\frontend:  npm install  then  npm run build
  pause
  exit /b 1
)
start "call-shield server" cmd /k python -m app.run --no-browser
timeout /t 4 /nobreak >nul
start "call-shield tunnel" cmd /k cloudflared tunnel --url http://127.0.0.1:8000 --metrics 127.0.0.1:20241
timeout /t 10 /nobreak >nul
start "" http://127.0.0.1:8000/#/call
echo.
echo The Receiver page is open on this computer.
echo If the public address box is empty, copy the https address ending in trycloudflare.com from the tunnel window into it.
echo Close the two new windows to stop the demo.
