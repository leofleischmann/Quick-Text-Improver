# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import traceback

try:
    from pynput import keyboard
    HAS_PYNPUT_SETTINGS = True
except ImportError:
    HAS_PYNPUT_SETTINGS = False


class SettingsWindow(tk.Toplevel):
    """Settings window for Quick Text Improver configuration with improved design."""
    
    def __init__(self, parent, config_manager, on_close_callback):
        super().__init__(parent)
        self.config = config_manager
        self.on_close_callback = on_close_callback
        self.title("Quick Text Improver - Einstellungen")
        
        # Window geometry - besser angepasst
        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            win_width = min(700, int(screen_width * 0.6))
            win_height = min(650, int(screen_height * 0.75))
            pos_x = (screen_width - win_width) // 2
            pos_y = (screen_height - win_height) // 2
            self.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
        except:
            self.geometry("700x650")
        
        self.minsize(600, 500)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Styling - verbessert
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            style.theme_use('default')
        
        # Verbesserte Styling-Konfiguration
        style.configure("TLabel", padding=(5, 3))
        style.configure("TEntry", padding=(5, 5))
        style.configure("TButton", padding=(10, 5))
        style.configure("TCheckbutton", padding=(0, 5), font=("", 9))
        style.configure("TLabelframe", padding=15)
        style.configure("TLabelframe.Label", padding=(5, 5), font=("", 10, "bold"))
        
        # Hauptcontainer
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Scrollable area mit verbessertem Layout
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0, bg=self.cget("bg"))
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def _on_canvas_configure(event):
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        scrollable_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Populate settings
        self._populate_settings(scrollable_frame)
        
        # Button frame - verbessert mit besserem Spacing
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill="x", pady=(5, 0))
        
        # Separator
        ttk.Separator(button_frame, orient="horizontal").pack(fill="x", pady=(0, 10))
        
        # Buttons mit besserem Layout
        button_inner = ttk.Frame(button_frame)
        button_inner.pack(side="right", padx=5)
        
        cancel_btn = ttk.Button(button_inner, text="Abbrechen", command=self.on_close, width=12)
        cancel_btn.pack(side="right", padx=(5, 0))
        
        save_btn = ttk.Button(button_inner, text="Speichern", command=self.save_settings, width=12)
        save_btn.pack(side="right", padx=5)
        
        # Fokus auf Speichern-Button
        save_btn.focus_set()
        
        self.wait_visibility()
        self.focus_set()
        self.grab_set()
    
    def _populate_settings(self, parent):
        """Populates the settings frame with all configuration options."""
        
        # Gemini API Settings - verbessertes Layout
        api_frame = ttk.Labelframe(parent, text="Gemini API Einstellungen", padding="15")
        api_frame.pack(fill="x", pady=(0, 15), padx=10)
        
        # API Key mit besserem Layout
        api_key_row = ttk.Frame(api_frame)
        api_key_row.pack(fill="x", pady=(0, 10))
        
        ttk.Label(api_key_row, text="API Key:", font=("", 9)).pack(side="left", padx=(0, 10))
        self.api_key_var = tk.StringVar(value=self.config.get("gemini_api_key"))
        api_key_entry = ttk.Entry(api_key_row, textvariable=self.api_key_var, width=55, show="*", font=("Consolas", 9))
        api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Show/Hide Button für API Key
        def toggle_api_key_visibility():
            if api_key_entry.cget("show") == "*":
                api_key_entry.config(show="")
                toggle_btn.config(text="Verbergen")
            else:
                api_key_entry.config(show="*")
                toggle_btn.config(text="Anzeigen")
        
        toggle_btn = ttk.Button(api_key_row, text="Anzeigen", width=10, command=toggle_api_key_visibility)
        toggle_btn.pack(side="left")
        
        # Help text für API Key
        help_text1 = ttk.Label(api_frame, text="Ihr Gemini API Key. Wird sicher gespeichert.", 
                               font=("", 8), foreground="gray")
        help_text1.pack(anchor="w", pady=(0, 15))
        
        # Model mit besserem Layout
        model_row = ttk.Frame(api_frame)
        model_row.pack(fill="x", pady=(0, 10))
        
        ttk.Label(model_row, text="Modell:", font=("", 9)).pack(side="left", padx=(0, 10))
        self.model_var = tk.StringVar(value=self.config.get("gemini_model"))
        model_combo = ttk.Combobox(model_row, textvariable=self.model_var, width=52, state="readonly", font=("", 9))
        model_combo['values'] = (
            "gemini-3-pro-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite"
        )
        model_combo.pack(side="left", fill="x", expand=True)
        
        # Help text für Modell
        help_text2 = ttk.Label(api_frame, text="Wählen Sie das Gemini-Modell. Flash ist schneller, Pro ist genauer.", 
                               font=("", 8), foreground="gray")
        help_text2.pack(anchor="w", pady=(0, 15))
        
        # System Prompt mit besserem Layout
        prompt_row = ttk.Frame(api_frame)
        prompt_row.pack(fill="x", pady=(0, 5))
        
        ttk.Label(prompt_row, text="System Prompt:", font=("", 9)).pack(anchor="nw", padx=(0, 10))
        
        prompt_container = ttk.Frame(api_frame)
        prompt_container.pack(fill="both", expand=True)
        
        self.prompt_text_widget = tk.Text(prompt_container, width=60, height=5, wrap=tk.WORD, 
                                          font=("", 9), relief="solid", borderwidth=1)
        self.prompt_text_widget.insert("1.0", self.config.get("system_prompt"))
        self.prompt_text_widget.pack(fill="both", expand=True, pady=(5, 0))
        
        # Scrollbar für Prompt
        prompt_scrollbar = ttk.Scrollbar(prompt_container, orient="vertical", 
                                         command=self.prompt_text_widget.yview)
        self.prompt_text_widget.configure(yscrollcommand=prompt_scrollbar.set)
        prompt_scrollbar.pack(side="right", fill="y")
        
        # Help text für System Prompt
        help_text3 = ttk.Label(api_frame, text="Der Prompt, der an Gemini gesendet wird. Der zu verbessernde Text wird automatisch angehängt.", 
                               font=("", 8), foreground="gray", wraplength=600)
        help_text3.pack(anchor="w", pady=(5, 0))
        
        # Hotkey Settings - verbessert
        hotkey_frame = ttk.Labelframe(parent, text="Hotkey Einstellungen", padding="15")
        hotkey_frame.pack(fill="x", pady=(0, 15), padx=10)
        
        hotkey_row = ttk.Frame(hotkey_frame)
        hotkey_row.pack(fill="x", pady=(0, 5))
        
        ttk.Label(hotkey_row, text="Hotkey:", font=("", 9)).pack(side="left", padx=(0, 10))
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey"))
        self.hotkey_entry = ttk.Entry(hotkey_row, textvariable=self.hotkey_var, width=40, font=("Consolas", 9))
        self.hotkey_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Hotkey Aufnahme Button
        self.recording_active = False
        self.pressed_keys = set()
        self.hotkey_listener = None
        self.record_button = ttk.Button(hotkey_row, text="Hotkey aufnehmen", command=self._start_hotkey_recording, width=15)
        self.record_button.pack(side="left")
        
        # Help text für Hotkey
        help_text4 = ttk.Label(hotkey_frame, 
                               text="Format: <ctrl>+r, <ctrl>+<shift>+r, <alt>+r, etc. Der Hotkey wird global registriert. Klicken Sie auf 'Hotkey aufnehmen' um eine Tastenkombination aufzunehmen.", 
                               font=("", 8), foreground="gray", wraplength=600)
        help_text4.pack(anchor="w", pady=(5, 0))
        
        # Text Insert Settings
        insert_frame = ttk.Labelframe(parent, text="Text-Einfüge Einstellungen", padding="15")
        insert_frame.pack(fill="x", pady=(0, 15), padx=10)
        
        # Text-Einfüge-Methode
        method_row = ttk.Frame(insert_frame)
        method_row.pack(fill="x", pady=(0, 10))
        
        ttk.Label(method_row, text="Einfüge-Methode:", font=("", 9)).pack(side="left", padx=(0, 10))
        self.insert_method_var = tk.StringVar(value=self.config.get("text_insert_method", "typed"))
        method_combo = ttk.Combobox(method_row, textvariable=self.insert_method_var, width=30, state="readonly", font=("", 9))
        method_combo['values'] = ("typed", "clipboard")
        method_combo.pack(side="left", fill="x", expand=True)
        
        # Help text für Einfüge-Methode
        help_text_method = ttk.Label(insert_frame, 
                                     text="'Getippt': Text wird Zeichen für Zeichen eingetippt. 'Clipboard': Text wird über Zwischenablage (Ctrl+V) eingefügt (schneller).", 
                                     font=("", 8), foreground="gray", wraplength=600)
        help_text_method.pack(anchor="w", pady=(0, 15))
        
        # Auto-Einfügen Option
        self.auto_insert_var = tk.BooleanVar(value=self.config.get("auto_insert_text", True))
        auto_insert_check = ttk.Checkbutton(
            insert_frame,
            text="Text automatisch einfügen",
            variable=self.auto_insert_var
        )
        auto_insert_check.pack(anchor="w", pady=5)
        
        # Help text für Auto-Einfügen
        help_text_auto = ttk.Label(insert_frame, 
                                   text="Wenn deaktiviert, wird der verbesserte Text nur in die Zwischenablage kopiert, aber nicht automatisch eingefügt.", 
                                   font=("", 8), foreground="gray", wraplength=600)
        help_text_auto.pack(anchor="w", pady=(0, 0))
        
        # Debug Settings
        debug_frame = ttk.Labelframe(parent, text="Debug Einstellungen", padding="15")
        debug_frame.pack(fill="x", pady=(0, 15), padx=10)
        
        self.debug_enabled_var = tk.BooleanVar(value=self.config.get("debug_enabled"))
        debug_check = ttk.Checkbutton(
            debug_frame,
            text="Debug-Modus aktivieren",
            variable=self.debug_enabled_var
        )
        debug_check.pack(anchor="w", pady=5)
        
        help_text6 = ttk.Label(debug_frame, 
                               text="Aktiviert detailliertes Logging für Performance-Analyse und Fehlerdiagnose. Debug-Ausgaben werden nur in der Konsole angezeigt (wenn aktiviert).", 
                               font=("", 8), foreground="gray", wraplength=600)
        help_text6.pack(anchor="w", pady=(0, 0))
    
    def save_settings(self):
        """Saves all settings to the config manager."""
        try:
            # Validate and save API Key
            api_key = self.api_key_var.get().strip()
            if not api_key:
                messagebox.showerror("Fehler", "API Key darf nicht leer sein.")
                return
            self.config.set("gemini_api_key", api_key)
            
            # Validate and save Model
            model = self.model_var.get().strip()
            if not model:
                messagebox.showerror("Fehler", "Modell darf nicht leer sein.")
                return
            self.config.set("gemini_model", model)
            
            # Save System Prompt
            prompt = self.prompt_text_widget.get("1.0", tk.END).strip()
            if not prompt:
                messagebox.showerror("Fehler", "System Prompt darf nicht leer sein.")
                return
            self.config.set("system_prompt", prompt)
            
            # Validate and save Hotkey
            hotkey = self.hotkey_var.get().strip()
            if not hotkey:
                messagebox.showerror("Fehler", "Hotkey darf nicht leer sein.")
                return
            
            # Test hotkey format
            if HAS_PYNPUT_SETTINGS:
                try:
                    # Try to create a test listener to validate the hotkey
                    test_listener = keyboard.GlobalHotKeys({hotkey: lambda: None})
                    test_listener.stop()
                except Exception as e:
                    messagebox.showerror(
                        "Hotkey Fehler",
                        f"Ungültiges Hotkey-Format: {hotkey}\n\nFehler: {e}\n\nBeispiel: <ctrl>+r"
                    )
                    return
            
            self.config.set("hotkey", hotkey)
            
            # Save text insert settings
            insert_method = self.insert_method_var.get().strip()
            if insert_method not in ("typed", "clipboard"):
                messagebox.showerror("Fehler", "Ungültige Einfüge-Methode.")
                return
            self.config.set("text_insert_method", insert_method)
            self.config.set("auto_insert_text", self.auto_insert_var.get())
            
            # Save other settings
            self.config.set("debug_enabled", self.debug_enabled_var.get())
            # debug_log_to_file wird nicht mehr verwendet - immer False
            self.config.set("debug_log_to_file", False)
            
            # Save to file
            self.config.save_settings()
            
            # Warnung wenn Debug aktiviert
            if self.debug_enabled_var.get():
                messagebox.showinfo(
                    "Debug aktiviert",
                    "Debug-Modus wurde aktiviert.\n\n"
                    "Bitte starten Sie die Anwendung neu, damit die Änderungen wirksam werden.\n\n"
                    "Debug-Logs werden in der Konsole ausgegeben."
                )
            
            messagebox.showinfo("Erfolg", "Einstellungen wurden erfolgreich gespeichert.")
            self.on_close()
            
        except Exception as e:
            error_msg = f"Fehler beim Speichern der Einstellungen:\n{e}"
            print(error_msg)
            traceback.print_exc()
            messagebox.showerror("Fehler", error_msg)
    
    def _start_hotkey_recording(self):
        """Startet die Hotkey-Aufnahme."""
        if not HAS_PYNPUT_SETTINGS:
            messagebox.showerror("Fehler", "'pynput' fehlt. Hotkey-Aufnahme nicht möglich.", parent=self)
            return
        
        if self.recording_active:
            return
        
        self.recording_active = True
        self.pressed_keys = set()
        self.captured_hotkey = None  # Speichere den finalen Hotkey
        self.hotkey_entry.config(state="readonly")
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, "Drücke Tastenkombination...")
        self.record_button.config(text="Aufnahme läuft...", state="disabled")
        
        # Starte Listener für Tastendrücke
        def on_press(key):
            try:
                if not self.recording_active:
                    return False
                
                # Konvertiere Key zu String
                key_name = None
                if hasattr(key, 'char') and key.char:
                    # Normale Zeichen haben Vorrang (z.B. 'r', 'a', etc.)
                    key_name = key.char
                elif hasattr(key, 'name'):
                    # Spezielle Tasten (ctrl, alt, shift, Funktionstasten, etc.)
                    key_name = key.name
                
                if key_name and key_name not in self.pressed_keys:
                    self.pressed_keys.add(key_name)
                    # GUI-Update im Hauptthread
                    self.after(0, self._update_hotkey_display)
            except Exception:
                pass
        
        def on_release(key):
            try:
                if not self.recording_active:
                    return False
                
                # Entferne Taste aus gedrückten Tasten
                key_name = None
                if hasattr(key, 'char') and key.char:
                    key_name = key.char
                elif hasattr(key, 'name'):
                    key_name = key.name
                
                if key_name and key_name in self.pressed_keys:
                    # Speichere den aktuellen Hotkey, bevor wir die Taste entfernen
                    if len(self.pressed_keys) > 1:  # Wenn noch andere Tasten gedrückt sind
                        self.captured_hotkey = self._format_hotkey_string(self.pressed_keys)
                    
                    self.pressed_keys.discard(key_name)
                    
                    # Wenn keine Tasten mehr gedrückt sind, beende Aufnahme
                    if not self.pressed_keys:
                        # Verwende den gespeicherten Hotkey falls vorhanden
                        if self.captured_hotkey:
                            self.after(0, lambda: self._finalize_hotkey(self.captured_hotkey))
                        else:
                            self.after(0, self._stop_hotkey_recording)
            except Exception:
                pass
        
        try:
            self.hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self.hotkey_listener.start()
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Starten der Hotkey-Aufnahme:\n{e}", parent=self)
            self._stop_hotkey_recording()
    
    def _format_hotkey_string(self, keys):
        """Formatiert eine Menge von Tasten zu einem pynput-Hotkey-String."""
        modifiers = []
        main_key = None
        
        # Mapping für Modifier-Tasten
        modifier_map = {
            'ctrl': 'ctrl', 'control': 'ctrl', 'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
            'alt': 'alt', 'alt_l': 'alt', 'alt_r': 'alt', 'alt_gr': 'alt',
            'shift': 'shift', 'shift_l': 'shift', 'shift_r': 'shift',
            'cmd': 'cmd', 'cmd_l': 'cmd', 'cmd_r': 'cmd', 'super': 'cmd'
        }
        
        # Liste aller bekannten Modifier-Namen
        all_modifier_names = set(modifier_map.keys())
        
        for key in keys:
            key_str = str(key)
            key_lower = key_str.lower()
            
            if key_lower in modifier_map:
                mod = modifier_map[key_lower]
                if mod not in modifiers:
                    modifiers.append(mod)
            elif key_lower not in all_modifier_names:
                # Haupttaste (alles was kein Modifier ist)
                if main_key is None:
                    main_key = key_str
        
        if not main_key:
            return None
        
        # Erstelle Hotkey-String im pynput-Format
        hotkey_parts = []
        # Sortiere Modifier in konsistenter Reihenfolge
        modifier_order = ['ctrl', 'alt', 'shift', 'cmd']
        for mod in modifier_order:
            if mod in modifiers:
                hotkey_parts.append(f"<{mod}>")
        
        # Füge Haupttaste hinzu
        if len(main_key) == 1:
            hotkey_parts.append(main_key.lower())
        else:
            # Für spezielle Tasten wie 'space', 'enter', etc.
            hotkey_parts.append(main_key.lower())
        
        return "+".join(hotkey_parts)
    
    def _update_hotkey_display(self):
        """Aktualisiert die Anzeige des aufgenommenen Hotkeys."""
        if not self.pressed_keys:
            return
        
        hotkey_str = self._format_hotkey_string(self.pressed_keys)
        
        if hotkey_str:
            self.hotkey_entry.config(state="normal")
            self.hotkey_entry.delete(0, tk.END)
            self.hotkey_entry.insert(0, hotkey_str)
            self.hotkey_var.set(hotkey_str)
            self.hotkey_entry.config(state="readonly")
        else:
            # Nur Modifier, keine Haupttaste - zeige Zwischenstand
            modifiers = []
            modifier_map = {
                'ctrl': 'ctrl', 'control': 'ctrl', 'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
                'alt': 'alt', 'alt_l': 'alt', 'alt_r': 'alt', 'alt_gr': 'alt',
                'shift': 'shift', 'shift_l': 'shift', 'shift_r': 'shift',
                'cmd': 'cmd', 'cmd_l': 'cmd', 'cmd_r': 'cmd', 'super': 'cmd'
            }
            for key in self.pressed_keys:
                key_lower = str(key).lower()
                if key_lower in modifier_map:
                    mod = modifier_map[key_lower]
                    if mod not in modifiers:
                        modifiers.append(mod)
            
            if modifiers:
                hotkey_parts = []
                modifier_order = ['ctrl', 'alt', 'shift', 'cmd']
                for mod in modifier_order:
                    if mod in modifiers:
                        hotkey_parts.append(f"<{mod}>")
                hotkey_str = "+".join(hotkey_parts) + "+..."
                self.hotkey_entry.config(state="normal")
                self.hotkey_entry.delete(0, tk.END)
                self.hotkey_entry.insert(0, hotkey_str)
                self.hotkey_entry.config(state="readonly")
    
    def _finalize_hotkey(self, hotkey_str):
        """Finalisiert den aufgenommenen Hotkey."""
        if hotkey_str:
            self.hotkey_entry.config(state="normal")
            self.hotkey_entry.delete(0, tk.END)
            self.hotkey_entry.insert(0, hotkey_str)
            self.hotkey_var.set(hotkey_str)
            self.hotkey_entry.config(state="readonly")
        
        self._stop_hotkey_recording()
    
    def _stop_hotkey_recording(self):
        """Beendet die Hotkey-Aufnahme."""
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except:
                pass
            self.hotkey_listener = None
        
        self.recording_active = False
        self.record_button.config(text="Hotkey aufnehmen", state="normal")
        self.hotkey_entry.config(state="normal")
        
        # Wenn kein Hotkey aufgenommen wurde, setze zurück
        current_value = self.hotkey_var.get()
        if not current_value or current_value == "Drücke Tastenkombination...":
            self.hotkey_var.set(self.config.get("hotkey"))
    
    def on_close(self):
        """Handles window close event."""
        # Stoppe Hotkey-Aufnahme falls aktiv
        if self.recording_active:
            self._stop_hotkey_recording()
        
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
