@echo off
cd /d "%~dp0"
start "backend-8000" cmd /c start-backend.bat
start "admin-web-5173" cmd /c start-admin-web.bat
start "user-web-5174" cmd /c start-user-web.bat
echo.
echo   Backend API docs : http://127.0.0.1:8000/docs
echo   Admin console    : http://127.0.0.1:5173/
echo   Customer view    : http://127.0.0.1:5174/
echo.
echo   Close the three service windows to stop everything.
echo.
timeout /t 5
