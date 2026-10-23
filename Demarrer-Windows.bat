@echo off
chcp 65001 >nul
title Tradevantage - en local
cd /d "%~dp0"
echo.
echo  === Tradevantage : demarrage en local ===
echo.
where node >nul 2>nul
if errorlevel 1 (
  echo  Node.js n'est pas installe.
  echo  Installez la version "LTS" depuis https://nodejs.org puis relancez ce fichier.
  start https://nodejs.org
  pause
  exit /b 1
)
if not exist node_modules (
  echo  Premiere fois : installation des composants, 1 a 3 minutes...
  call npm install
  if errorlevel 1 ( echo  L'installation a echoue. & pause & exit /b 1 )
)
echo.
echo  Le site va s'ouvrir dans votre navigateur : http://localhost:5173
echo  Gardez cette fenetre ouverte. Pour arreter : fermez-la.
echo.
call npm run dev -- --host --open
pause
