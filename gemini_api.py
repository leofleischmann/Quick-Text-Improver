# -*- coding: utf-8 -*-

import os
import time
import traceback

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("FATAL ERROR: 'google-genai' not found.")
    print("Install with: pip install google-genai")

# Debug Logger Import
try:
    from debug_logger import get_debug_logger
except ImportError:
    get_debug_logger = None


def improve_text_with_gemini_stream(text, api_key, model, system_prompt, on_chunk_callback):
    """
    Sendet Text an Gemini API mit Streaming und ruft für jeden Chunk einen Callback auf.
    
    Args:
        text (str): Der zu verbessernde Text
        api_key (str): Der Gemini API Key
        model (str): Das zu verwendende Gemini Modell
        system_prompt (str): Der System Prompt für die Verbesserung
        on_chunk_callback (callable): Funktion die für jeden Text-Chunk aufgerufen wird (chunk_text)
        
    Returns:
        str: Der vollständige verbesserte Text oder None bei Fehler
    """
    if not HAS_GENAI:
        return None
    
    if not text or not text.strip():
        return None
    
    debug = get_debug_logger() if get_debug_logger else None
    
    try:
        if debug:
            debug.start_timer("api_setup")
            debug.log("Initialisiere Gemini API", f"Modell: {model}, API Key vorhanden: {bool(api_key)}")
        
        # Erstelle Client mit direkt übergebenem API Key (sauberer als Umgebungsvariable)
        try:
            # Versuche API Key direkt zu übergeben (neue SDK-Version)
            try:
                client = genai.Client(api_key=api_key)
                if debug:
                    debug.log("Client erstellt", "Mit direktem API Key")
            except TypeError:
                # Fallback: Falls Client keine api_key Parameter akzeptiert, verwende Umgebungsvariable
                if 'GEMINI_API_KEY' not in os.environ:
                    os.environ['GEMINI_API_KEY'] = api_key
                    if debug:
                        debug.log("API Key in Umgebungsvariable gesetzt (Fallback)", f"Länge: {len(api_key)} Zeichen")
                client = genai.Client()
                if debug:
                    debug.log("Client erstellt", "Mit Umgebungsvariable (Fallback)")
        except Exception as e:
            if debug:
                debug.log_exception("Fehler beim Erstellen des Clients", e)
            print(f"Fehler beim Erstellen des Gemini Clients: {e}")
            traceback.print_exc()
            return None
        
        if debug:
            setup_time = debug.end_timer("api_setup")
            if setup_time is not None:
                debug.log("API Client erstellt", f"Dauer: {setup_time:.3f}s")
            else:
                debug.log("API Client erstellt")
            debug.start_timer("prompt_creation")
        
        # Erstelle den Prompt
        prompt = f"{system_prompt}\n\n{text}"
        
        if debug:
            prompt_time = debug.end_timer("prompt_creation")
            if prompt_time is not None:
                debug.log("Prompt erstellt", f"Länge: {len(prompt)} Zeichen, Dauer: {prompt_time:.3f}s")
            else:
                debug.log("Prompt erstellt", f"Länge: {len(prompt)} Zeichen")
            debug.log("Prompt Vorschau", f"{prompt[:100]}...", level="DEBUG")
            debug.start_timer("api_request")
        
        # Validierung
        if not prompt or not prompt.strip():
            if debug:
                debug.log("Prompt ist leer", level="ERROR")
            print("FEHLER: Prompt ist leer!")
            return None
        
        # Sende Anfrage an Gemini mit Streaming
        full_text = ""
        chunk_count = 0
        
        # Versuche Streaming-API
        streaming_success = False
        
        # Streaming-Methode: generate_content_stream
        try:
            if debug:
                debug.log("Verwende generate_content_stream für Streaming", f"Modell: {model}")
            
            response = client.models.generate_content_stream(
                model=model,
                contents=prompt
            )
            
            if debug:
                request_time = debug.end_timer("api_request")
                if request_time is not None:
                    debug.log("API-Request gesendet (Stream)", f"Dauer bis Response: {request_time:.3f}s")
                debug.start_timer("streaming")
                debug.start_timer("first_chunk_wait")
            
            # Verarbeite jeden Chunk aus dem Stream
            chunks_processed = 0
            first_chunk_received = False
            
            for chunk in response:
                chunks_processed += 1
                chunk_text = None
                
                if debug and chunks_processed == 1:
                    debug.log("Erster Chunk-Objekt erhalten", f"Typ: {type(chunk)}, Hat text: {hasattr(chunk, 'text')}, Hat candidates: {hasattr(chunk, 'candidates')}")
                
                # Versuche verschiedene Möglichkeiten, Text aus Chunk zu extrahieren
                # Methode 1: Direktes text-Attribut (häufigste Methode im neuen SDK)
                chunk_text = getattr(chunk, "text", None)
                
                # Methode 2: Über candidates (Fallback für ältere SDK-Versionen)
                if not chunk_text and hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        chunk_text = part.text
                                        break
                            elif hasattr(candidate.content, 'text'):
                                chunk_text = candidate.content.text
                                break
                        if chunk_text:
                            break
                
                if chunk_text:
                    full_text += chunk_text
                    chunk_count += 1
                    
                    if debug and not first_chunk_received:
                        first_chunk_received = True
                        first_chunk_time = debug.end_timer("first_chunk_wait")
                        if first_chunk_time is not None:
                            debug.log("Erster Text-Chunk erhalten", f"Nach {first_chunk_time:.3f}s, Text: {chunk_text[:50]}...")
                        else:
                            debug.log("Erster Text-Chunk erhalten", f"Text: {chunk_text[:50]}...")
                    
                    # Rufe Callback für jeden Chunk auf (vollständiger Text wird auf einmal übergeben)
                    if on_chunk_callback:
                        try:
                            on_chunk_callback(chunk_text)
                        except Exception as callback_error:
                            if debug:
                                debug.log_exception("Fehler im Chunk-Callback", callback_error)
                            print(f"Fehler im Chunk-Callback: {callback_error}")
                else:
                    if debug:
                        debug.log(f"Chunk {chunks_processed} ohne Text", 
                                f"Typ: {type(chunk)}, Hat text: {hasattr(chunk, 'text')}, Hat candidates: {hasattr(chunk, 'candidates')}", 
                                level="WARNING")
            
            if debug:
                debug.log("Chunk-Verarbeitung abgeschlossen", f"{chunks_processed} Chunk-Objekte verarbeitet, {chunk_count} mit Text")
            
            if chunk_count == 0:
                if debug:
                    debug.log("KEINE CHUNKS EMPFANGEN", f"{chunks_processed} Chunk-Objekte verarbeitet, aber kein Text extrahiert", level="ERROR")
                print("WARNUNG: Keine Text-Chunks von Streaming-API erhalten!")
                streaming_success = False
            else:
                streaming_success = True
                
                if debug:
                    streaming_time = debug.end_timer("streaming")
                    if streaming_time is not None:
                        debug.log("Streaming abgeschlossen", f"{chunk_count} Chunks, Dauer: {streaming_time:.3f}s, Gesamttext: {len(full_text)} Zeichen")
                    else:
                        debug.log("Streaming abgeschlossen", f"{chunk_count} Chunks, Gesamttext: {len(full_text)} Zeichen")
        
        except AttributeError as e:
            if debug:
                debug.log("generate_content_stream nicht verfügbar (AttributeError)", f"Fehler: {e}", level="WARNING")
            streaming_success = False
        except Exception as e:
            if debug:
                debug.log_exception("Fehler bei generate_content_stream", e)
            print(f"Fehler bei generate_content_stream: {e}")
            traceback.print_exc()
            streaming_success = False
        
        # Fallback: Normale API ohne Streaming (falls Streaming fehlschlägt)
        if not streaming_success:
            try:
                if debug:
                    debug.log("Verwende normale API ohne Streaming", f"Modell: {model}")
                
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                
                if debug:
                    request_time = debug.end_timer("api_request")
                    if request_time is not None:
                        debug.log("API-Request gesendet (ohne Stream)", f"Dauer: {request_time:.3f}s")
                    else:
                        debug.log("API-Request gesendet (ohne Stream)", "Dauer konnte nicht gemessen werden")
                
                # Extrahiere Text (vereinfacht mit getattr)
                full_text = getattr(response, "text", None)
                
                # Fallback über candidates falls text nicht direkt verfügbar
                if not full_text and hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        full_text = part.text
                                        break
                            elif hasattr(candidate.content, 'text'):
                                full_text = candidate.content.text
                                break
                        if full_text:
                            break
                
                if debug:
                    debug.log("Text von normaler API erhalten", f"Länge: {len(full_text)} Zeichen")
                
                if on_chunk_callback and full_text:
                    # Füge Text direkt auf einmal ein (keine Simulation nötig, da wir sowieso warten müssen)
                    on_chunk_callback(full_text)
                    chunk_count = 1
                
                if debug:
                    debug.log("Fallback-API abgeschlossen", f"{chunk_count} simulierte Chunks")
            
            except Exception as e:
                if debug:
                    debug.log_exception("Fehler bei normaler API", e)
                print(f"Fehler bei normaler API: {e}")
                traceback.print_exc()
                return None
        
        # Prüfe ob Text erhalten wurde
        if not full_text or not full_text.strip():
            if debug:
                debug.log("Kein Text von API erhalten", f"Chunk Count: {chunk_count}", level="ERROR")
            print("WARNUNG: Kein Text von Gemini API erhalten!")
            return None
        
        # Entferne Anführungszeichen am Anfang und Ende, falls vorhanden
        improved_text = full_text.strip()
        if improved_text.startswith('"') and improved_text.endswith('"'):
            improved_text = improved_text[1:-1].strip()
        if improved_text.startswith("'") and improved_text.endswith("'"):
            improved_text = improved_text[1:-1].strip()
        
        if debug:
            debug.log("Text-Verbesserung abgeschlossen", f"Finale Länge: {len(improved_text)} Zeichen")
        
        return improved_text
            
    except Exception as e:
        print(f"Fehler beim Aufruf der Gemini API: {e}")
        traceback.print_exc()
        return None


