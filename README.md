# LIGHTWEIGHT-IDE

A lightweight **Python-only desktop IDE** for algorithm/data-structure learning with a minimalist glass-style UI.

## Features
- Minimal top-bar icon layout (`☰` menu + `📝` notebook)
- Compact tab workflow with close buttons
- Python-only file tree and file opening (`.py` only)
- Clean bottom output panel
- Full-file run and instant stop
- Contextual right-click actions:
  - Run Selection
  - Save as Note
  - Stop
  - Toggle Live Mode
- Live mode (auto-run on save) with auto-stop/clear when editor becomes empty
- Built-in DSA notebook drawer:
  - Categories
  - Section isolation
  - Expand-all toggle
  - Run note code
  - Save note output
  - Insert note into editor
- Background modes:
  - Solid dark mode
  - Wallpaper mode (PNG)

## Run (macOS)
```bash
python3 app.py
```

## Notes
- This is implemented as a native Python desktop application (Tkinter), not a web app.
- Wallpaper mode currently supports PNG images for a lightweight dependency-free setup.
