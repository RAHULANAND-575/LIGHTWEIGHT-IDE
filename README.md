# LIGHTWEIGHT-IDE

A lightweight **Python-only desktop IDE** for algorithm/data-structure learning with a minimalist glass-style UI.

## Features
- Minimal top-bar icon layout (`☰` menu + `📝` notebook)
- Smooth transitions: startup fade-in, animated ambient glow, live-dot pulse, hover effects, and sliding panels
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
  - Wallpaper mode (PNG/GIF)

## Run (macOS)
```bash
python3 app.py
```

## Notes
- This is implemented as a native Python desktop application (Tkinter), not a web app.
- Wallpaper mode currently supports PNG images for a lightweight dependency-free setup.


## Interaction reliability
- Context menu now works on macOS right-click variants (`Button-2`, `Button-3`, and `Control+Click`).
- Popup menus release grab correctly to prevent controls becoming unresponsive after menu usage.
