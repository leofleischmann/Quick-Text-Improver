# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import sys
import traceback
import queue
import logging
from datetime import datetime

# --- Konsolenfenster verstecken (außer bei Debug) ---# Diese Funktion wird so früh wie möglich aufgerufen, um das Fenster zu verstecken
def hide_console_if_needed():
    """Versteckt das Konsolenfenster, außer Debug-Modus ist aktiviert."""
    if sys.platform == 'win32':
        try:
            # Prüfe ob Debug-Modus aktiviert ist (vor dem Laden der Config)
            # Wir müssen die Config hier laden, aber das sollte OK sein
            debug_enabled = False
            try:
                from config import ConfigManager
                config = ConfigManager()
                debug_enabled = config.get("debug_enabled")
            except:
                pass
            
            # Nur verstecken wenn Debug nicht aktiviert ist
            if not debug_enabled:
                import ctypes
                kernel32 = ctypes.WinDLL('kernel32')
                user32 = ctypes.WinDLL('user32')
                
                # Hole Konsolenfenster-Handle
                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    # SW_HIDE = 0 - Verstecke das Fenster komplett
                    user32.ShowWindow(hwnd, 0)
                    
                    # Setze auch das Fenster auf "nicht sichtbar" im Taskbar
                    # GWL_EXSTYLE = -20, WS_EX_TOOLWINDOW = 0x00000080
                    try:
                        exstyle = user32.GetWindowLongW(hwnd, -20)
                        user32.SetWindowLongW(hwnd, -20, exstyle | 0x00000080)
                    except:
                        pass
        except Exception as e:
            # Falls Verstecken fehlschlägt, ignoriere es
            pass

# --- Debug-print Funktion ---
_debug_enabled = None

def debug_print(*args, **kwargs):
    """Gibt nur aus, wenn Debug-Modus aktiviert ist."""
    global _debug_enabled
    if _debug_enabled is None:
        try:
            from config import ConfigManager
            config = ConfigManager()
            _debug_enabled = config.get("debug_enabled")
        except:
            _debug_enabled = False
    
    if _debug_enabled:
        print(*args, **kwargs)

# Verstecke Konsolenfenster beim Import (wenn nicht Debug)
hide_console_if_needed()

# --- Dependency Imports ---
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    # Diese Fehler müssen immer angezeigt werden (auch ohne Debug)
    if sys.stdout:  # Nur wenn Konsolenfenster sichtbar ist
        print("FATAL ERROR: 'pynput' not found.")
        print("Install with: pip install pynput")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    # Diese Fehler müssen immer angezeigt werden (auch ohne Debug)
    if sys.stdout:  # Nur wenn Konsolenfenster sichtbar ist
        print("FATAL ERROR: 'pyperclip' not found.")
        print("Install with: pip install pyperclip")

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    debug_print("Warning: 'pystray' not found. System tray will be disabled.")
    debug_print("Install with: pip install pystray Pillow")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    debug_print("Warning: 'psutil' not found. Stale lock file detection might not work.")
    debug_print("Install with: pip install psutil")

# --- Local Module Imports ---
try:
    from config import ConfigManager
    from gemini_api import improve_text_with_gemini, improve_text_with_gemini_stream
    from settings_window import SettingsWindow
    from debug_logger import init_debug_logger, get_debug_logger
    from debug_window import DebugWindow, DebugWindowHandler
except ImportError as e:
    # Kritischer Fehler - muss immer angezeigt werden
    if sys.stdout:
        print(f"FATAL ERROR: Could not import local modules: {e}")
    root_err = tk.Tk()
    root_err.withdraw()
    messagebox.showerror("Import Fehler", f"Modulimport fehlgeschlagen: {e}")
    root_err.destroy()
    sys.exit(f"Import Error: {e}")

# --- App Konstanten ---
APP_VERSION = "1.0"
APP_NAME = "QuickTextImprover"

