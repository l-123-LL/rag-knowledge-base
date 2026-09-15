@echo off
title user-web-5174
cd /d "%~dp0web"
call npm.cmd run dev -- --mode user --port 5174 --strictPort
if errorlevel 1 pause
