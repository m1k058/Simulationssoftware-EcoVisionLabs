"""
Runner for main_ui-v2.py (menu-based interface with advanced features)

Usage:
  python scripts/run_ui_v2.py
  
This launches the v2 interface with menus for:
- Generating graphs (saved/session plots)
- Configuring new plots
- Managing plots (edit/delete)
- CSV calculation mode
"""
import sys
from pathlib import Path

# Ensure local source-code is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source-code"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import importlib
main = importlib.import_module("main_ui-v2").main

if __name__ == "__main__":
    main()
