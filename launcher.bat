@echo off
:MENU
cls
echo ================================
echo Reflex2.0 Launcher Menu
echo ================================
echo 1. Launch dbm.bat
echo 2. Launch morning.bat
echo 3. Launch runhub.bat
echo 4. Launch startreplay.bat
echo 5. Launch testflex.bat
echo 6. Launch pipme.bat
echo 7. Exit
echo ================================
set /p choice=Enter your choice (1-7): 

if "%choice%"=="1" call dbm.bat
if "%choice%"=="2" call morning.bat
if "%choice%"=="3" call runhub.bat
if "%choice%"=="4" call startreplay.bat
if "%choice%"=="5" call testflex.bat
if "%choice%"=="6" call pipme.bat
if "%choice%"=="7" exit

goto MENU
