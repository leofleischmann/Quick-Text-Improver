@echo off
echo Suche nach laufenden Quick Text Improver Prozessen...
echo.

REM Suche nach Python-Prozessen die main.py ausfuehren
tasklist /FI "IMAGENAME eq python.exe" /FO CSV | findstr /I "python" > nul
if %ERRORLEVEL% EQU 0 (
    echo Gefundene Python-Prozesse:
    tasklist /FI "IMAGENAME eq python.exe" /FO TABLE
    echo.
    echo Versuche Quick Text Improver Prozesse zu beenden...
    REM Beende alle Python-Prozesse (Vorsicht: beendet ALLE Python-Prozesse!)
    REM taskkill /F /IM python.exe
    echo.
    echo Bitte beenden Sie Quick Text Improver manuell ueber das Tray Icon oder Task Manager.
) else (
    echo Keine Python-Prozesse gefunden.
)

echo.
echo Entferne veraltetes Lock File...
if exist "%TEMP%\textimprover_instance.lock" (
    del "%TEMP%\textimprover_instance.lock"
    echo Lock File entfernt.
) else (
    echo Kein Lock File gefunden.
)

echo.
echo Fertig!
pause

