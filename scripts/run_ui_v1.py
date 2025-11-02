"""
Runner for main_ui-v1.py (classic single-plot workflow)

Usage:
  python scripts/run_ui_v1.py
  
This launches the v1 interface which creates a single plot using the original workflow.
"""
import sys
from pathlib import Path

# Ensure local source-code is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source-code"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import importlib
main = importlib.import_module("main_ui-v1").main

if __name__ == "__main__":
    main()
