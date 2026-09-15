@echo off
title admin-web-5173
cd /d "%~dp0web"
call npm.cmd run dev -- --strictPort
if errorlevel 1 pause
