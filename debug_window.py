# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import time
import logging
from datetime import datetime


class DebugWindow(tk.Toplevel):
    """Debug-Fenster zum Anzeigen von Debug-Logs."""
    
    def __init__(self, parent, debug_logger):
        super().__init__(parent)
        self.debug_logger = debug_logger
        self.title("Quick Text Improver - Debug Logs")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # Log-Queue für Thread-sichere Updates
        self.log_queue = queue.Queue()
        
        # Hauptcontainer
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Header mit Buttons
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_frame, text="Debug Logs", font=("", 12, "bold")).pack(side="left")
        
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side="right")
        
        clear_btn = ttk.Button(button_frame, text="Löschen", command=self.clear_logs)
        clear_btn.pack(side="left", padx=(0, 5))
        
        copy_btn = ttk.Button(button_frame, text="Kopieren", command=self.copy_logs)
        copy_btn.pack(side="left", padx=(0, 5))
        
        auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(
            button_frame,
            text="Auto-Scroll",
            variable=auto_scroll_var
        )
        auto_scroll_check.pack(side="left")
        self.auto_scroll = auto_scroll_var
        
        # Text-Widget für Logs
        self.log_text = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # Konfiguriere Tags für verschiedene Log-Level
        self.log_text.tag_config("DEBUG", foreground="#808080")
        self.log_text.tag_config("INFO", foreground="#4ec9b0")
        self.log_text.tag_config("WARNING", foreground="#dcdcaa")
        self.log_text.tag_config("ERROR", foreground="#f48771")
        self.log_text.tag_config("PERF", foreground="#569cd6")
        
        # Status-Bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Bereit")
        self.status_label.pack(side="left")
        
        # Starte Queue-Processor
        self.process_log_queue()
        
        # Protokoll für Fenster-Schließung
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialisiere mit vorhandenen Logs (falls verfügbar)
        self.add_initial_message()
    
    def add_initial_message(self):
        """Fügt eine initiale Nachricht hinzu."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.append_log(f"[{timestamp}] Debug-Fenster geöffnet", "INFO")
    
    def append_log(self, message, level="INFO"):
        """Fügt eine Log-Nachricht hinzu (Thread-sicher über Queue)."""
        self.log_queue.put((message, level))
    
    def process_log_queue(self):
        """Verarbeitet Log-Nachrichten aus der Queue (im Main-Thread)."""
        try:
            while True:
                try:
                    message, level = self.log_queue.get_nowait()
                    self._append_log_direct(message, level)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Fehler beim Verarbeiten der Log-Queue: {e}")
        finally:
            # Prüfe erneut in 100ms
            self.after(100, self.process_log_queue)
    
    def _append_log_direct(self, message, level="INFO"):
        """Fügt eine Log-Nachricht direkt hinzu (muss im Main-Thread aufgerufen werden)."""
        try:
            # Füge Zeilenumbruch hinzu
            full_message = message + "\n"
            
            # Füge Text hinzu
            self.log_text.insert(tk.END, full_message, level)
            
            # Auto-Scroll wenn aktiviert
            if self.auto_scroll.get():
                self.log_text.see(tk.END)
            
            # Begrenze auf 10000 Zeilen (um Speicher zu sparen)
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 10000:
                self.log_text.delete('1.0', f'{lines - 10000}.0')
        except Exception as e:
            print(f"Fehler beim Hinzufügen von Log: {e}")
    
    def clear_logs(self):
        """Löscht alle Logs."""
        self.log_text.delete('1.0', tk.END)
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.append_log(f"[{timestamp}] Logs gelöscht", "INFO")
    
    def copy_logs(self):
        """Kopiert alle Logs in die Zwischenablage."""
        try:
            content = self.log_text.get('1.0', tk.END)
            self.clipboard_clear()
            self.clipboard_append(content)
            self.status_label.config(text="Logs in Zwischenablage kopiert")
            self.after(2000, lambda: self.status_label.config(text="Bereit"))
        except Exception as e:
            self.status_label.config(text=f"Fehler beim Kopieren: {e}")
    
    def on_close(self):
        """Wird aufgerufen, wenn das Fenster geschlossen wird."""
        self.destroy()


# Custom Log Handler für das Debug-Fenster
class DebugWindowHandler(logging.Handler):
    """Custom Log Handler, der Logs an das Debug-Fenster weiterleitet."""
    
    def __init__(self, debug_window):
        super().__init__()
        self.debug_window = debug_window
    
    def emit(self, record):
        """Sendet eine Log-Nachricht an das Debug-Fenster."""
        try:
            if self.debug_window and self.debug_window.winfo_exists():
                # Formatiere die Nachricht
                msg = self.format(record)
                level = record.levelname
                self.debug_window.append_log(msg, level)
        except Exception:
            pass  # Ignoriere Fehler beim Senden an das Fenster