# --- Main Application Class ---
class TextImproverApp:
    def __init__(self, root):
        self.root = root
        self.config = ConfigManager()
        self.hotkey_listener = None
        self.listener_thread = None
        self.tray_icon = None
        self.tray_thread = None
        self.settings_window_instance = None
        self.debug_window_instance = None
        self.is_shutting_down = False
        self.is_processing = False
        self.original_text = None  # Speichert den ursprünglichen Text
        self.stream_thread_obj = None  # Referenz zum Stream-Thread
        # Queue für Thread-zu-GUI Kommunikation (Thread-sicher)
        self.message_queue = queue.Queue()
        # Starte Queue-Processor
        self.root.after(100, self.process_queue)
        
        # Initialisiere Debug Logger
        debug_enabled = self.config.get("debug_enabled")
        debug_log_to_file = self.config.get("debug_log_to_file")
        init_debug_logger(debug_enabled, debug_log_to_file)
        self.debug = get_debug_logger()
        
        # Aktualisiere globale Debug-Einstellung für debug_print
        global _debug_enabled
        _debug_enabled = debug_enabled
        
        # Verstecke Konsolenfenster erneut (falls es wieder angezeigt wurde)
        if not debug_enabled:
            hide_console_if_needed()
        
        if debug_enabled:
            self.debug.log("Quick Text Improver gestartet", "Debug-Modus aktiviert")
            # Verbinde Debug-Logger mit Debug-Fenster (wird später erstellt)
            # Das wird in open_debug_window gemacht
        
        # Verstecke Hauptfenster immer (läuft im Hintergrund)
        self.root.withdraw()
        
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        # Starte Hotkey Listener
        if HAS_PYNPUT:
            self.start_hotkey_listener()
        else:
            debug_print("ERROR: pynput not available. Hotkey listener cannot start.")
        
        # Setup System Tray
        if HAS_PYSTRAY:
            self.setup_tray_icon()
            if self.tray_icon:
                self.tray_thread = threading.Thread(target=self.run_tray_icon, daemon=True)
                self.tray_thread.start()
        else:
            debug_print("System tray not available.")
        
        debug_print("Quick Text Improver gestartet. Drücke STRG+R um markierten Text zu verbessern.")
    
    def setup_tray_icon(self):
        """Erstellt das System Tray Icon."""
        if not HAS_PYSTRAY:
            self.tray_icon = None
            return
        
        try:
            # Versuche icon.png zu laden
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                try:
                    icon_image = Image.open(icon_path)
                    # Resize auf 64x64 falls nötig
                    if icon_image.size != (64, 64):
                        icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
                    debug_print(f"Custom Icon geladen: {icon_path}")
                except Exception as e:
                    debug_print(f"Fehler beim Laden des Custom Icons: {e}. Verwende Standard-Icon.")
                    icon_image = Image.new('RGB', (64, 64), color='lightgreen')
                    d = ImageDraw.Draw(icon_image)
                    d.rectangle([10, 10, 54, 54], fill='darkgreen')
                    d.text((20, 20), "T", fill='white')
            else:
                # Fallback: Erstelle einfaches Icon
                debug_print(f"Icon nicht gefunden: {icon_path}. Verwende Standard-Icon.")
                icon_image = Image.new('RGB', (64, 64), color='lightgreen')
                d = ImageDraw.Draw(icon_image)
                d.rectangle([10, 10, 54, 54], fill='darkgreen')
                d.text((20, 20), "T", fill='white')
            
            # Definiere Menü
            menu_items = [
                pystray.MenuItem('Einstellungen...', self.on_tray_open_settings),
            ]
            
            # Debug-Menüpunkt nur hinzufügen, wenn Debug aktiviert ist
            if self.debug and self.debug.enabled:
                menu_items.append(pystray.MenuItem('Debug Logs...', self.on_tray_open_debug))
            
            menu_items.extend([
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f'Version: {APP_VERSION}', None, enabled=False),
                pystray.MenuItem(f'Hotkey: {self.config.get("hotkey")}', None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Beenden', self.on_tray_quit)
            ])
            tray_menu = pystray.Menu(*menu_items)
            
            self.tray_icon = pystray.Icon(
                APP_NAME,
                icon=icon_image,
                title="Quick Text Improver",
                menu=tray_menu
            )
            debug_print("System tray icon konfiguriert.")
        except Exception as e:
            debug_print(f"Fehler beim Setup des Tray Icons: {e}")
            traceback.print_exc()
            self.tray_icon = None
    
    def run_tray_icon(self):
        """Startet den pystray Event Loop."""
        if self.tray_icon:
            try:
                self.tray_icon.run()
            except Exception as e:
                debug_print(f"Fehler beim Ausführen des Tray Icons: {e}")
    
    def on_tray_open_settings(self, icon=None, item=None):
        """Callback für Tray Menü: Einstellungen öffnen."""
        debug_print("Tray action: Open settings")
        self.root.after(0, self.open_settings)
    
    def on_tray_open_debug(self, icon=None, item=None):
        """Callback für Tray Menü: Debug-Fenster öffnen."""
        debug_print("Tray action: Open debug window")
        self.root.after(0, self.open_debug_window)
    
    def on_tray_quit(self, icon=None, item=None):
        """Callback für Tray Menü: Beenden."""
        debug_print("Beenden über Tray Menü...")
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.quit_app)
    
    def open_settings(self):
        """Öffnet das Einstellungsfenster."""
        if self.settings_window_instance and self.settings_window_instance.winfo_exists():
            debug_print("Settings window already open.")
            self.settings_window_instance.focus_set()
            self.settings_window_instance.lift()
            return
        
        debug_print("Opening settings window...")
        
        def settings_closed_callback():
            debug_print("Settings window closed.")
            self.settings_window_instance = None
            # Starte Hotkey Listener neu, falls Hotkey geändert wurde
            if HAS_PYNPUT:
                self.start_hotkey_listener()
            # Aktualisiere Tray Menu
            if self.tray_icon:
                self.setup_tray_icon()
        
        # Stelle sicher, dass Root sichtbar ist für das Settings Window
        root_was_hidden = False
        try:
            if self.root.state() == 'withdrawn':
                root_was_hidden = True
                self.root.deiconify()
                self.root.update_idletasks()
                time.sleep(0.05)
            
            self.settings_window_instance = SettingsWindow(
                self.root,
                self.config,
                settings_closed_callback
            )
            debug_print("SettingsWindow instance created.")
            
            self.root.update_idletasks()
            if self.settings_window_instance and self.settings_window_instance.winfo_exists():
                self.settings_window_instance.deiconify()
                self.settings_window_instance.lift()
                self.settings_window_instance.focus_force()
            else:
                debug_print("Settings window instance invalid after creation.")
                self.settings_window_instance = None
        except Exception as e:
            debug_print("!!! Error creating/showing SettingsWindow !!!")
            traceback.print_exc()
            messagebox.showerror("Fenster Fehler", f"Einstellungen konnten nicht erstellt/angezeigt werden:\n{e}")
            self.settings_window_instance = None
        finally:
            # Verstecke Root-Fenster wieder (wichtig: immer verstecken, nicht nur wenn hide_main_window aktiviert ist)
            if root_was_hidden:
                self.root.withdraw()
    
    def open_debug_window(self):
        """Öffnet das Debug-Fenster."""
        if not self.debug or not self.debug.enabled:
            messagebox.showinfo("Debug deaktiviert", "Debug-Modus ist nicht aktiviert.")
            return
        
        if self.debug_window_instance and self.debug_window_instance.winfo_exists():
            debug_print("Debug window already open.")
            self.debug_window_instance.focus_set()
            self.debug_window_instance.lift()
            return
        
        debug_print("Opening debug window...")
        
        # Stelle sicher, dass Root sichtbar ist für das Debug Window
        root_was_hidden = False
        try:
            if self.root.state() == 'withdrawn':
                root_was_hidden = True
                self.root.deiconify()
                self.root.update_idletasks()
                time.sleep(0.05)
            
            self.debug_window_instance = DebugWindow(self.root, self.debug)
            
            # Verbinde Debug-Logger mit Debug-Fenster
            if self.debug and self.debug.logger:
                debug_handler = DebugWindowHandler(self.debug_window_instance)
                debug_handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
                debug_handler.setFormatter(formatter)
                self.debug.logger.addHandler(debug_handler)
            
            debug_print("DebugWindow instance created.")
            
            self.root.update_idletasks()
            if self.debug_window_instance and self.debug_window_instance.winfo_exists():
                self.debug_window_instance.deiconify()
                self.debug_window_instance.lift()
                self.debug_window_instance.focus_force()
            else:
                debug_print("Debug window instance invalid after creation.")
                self.debug_window_instance = None
        except Exception as e:
            debug_print("!!! Error creating/showing DebugWindow !!!")
            traceback.print_exc()
            messagebox.showerror("Fenster Fehler", f"Debug-Fenster konnte nicht erstellt/angezeigt werden:\n{e}")
            self.debug_window_instance = None
        finally:
            # Verstecke Root-Fenster wieder
            if root_was_hidden:
                self.root.withdraw()
    
    def start_hotkey_listener(self):
        """Startet den globalen Hotkey Listener."""
        if not HAS_PYNPUT:
            return
        
        self.stop_hotkey_listener()
        hotkey_str = self.config.get("hotkey")
        
        if not hotkey_str:
            debug_print("Hotkey nicht konfiguriert.")
            return
        
        debug_print(f"Registriere Hotkey: {hotkey_str}")
        
        def on_activate():
            """Aktion wenn Hotkey gedrückt wird."""
            if self.is_processing:
                # Wenn bereits verarbeitet wird, ignoriere den Hotkey
                debug_print("Verarbeitung läuft bereits, ignoriere Hotkey...")
                return
            
            debug_print(f"Hotkey '{hotkey_str}' aktiviert!")
            self.root.after(0, self.process_selected_text)
        
        def listener_thread_func():
            """Funktion die im Listener Thread läuft."""
            try:
                self.hotkey_listener = keyboard.GlobalHotKeys({hotkey_str: on_activate})
                debug_print(f"Hotkey Listener gestartet mit: {hotkey_str}")
                self.hotkey_listener.run()
            except Exception as e:
                error_msg = f"Fehler beim Registrieren/Ausführen des Hotkeys '{hotkey_str}':\n{e}"
                debug_print(f"Fehler im Listener Thread: {error_msg}")
                traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("Hotkey Fehler", error_msg))
            finally:
                debug_print("Hotkey Listener Thread beendet.")
                self.hotkey_listener = None
        
        self.listener_thread = threading.Thread(target=listener_thread_func, daemon=True)
        self.listener_thread.start()
        time.sleep(0.2)
    
    def stop_hotkey_listener(self):
        """Stoppt den globalen Hotkey Listener."""
        listener = self.hotkey_listener
        if listener:
            debug_print("Stoppe Hotkey Listener...")
            try:
                listener.stop()
                self.hotkey_listener = None
            except Exception as e:
                debug_print(f"Fehler beim Stoppen des Hotkey Listeners: {e}")
        
        thread = self.listener_thread
        if thread and thread.is_alive():
            debug_print("Warte auf Listener Thread...")
            thread.join(timeout=0.5)
            if thread and thread.is_alive():
                debug_print("Warnung: Listener Thread hat nicht gestoppt.")
        self.listener_thread = None
        debug_print("Hotkey Listener gestoppt.")
    
    def process_selected_text(self):
        """Verarbeitet den markierten Text."""
        if self.is_processing:
            if self.debug:
                self.debug.log("Verarbeitung bereits aktiv, ignoriere Hotkey", level="WARNING")
            return
        
        self.is_processing = True
        self.original_text = None
        overall_start = time.time()
        
        if self.debug:
            self.debug.log("=== Text-Verbesserung gestartet ===", level="INFO")
            self.debug.start_timer("overall_processing")
        
        try:
            if not HAS_PYPERCLIP:
                messagebox.showerror("Fehler", "'pyperclip' fehlt.")
                return
            
            try:
                if self.debug:
                    self.debug.start_timer("text_selection")
                
                # Simuliere Ctrl+C um markierten Text zu kopieren
                keyboard_controller = keyboard.Controller()
                
                # Minimale Verzögerung für Stabilität
                time.sleep(0.05)  # Reduziert von 0.1s auf 0.05s
                
                # Leere Clipboard temporär für zuverlässige Änderungserkennung
                pyperclip.copy("")
                time.sleep(0.02)  # Minimale Pause damit Clipboard geleert wird (reduziert von 0.05s)
                
                if self.debug:
                    self.debug.log("Clipboard geleert", "Vor Copy-Befehl")
                
                # Sende Ctrl+C
                keyboard_controller.press(keyboard.Key.ctrl)
                keyboard_controller.press('c')
                keyboard_controller.release('c')
                keyboard_controller.release(keyboard.Key.ctrl)
                
                # Warte bis Clipboard nicht mehr leer ist (mit Timeout)
                start_wait = time.time()
                selected_text = ""
                while time.time() - start_wait < 0.8:  # Max 0.8 Sekunden warten (reduziert von 1.0s)
                    selected_text = pyperclip.paste()
                    if selected_text:
                        break
                    time.sleep(0.03)  # Reduziert von 0.05s auf 0.03s für schnellere Checks
                
                # Falls nach 1 Sekunde immer noch leer, versuche es nochmal
                if not selected_text:
                    if self.debug:
                        self.debug.log("Clipboard nach 1s leer, warte länger...", level="WARNING")
                    time.sleep(0.3)
                    selected_text = pyperclip.paste()
                
                if self.debug:
                    text_selection_time = self.debug.end_timer("text_selection")
                    if text_selection_time is not None:
                        self.debug.log("Text ausgewählt", f"Länge: {len(selected_text)} Zeichen, Dauer: {text_selection_time:.3f}s")
                    else:
                        self.debug.log("Text ausgewählt", f"Länge: {len(selected_text)} Zeichen")
                
                if not selected_text or selected_text.strip() == "":
                    if self.tray_icon:
                        try:
                            self.tray_icon.notify("Kein Text markiert", "Quick Text Improver")
                        except:
                            pass
                    if self.debug:
                        self.debug.log("Kein Text markiert", level="WARNING")
                    debug_print("Kein Text markiert oder Clipboard leer.")
                    self.is_processing = False
                    return
                
                # Speichere ursprünglichen Text für möglichen Abbruch
                self.original_text = selected_text
                
                debug_print(f"Markierter Text: {selected_text[:100]}...")
                
                # Zeige Ladesymbol in Tray
                if self.tray_icon:
                    try:
                        self.tray_icon.notify("Text wird verbessert...", "Quick Text Improver")
                    except:
                        pass
                
                if self.debug:
                    self.debug.start_timer("text_deletion")
                
                # Lösche markierten Text (einmaliges Backspace, da Text noch markiert ist)
                # Minimale Wartezeit vor dem Löschen
                time.sleep(0.05)  # Reduziert von 0.1s auf 0.05s
                # Drücke Backspace einmal, um die Markierung zu löschen
                keyboard_controller.press(keyboard.Key.backspace)
                keyboard_controller.release(keyboard.Key.backspace)
                # Minimale Pause, damit die App reagieren kann
                time.sleep(0.03)  # Reduziert von 0.05s auf 0.03s
                
                if self.debug:
                    deletion_time = self.debug.end_timer("text_deletion")
                    if deletion_time is not None:
                        self.debug.log("Text gelöscht", f"Dauer: {deletion_time:.3f}s")
                    else:
                        self.debug.log("Text gelöscht")
                
                # Verbessere Text mit Gemini Streaming (verwende Einstellungen aus Config)
                api_key = self.config.get("gemini_api_key")
                model = self.config.get("gemini_model")
                system_prompt = self.config.get("system_prompt")
                
                if self.debug:
                    self.debug.log("API-Parameter", f"Modell: {model}, Prompt-Länge: {len(system_prompt)} Zeichen")
                    self.debug.start_timer("api_call")
                    self.debug.start_timer("first_chunk")
                
                # Callback für jeden Chunk - sammle Text (wird am Ende mit Typing-Effekt eingefügt)
                accumulated_text = ""
                chunk_count = 0
                first_chunk_received = False
                
                def on_chunk_received(chunk_text):
                    """Wird für jeden Text-Chunk aufgerufen (im API-Thread)."""
                    nonlocal accumulated_text, chunk_count, first_chunk_received
                    
                    accumulated_text += chunk_text
                    chunk_count += 1
                    
                    if not first_chunk_received:
                        first_chunk_received = True
                        if self.debug:
                            first_chunk_time = self.debug.end_timer("first_chunk")
                            if first_chunk_time is not None:
                                self.debug.log("Erster Chunk erhalten", f"Nach {first_chunk_time:.3f}s")
                            else:
                                self.debug.log("Erster Chunk erhalten")
                    
                    if self.debug and chunk_count % 5 == 0:
                        self.debug.log(f"Chunk {chunk_count} erhalten", f"Akkumulierte Länge: {len(accumulated_text)} Zeichen")
                
                # Starte Streaming in separatem Thread
                improved_text = None
                error_occurred = False
                stream_thread_obj = None
                stream_start_time = time.time()
                stream_timeout = 120  # 2 Minuten Timeout
                
                def stream_thread():
                    nonlocal improved_text, error_occurred
                    # chunk_count wird in on_chunk_received aktualisiert und ist dort verfügbar
                    try:
                        if self.debug:
                            self.debug.log("Starte API-Aufruf im Thread", f"Text-Länge: {len(selected_text)} Zeichen")
                            self.debug.start_timer("api_call")
                        
                        improved_text = improve_text_with_gemini_stream(
                            selected_text,
                            api_key,
                            model,
                            system_prompt,
                            on_chunk_received
                        )
                        
                        # Hole chunk_count aus dem Closure (wird in on_chunk_received aktualisiert)
                        final_chunk_count = chunk_count
                        
                        if self.debug:
                            api_time = self.debug.end_timer("api_call")
                            if improved_text:
                                self.debug.log("API-Aufruf erfolgreich", f"Erhaltener Text: {len(improved_text)} Zeichen")
                                if api_time is not None:
                                    self.debug.log_performance("API-Aufruf", api_time, f"{final_chunk_count} Chunks, {len(improved_text)} Zeichen")
                                else:
                                    self.debug.log("API-Aufruf", f"{final_chunk_count} Chunks, {len(improved_text)} Zeichen")
                            else:
                                self.debug.log("API-Aufruf zurückgegeben: None", level="ERROR")
                        
                        # Sende Nachricht über Queue
                        if error_occurred or not improved_text:
                            error_msg = "Fehler beim Verbessern des Textes. Bitte versuchen Sie es erneut."
                            detailed_msg = error_msg
                            if self.debug:
                                detailed_msg += f"\n\nDebug-Info:\n- Fehler aufgetreten: {error_occurred}\n- Text erhalten: {improved_text is not None}\n- Chunks empfangen: {final_chunk_count}"
                            self.message_queue.put(("error", {
                                "message": error_msg,
                                "detailed": detailed_msg
                            }))
                        else:
                            # Erfolg - sende Daten für Logging
                            if self.debug:
                                overall_time = self.debug.end_timer("overall_processing")
                                if overall_time is not None:
                                    self.debug.log_performance("Gesamte Verarbeitung", overall_time, 
                                                             f"Input: {len(selected_text)} Zeichen, Output: {len(improved_text)} Zeichen, {final_chunk_count} Chunks")
                                else:
                                    self.debug.log("Gesamte Verarbeitung", 
                                                 f"Input: {len(selected_text)} Zeichen, Output: {len(improved_text)} Zeichen, {final_chunk_count} Chunks")
                                self.debug.log("=== Text-Verbesserung abgeschlossen ===", level="INFO")
                            
                            debug_print(f"Verbesserter Text vollständig: {improved_text[:100]}...")
                            self.message_queue.put(("success", {
                                "improved_text": improved_text,
                                "chunk_count": final_chunk_count
                            }))
                    except Exception as e:
                        error_occurred = True
                        if self.debug:
                            self.debug.log_exception("Fehler im Streaming-Thread", e)
                        debug_print(f"Fehler im Streaming-Thread: {e}")
                        traceback.print_exc()
                        error_msg = f"Fehler beim Verbessern des Textes:\n{e}"
                        self.message_queue.put(("error", {
                            "message": error_msg,
                            "detailed": error_msg
                        }))
                
                stream_thread_obj = threading.Thread(target=stream_thread, daemon=True)
                self.stream_thread_obj = stream_thread_obj  # Speichere Referenz
                stream_thread_obj.start()
                
                # Polling statt join() - prüfe Thread-Status ohne GUI zu blockieren
                def check_stream_thread():
                    nonlocal improved_text, error_occurred
                    
                    if stream_thread_obj is None:
                        return
                    
                    if not stream_thread_obj.is_alive():
                        # Thread ist fertig, Queue wird die Nachricht verarbeiten
                        return
                    
                    # Prüfe Timeout
                    elapsed = time.time() - stream_start_time
                    if elapsed > stream_timeout:
                        error_msg = "API-Aufruf hat zu lange gedauert (Timeout nach 2 Minuten)."
                        if self.debug:
                            self.debug.log("API-Timeout", error_msg, level="ERROR")
                        debug_print(error_msg)
                        error_occurred = True
                        improved_text = None
                        self.message_queue.put(("error", {
                            "message": error_msg,
                            "detailed": error_msg
                        }))
                        return
                    
                    # Prüfe erneut in 500ms
                    self.root.after(500, check_stream_thread)
                
                # Starte Polling
                self.root.after(500, check_stream_thread)
                
                # Die Verarbeitung wird jetzt über die Queue abgewickelt
                # Die Funktion kehrt hier zurück, damit die GUI nicht blockiert wird
                # check_stream_thread() und process_queue() übernehmen die weitere Verarbeitung
                return
                
            except Exception as e:
                error_msg = f"Fehler beim Verarbeiten des Textes:\n{e}"
                print(error_msg)
                traceback.print_exc()
                if self.tray_icon:
                    try:
                        self.tray_icon.notify(error_msg, "Quick Text Improver - Fehler")
                    except:
                        pass
                messagebox.showerror("Fehler", error_msg)
            finally:
                # Flags zurücksetzen
                self.is_processing = False
        
        except Exception as e:
            debug_print(f"Unerwarteter Fehler: {e}")
            traceback.print_exc()
            # Flags zurücksetzen
            self.is_processing = False
    
    def type_text_with_effect(self, text, delay_per_char=0.0002):
        """
        Fügt Text mit einem Typing-Effekt ein (Zeichen für Zeichen).
        
        Args:
            text (str): Der einzufügende Text
            delay_per_char (float): Verzögerung pro Zeichen in Sekunden (Standard: 0.0002 = 0.2ms)
        """
        if not text or not HAS_PYNPUT:
            return
        
        keyboard_controller = keyboard.Controller()
        
        if self.debug:
            typing_start = time.time()
            self.debug.log("Starte Typing-Effekt", f"Text-Länge: {len(text)} Zeichen, Delay: {delay_per_char*1000:.1f}ms pro Zeichen")
        
        try:
            # Tippe jedes Zeichen einzeln
            for i, char in enumerate(text):
                try:
                    # Spezielle Behandlung für bestimmte Zeichen
                    if char == '\n':
                        keyboard_controller.press(keyboard.Key.enter)
                        keyboard_controller.release(keyboard.Key.enter)
                    elif char == '\t':
                        keyboard_controller.press(keyboard.Key.tab)
                        keyboard_controller.release(keyboard.Key.tab)
                    elif char == '\r':
                        # Carriage return ignorieren (wird mit \n behandelt)
                        continue
                    else:
                        # Normale Zeichen tippen (keyboard.type() kann auch Unicode)
                        keyboard_controller.type(char)
                    
                    # Sehr kurze Verzögerung zwischen Zeichen (für Stabilität)
                    if delay_per_char > 0:
                        time.sleep(delay_per_char)
                    
                    # Update Status alle 100 Zeichen
                    if (i + 1) % 100 == 0:
                        progress = (i + 1) / len(text) * 100
                        self.message_queue.put(("status", f"Text wird eingefügt... {progress:.0f}%"))
                except Exception as char_error:
                    # Bei Fehler mit einem Zeichen, versuche es zu überspringen
                    if self.debug:
                        self.debug.log(f"Fehler beim Tippen von Zeichen {i+1}", f"Zeichen: {repr(char)}, Fehler: {char_error}", level="WARNING")
                    continue
            
            if self.debug:
                typing_time = time.time() - typing_start
                chars_per_sec = len(text) / typing_time if typing_time > 0 else 0
                self.debug.log("Typing-Effekt abgeschlossen", 
                              f"Dauer: {typing_time:.3f}s, {chars_per_sec:.0f} Zeichen/s")
        
        except Exception as e:
            if self.debug:
                self.debug.log_exception("Fehler beim Typing-Effekt", e)
            debug_print(f"Fehler beim Typing-Effekt: {e}")
            traceback.print_exc()
    
    def insert_text_via_clipboard(self, text):
        """
        Fügt Text über die Zwischenablage ein (Clipboard + Ctrl+V).
        Diese Methode ist schneller als Zeichen-für-Zeichen-Tippen.
        
        Args:
            text (str): Der einzufügende Text
        """
        if not text or not HAS_PYPERCLIP or not HAS_PYNPUT:
            return
        
        if self.debug:
            insert_start = time.time()
            self.debug.log("Starte Text-Einfügen via Clipboard", f"Text-Länge: {len(text)} Zeichen")
        
        try:
            # Kopiere Text in Zwischenablage
            pyperclip.copy(text)
            time.sleep(0.05)  # Kurze Pause damit Clipboard aktualisiert wird
            
            # Kurze Wartezeit, damit die Anwendung bereit ist
            time.sleep(0.1)
            
            # Füge mit Ctrl+V ein
            keyboard_controller = keyboard.Controller()
            keyboard_controller.press(keyboard.Key.ctrl)
            keyboard_controller.press('v')
            keyboard_controller.release('v')
            keyboard_controller.release(keyboard.Key.ctrl)
            time.sleep(0.05)  # Minimale Pause nach dem Einfügen
            
            if self.debug:
                insert_time = time.time() - insert_start
                self.debug.log("Text-Einfügen via Clipboard abgeschlossen", 
                              f"Dauer: {insert_time:.3f}s")
        
        except Exception as e:
            if self.debug:
                self.debug.log_exception("Fehler beim Text-Einfügen via Clipboard", e)
            debug_print(f"Fehler beim Text-Einfügen via Clipboard: {e}")
            traceback.print_exc()
    
    def copy_text_to_clipboard(self, text):
        """
        Kopiert Text nur in die Zwischenablage, ohne ihn einzufügen.
        
        Args:
            text (str): Der zu kopierende Text
        """
        if not text or not HAS_PYPERCLIP:
            return
        
        if self.debug:
            self.debug.log("Kopiere Text in Zwischenablage", f"Text-Länge: {len(text)} Zeichen")
        
        try:
            pyperclip.copy(text)
            if self.debug:
                self.debug.log("Text erfolgreich in Zwischenablage kopiert")
        except Exception as e:
            if self.debug:
                self.debug.log_exception("Fehler beim Kopieren in Zwischenablage", e)
            debug_print(f"Fehler beim Kopieren in Zwischenablage: {e}")
            traceback.print_exc()
    
    def process_queue(self):
        """Verarbeitet Nachrichten vom API-Thread (Thread-sicher für GUI-Updates)."""
        try:
            while True:
                # Hole Nachrichten vom Thread (non-blocking)
                try:
                    msg_type, content = self.message_queue.get_nowait()
                    
                    if msg_type == "error":
                        # Fehler aufgetreten
                        error_msg = content.get("message", "Unbekannter Fehler")
                        detailed_msg = content.get("detailed", error_msg)
                        messagebox.showerror("Fehler", detailed_msg)
                        self.is_processing = False
                    
                    elif msg_type == "success":
                        # Erfolgreich abgeschlossen - verarbeite Text basierend auf Einstellungen
                        improved_text = content.get("improved_text", "")
                        chunk_count = content.get("chunk_count", 0)
                        
                        if improved_text:
                            # Hole Einstellungen
                            insert_method = self.config.get("text_insert_method", "typed")
                            auto_insert = self.config.get("auto_insert_text", True)
                            
                            if not auto_insert:
                                # Nur in Zwischenablage kopieren, nicht einfügen
                                def copy_thread():
                                    try:
                                        self.copy_text_to_clipboard(improved_text)
                                        self.message_queue.put(("insert_complete", {}))
                                    except Exception as e:
                                        if self.debug:
                                            self.debug.log_exception("Fehler im Copy-Thread", e)
                                        debug_print(f"Fehler im Copy-Thread: {e}")
                                        self.message_queue.put(("insert_complete", {}))
                                
                                copy_thread_obj = threading.Thread(target=copy_thread, daemon=True)
                                copy_thread_obj.start()
                            elif insert_method == "clipboard":
                                # Über Clipboard einfügen
                                def clipboard_thread():
                                    try:
                                        # Kurze Pause, damit die Anwendung bereit ist
                                        time.sleep(0.1)
                                        self.insert_text_via_clipboard(improved_text)
                                        self.message_queue.put(("insert_complete", {}))
                                    except Exception as e:
                                        if self.debug:
                                            self.debug.log_exception("Fehler im Clipboard-Thread", e)
                                        debug_print(f"Fehler im Clipboard-Thread: {e}")
                                        self.message_queue.put(("insert_complete", {}))
                                
                                clipboard_thread_obj = threading.Thread(target=clipboard_thread, daemon=True)
                                clipboard_thread_obj.start()
                            else:
                                # Standard: Mit Typing-Effekt einfügen
                                def typing_thread():
                                    try:
                                        # Kurze Pause, damit die Anwendung bereit ist
                                        time.sleep(0.1)
                                        self.type_text_with_effect(improved_text, delay_per_char=0.0002)
                                        self.message_queue.put(("insert_complete", {}))
                                    except Exception as e:
                                        if self.debug:
                                            self.debug.log_exception("Fehler im Typing-Thread", e)
                                        debug_print(f"Fehler im Typing-Thread: {e}")
                                        self.message_queue.put(("insert_complete", {}))
                                
                                typing_thread_obj = threading.Thread(target=typing_thread, daemon=True)
                                typing_thread_obj.start()
                        else:
                            # Kein Text zum Einfügen
                            self.is_processing = False
                    
                    elif msg_type == "insert_complete":
                        # Text-Einfügen/Kopieren abgeschlossen
                        auto_insert = self.config.get("auto_insert_text", True)
                        if auto_insert:
                            # Benachrichtigung
                            if self.tray_icon:
                                try:
                                    self.tray_icon.notify("Text erfolgreich verbessert!", "Quick Text Improver")
                                except:
                                    pass
                            debug_print("Text erfolgreich verbessert und eingefügt.")
                        else:
                            # Benachrichtigung für nur Clipboard
                            if self.tray_icon:
                                try:
                                    self.tray_icon.notify("Text in Zwischenablage kopiert!", "Quick Text Improver")
                                except:
                                    pass
                            debug_print("Text erfolgreich verbessert und in Zwischenablage kopiert.")
                        self.is_processing = False
                    
                    elif msg_type == "typing_complete":
                        # Typing-Effekt abgeschlossen (Legacy - wird durch insert_complete ersetzt)
                        # Benachrichtigung
                        if self.tray_icon:
                            try:
                                self.tray_icon.notify("Text erfolgreich verbessert!", "Text Improver")
                            except:
                                pass
                        
                        debug_print("Text erfolgreich verbessert und eingefügt.")
                        self.is_processing = False
                    
                    elif msg_type == "typing_complete":
                        # Typing-Effekt abgeschlossen
                        # Benachrichtigung
                        if self.tray_icon:
                            try:
                                self.tray_icon.notify("Text erfolgreich verbessert!", "Text Improver")
                            except:
                                pass
                        
                        debug_print("Text erfolgreich verbessert und eingefügt.")
                        self.is_processing = False
                    
                    self.message_queue.task_done()
                except queue.Empty:
                    break
        except Exception as e:
            debug_print(f"Fehler beim Verarbeiten der Queue: {e}")
            traceback.print_exc()
        finally:
            # Prüfe erneut in 100ms
            self.root.after(100, self.process_queue)
    
    def quit_app(self):
        """Räumt Ressourcen auf und beendet die Anwendung."""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        debug_print("Beenden angefordert. Räume auf...")
        
        self.stop_hotkey_listener()
        
        # Schließe Debug-Fenster falls offen
        if self.debug_window_instance and self.debug_window_instance.winfo_exists():
            try:
                self.debug_window_instance.destroy()
            except:
                pass
            self.debug_window_instance = None
        
        # Schließe Settings-Fenster falls offen
        if self.settings_window_instance and self.settings_window_instance.winfo_exists():
            try:
                self.settings_window_instance.destroy()
            except:
                pass
            self.settings_window_instance = None
        
        if self.tray_icon:
            debug_print("Stoppe Tray Icon...")
            self.tray_icon.stop()
        
        if self.tray_thread and self.tray_thread.is_alive():
            debug_print("Warte auf Tray Thread...")
            self.tray_thread.join(timeout=0.5)
        
        debug_print("Zerstöre Tkinter Root...")
        try:
            if self.root.winfo_exists():
                self.root.destroy()
                debug_print("Tkinter Root zerstört.")
        except tk.TclError as e:
            debug_print(f"TclError beim Zerstören des Root: {e}")
        
        debug_print("Anwendung beendet.")

