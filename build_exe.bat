@echo off

REM --- Überprüfen, ob PyInstaller installiert ist ---
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller ist nicht installiert.
    echo Installation wird versucht...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Fehler bei der Installation von PyInstaller.
        echo Bitte installieren Sie PyInstaller manuell und führen Sie dieses Skript erneut aus.
        pause
        exit /b 1
    )
)

REM --- PyInstaller-Befehl ausführen ---
echo Starte PyInstaller...
pyinstaller --onefile --noconsole --icon=icon.png --add-data="icon.png;." --name QuickTextImprover main.py

REM --- Fehlerbehandlung ---
if %errorlevel% neq 0 (
    echo PyInstaller ist mit einem Fehler fehlgeschlagen.
    echo Überprüfen Sie die obigen Ausgaben für Details.
    pause
    exit /b 1
)

echo.
echo PyInstaller erfolgreich abgeschlossen!
echo Die 'QuickTextImprover.exe' wurde im 'dist'-Ordner erstellt.
pause
exit /b 0

