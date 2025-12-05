# -*- coding: utf-8 -*-

import logging
import os
import sys
from datetime import datetime
import traceback


class DebugLogger:
    """Debug-Logging-System für Quick Text Improver."""
    
    def __init__(self, enabled=False, log_to_file=False):
        self.enabled = enabled
        self.log_to_file = log_to_file
        self.logger = None
        self.log_file_path = None
        self.start_times = {}  # Für Zeitmessungen
        
        if enabled:
            self._setup_logger()
    
    def _setup_logger(self):
        """Richtet den Logger ein."""
        self.logger = logging.getLogger('QuickTextImprover')
        self.logger.setLevel(logging.DEBUG)
        
        import time
        
        # Custom Formatter mit Millisekunden-Unterstützung
        class MillisecondFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                ct = self.converter(record.created)
                # Konvertiere msecs zu Integer (kann Float sein)
                msecs = int(record.msecs)
                if datefmt:
                    s = time.strftime(datefmt, ct)
                    # Füge Millisekunden hinzu
                    s = f"{s}.{msecs:03d}"
                else:
                    t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
                    s = f"{t}.{msecs:03d}"
                return s
        
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = MillisecondFormatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # File Handler (optional)
        if self.log_to_file:
            try:
                # Log-Datei im AppData-Verzeichnis
                if sys.platform == 'win32':
                    base_path = os.getenv('APPDATA', os.path.expanduser('~'))
                    log_dir = os.path.join(base_path, 'QuickTextImprover')
                else:
                    log_dir = os.path.join(os.path.expanduser('~'), '.config', 'QuickTextImprover')
                
                os.makedirs(log_dir, exist_ok=True)
                self.log_file_path = os.path.join(log_dir, 'text_improver_debug.log')
                
                file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_format = MillisecondFormatter(
                    '%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_format)
                self.logger.addHandler(file_handler)
                
                self.log("Debug-Logging aktiviert", "Log-Datei: " + self.log_file_path)
            except Exception as e:
                print(f"Konnte Log-Datei nicht erstellen: {e}")
    
    def log(self, message, details=None, level="INFO"):
        """Loggt eine Nachricht."""
        if not self.enabled:
            return
        
        if self.logger:
            full_message = message
            if details:
                full_message += f" | {details}"
            
            if level == "DEBUG":
                self.logger.debug(full_message)
            elif level == "INFO":
                self.logger.info(full_message)
            elif level == "WARNING":
                self.logger.warning(full_message)
            elif level == "ERROR":
                self.logger.error(full_message)
        else:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            print(f"[{timestamp}] [{level}] {message}" + (f" | {details}" if details else ""))
    
    def start_timer(self, name):
        """Startet einen Timer für eine Operation."""
        if self.enabled:
            import time
            self.start_times[name] = time.time()
            self.log(f"Timer gestartet: {name}", level="DEBUG")
    
    def end_timer(self, name):
        """Beendet einen Timer und gibt die Dauer zurück."""
        if not self.enabled or name not in self.start_times:
            return None
        
        import time
        duration = time.time() - self.start_times[name]
        del self.start_times[name]
        self.log(f"Timer beendet: {name}", f"Dauer: {duration:.3f}s", level="DEBUG")
        return duration
    
    def log_exception(self, message, exception):
        """Loggt eine Exception mit Traceback."""
        if self.enabled:
            self.log(f"{message}: {str(exception)}", level="ERROR")
            if self.logger:
                self.logger.exception(message)
            else:
                traceback.print_exc()
    
    def log_performance(self, operation, duration, details=None):
        """Loggt Performance-Metriken."""
        if self.enabled:
            details_str = f" | {details}" if details else ""
            if duration is not None:
                self.log(f"PERF: {operation}", f"{duration:.3f}s{details_str}", level="INFO")
            else:
                self.log(f"PERF: {operation}", f"N/A{details_str}", level="INFO")
    
    def get_log_file_path(self):
        """Gibt den Pfad zur Log-Datei zurück."""
        return self.log_file_path


# Globaler Debug Logger (wird von main.py initialisiert)
debug_logger = None


def init_debug_logger(enabled=False, log_to_file=False):
    """Initialisiert den globalen Debug Logger."""
    global debug_logger
    debug_logger = DebugLogger(enabled, log_to_file)
    return debug_logger


def get_debug_logger():
    """Gibt den globalen Debug Logger zurück."""
    return debug_logger