# --- Application Entry Point ---
if __name__ == "__main__":
    # Lock File Handling
    lock_file_path = os.path.join(
        os.getenv('TEMP', os.getenv('TMP', '/tmp')),
        'textimprover_instance.lock'
    )
    lock_file_handle = None
    current_pid = os.getpid()
    app_already_running = False
    
    try:
        lock_file_handle = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(lock_file_handle, str(current_pid).encode())
            debug_print(f"Lock File erstellt: {lock_file_path} mit PID: {current_pid}")
        except OSError as e_write:
            debug_print(f"Warnung: Konnte PID nicht in Lock File schreiben: {e_write}")
    except FileExistsError:
        debug_print(f"Lock File {lock_file_path} existiert bereits. Prüfe PID...")
        old_pid = None
        try:
            with open(lock_file_path, 'r') as f_lock:
                pid_str = f_lock.read().strip()
                if pid_str:
                    old_pid = int(pid_str)
        except (IOError, ValueError) as e_read:
            debug_print(f"Warnung: Konnte PID aus Lock File nicht lesen: {e_read}. Nehme an, dass es veraltet ist.")
        
        # Prüfe ob der Prozess noch läuft
        if old_pid is not None and HAS_PSUTIL:
            try:
                if psutil.pid_exists(old_pid):
                    try:
                        proc = psutil.Process(old_pid)
                        proc_name = proc.name().lower()
                        if 'python' in proc_name or 'textimprover' in proc_name or 'main.py' in ' '.join(proc.cmdline()).lower():
                            debug_print(f"Eine andere Instanz läuft (PID {old_pid} existiert). Beende.")
                            app_already_running = True
                        else:
                            debug_print(f"PID {old_pid} existiert, aber ist nicht Quick Text Improver. Nehme an, dass Lock File veraltet ist.")
                            old_pid = None
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        debug_print(f"PID {old_pid} nicht gefunden/Zugriff verweigert. Nehme an, dass Lock File veraltet ist.")
                        old_pid = None
                else:
                    debug_print(f"PID {old_pid} nicht gefunden. Lock File ist veraltet.")
                    old_pid = None
            except Exception as e_psutil:
                debug_print(f"Fehler beim Prüfen von PID {old_pid}: {e_psutil}. Nehme an, dass Lock File veraltet ist.")
                old_pid = None
        elif old_pid is not None and not HAS_PSUTIL:
            debug_print("Warnung: psutil nicht gefunden. Versuche Lock File zu entfernen...")
            old_pid = None
        
        # Wenn Lock File veraltet ist, entferne es und erstelle ein neues
        if not app_already_running:
            try:
                debug_print("Versuche veraltetes Lock File zu entfernen...")
                os.remove(lock_file_path)
                lock_file_handle = os.open(lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(lock_file_handle, str(current_pid).encode())
                debug_print(f"Lock File neu erstellt mit neuer PID: {current_pid}")
            except Exception as e_recreate:
                debug_print(f"Fehler beim Neuerstellen des Lock Files: {e_recreate}. Beende.")
                app_already_running = True
    except Exception as e_lock_init:
        debug_print(f"Unerwarteter Fehler beim Lock File Handling: {e_lock_init}")
        app_already_running = True
    
    if app_already_running:
        root_check = tk.Tk()
        root_check.withdraw()
        messagebox.showerror(
            "Quick Text Improver",
            "Eine andere Instanz läuft bereits oder Lock-Datei-Problem."
        )
        root_check.destroy()
        sys.exit(1)
    
    debug_print("Starte Quick Text Improver Anwendung...")
    
    if not HAS_PYNPUT:
        root_check = tk.Tk()
        root_check.withdraw()
        messagebox.showerror(
            "Kritischer Fehler",
            "'pynput' fehlt.\nInstallieren: pip install pynput"
        )
        root_check.destroy()
        sys.exit("Fehler: pynput nicht gefunden.")
    
    if not HAS_PYPERCLIP:
        root_check = tk.Tk()
        root_check.withdraw()
        messagebox.showerror(
            "Kritischer Fehler",
            "'pyperclip' fehlt.\nInstallieren: pip install pyperclip"
        )
        root_check.destroy()
        sys.exit("Fehler: pyperclip nicht gefunden.")
    
    app = None
    root = tk.Tk()
    
    # Verstecke Konsolenfenster erneut (falls es wieder angezeigt wurde)
    hide_console_if_needed()
    
    try:
        app = TextImproverApp(root)
        
        # Verstecke Konsolenfenster nochmal nach App-Initialisierung
        hide_console_if_needed()
        
        debug_print("Starte Tkinter Main Loop...")
        root.mainloop()
        debug_print("Main Loop normal beendet.")
    except KeyboardInterrupt:
        debug_print("\nKeyboardInterrupt. Beende...")
        if app:
            try:
                app.quit_app()
            except Exception as quit_e:
                debug_print(f"Fehler beim Beenden nach KBI: {quit_e}")
        elif 'root' in locals() and root.winfo_exists():
            root.destroy()
    except Exception as e:
        debug_print("\nUnerwartete Ausnahme:")
        traceback.print_exc()
        if app:
            try:
                app.quit_app()
            except Exception as quit_e:
                debug_print(f"Fehler beim Beenden nach Ausnahme: {quit_e}")
        elif 'root' in locals() and root.winfo_exists():
            root.destroy()
    finally:
        debug_print("Betrete finalen Cleanup...")
        if lock_file_handle is not None:
            try:
                os.close(lock_file_handle)
                if os.path.exists(lock_file_path):
                    pid_in_file = -1
                    try:
                        with open(lock_file_path, 'r') as f_final:
                            pid_in_file = int(f_final.read().strip())
                    except Exception:
                        pass
                    if pid_in_file == current_pid:
                        os.remove(lock_file_path)
                        debug_print("Lock File entfernt.")
                    else:
                        debug_print(f"Lock File PID ({pid_in_file}) != aktuelle PID ({current_pid}). Nicht entfernen.")
                else:
                    debug_print("Lock File bereits entfernt.")
            except Exception as e_lock:
                debug_print(f"Fehler beim Schließen/Entfernen des Lock Files: {e_lock}")
        
        if app and hasattr(app, 'is_shutting_down') and not app.is_shutting_down:
            debug_print("Main Loop unerwartet beendet, versuche finalen Cleanup...")
            try:
                app.quit_app()
            except Exception as quit_e:
                debug_print(f"Fehler beim finalen Cleanup: {quit_e}")
        
        debug_print("Anwendung beendet.")