def improve_text_with_gemini(text, api_key, model, system_prompt):
    """
    Sendet Text an Gemini API und erhält verbesserten Text zurück (ohne Streaming).
    
    Args:
        text (str): Der zu verbessernde Text
        api_key (str): Der Gemini API Key
        model (str): Das zu verwendende Gemini Modell
        system_prompt (str): Der System Prompt für die Verbesserung
        
    Returns:
        str: Der verbesserte Text oder None bei Fehler
    """
    if not HAS_GENAI:
        return None
    
    if not text or not text.strip():
        return None
    
    try:
        # Erstelle Client mit direkt übergebenem API Key
        try:
            client = genai.Client(api_key=api_key)
        except TypeError:
            # Fallback: Falls Client keine api_key Parameter akzeptiert, verwende Umgebungsvariable
            if 'GEMINI_API_KEY' not in os.environ:
                os.environ['GEMINI_API_KEY'] = api_key
            client = genai.Client()
        
        # Erstelle den Prompt
        prompt = f"{system_prompt}\n\n{text}"
        
        # Sende Anfrage an Gemini
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        # Extrahiere den verbesserten Text
        improved_text = response.text.strip()
        
        # Entferne Anführungszeichen am Anfang und Ende, falls vorhanden
        if improved_text.startswith('"') and improved_text.endswith('"'):
            improved_text = improved_text[1:-1].strip()
        if improved_text.startswith("'") and improved_text.endswith("'"):
            improved_text = improved_text[1:-1].strip()
        
        return improved_text
            
    except Exception as e:
        print(f"Fehler beim Aufruf der Gemini API: {e}")
        traceback.print_exc()
        return None

