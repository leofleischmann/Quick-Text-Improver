# Quick Text Improver

A simple Windows tool that improves text directly in any application with a hotkey - without the hassle of copying and pasting.

## The Problem

When writing emails, documents, or other texts, you often want to improve grammar and style. The usual workflow is tedious:

1. Select and copy text
2. Open a separate application (e.g., ChatGPT, Gemini, etc.)
3. Paste text
4. Copy the improved text
5. Switch back to the original application
6. Paste text

**Quick Text Improver solves this problem** - with a single hotkey, the selected text is automatically improved and directly reinserted.

## Solution

Quick Text Improver runs in the background as a tray icon and improves selected text directly in the current application:

1. Select text
2. Press hotkey (default: `Ctrl+R`)
3. Done! The text is automatically improved and inserted

## Usage

1. **Select text** in any application (email, Word, browser, etc.)
2. **Press hotkey** (default: `Ctrl+R`)
3. The selected text is automatically:
   - Deleted
   - Sent to the Gemini API
   - Improved
   - Reinserted

## Configuration

Right-click on the tray icon → **Settings...**

- **Gemini API Key**: Your API key from Google AI Studio
- **Model**: Choose the Gemini model (default: `gemini-2.5-flash`)
- **Hotkey**: Adjust the hotkey or record a new one
- **Text Insert Method**: 
  - "Typed": Text is typed character by character
  - "Clipboard": Text is inserted via clipboard (faster)
- **Auto Insert**: Deactivate this option to only copy text to the clipboard. This way you don't need to keep the window in focus and can do something else during processing, then come back and insert the text via CTRL+V.

## Installation

1. Download the `QuickTextImprover.exe` file
2. Double-click the `.exe` file
3. The program starts in the background (tray icon)
4. Right-click the tray icon → **Settings...**
5. Enter your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## System Requirements

- Windows 10/11
- Internet connection (for Gemini API)
- Gemini API key (Information on how to get one can be found online. A free API key should be sufficient for normal use.)

## Additionally, the prompt can be adjusted in the settings, which also allows other things to be configured beyond just text improvement or processing.
