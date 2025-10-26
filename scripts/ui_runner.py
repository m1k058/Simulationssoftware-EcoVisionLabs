"""
Simple runner to connect `user_interface.get_user_input` and `config_manager.ConfigManager`.

Usage:
  python3 scripts/ui_runner.py        # runs interactive UI
  python3 scripts/ui_runner.py --auto # runs non-interactive demo/test

This script ensures the local `source-code` package is importable by adjusting sys.path.
"""
import sys
from pathlib import Path

# Make sure local source-code dir is importable
ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "source-code"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from user_interface import get_user_input
from config_manager import ConfigManager

import argparse

parser = argparse.ArgumentParser(description="Run UI runner for EcoVisionLabs")
parser.add_argument("--auto", action="store_true", help="Run a non-interactive demo")
args = parser.parse_args()

cm = ConfigManager()

if args.auto:
    # Build a fake selection using the first dataset if available
    datasets = cm.get_dataframes()
    if not datasets:
        print("No datasets found in config. Exiting.")
        sys.exit(1)
    ds = datasets[0]
    fake_ui = {
        "dataset": ds,
        "date_start": "01.01.2023 00:00",
        "date_end": "07.01.2023 23:59",
        "energy_sources": ["PV", "WON"],
        "plot_name": "Auto Demo Plot",
        "save_plot": False,
    }
    print("Running auto demo with fake selections:")
    print(fake_ui)
    plot_id = cm.create_plot_from_ui(fake_ui)
    print(f"Created plot with ID: {plot_id}")
else:
    # Interactive mode
    ui = get_user_input()
    print("User selections:\n", ui)
    plot_id = cm.create_plot_from_ui(ui)
    print(f"Created plot with ID: {plot_id}")
    if ui.get("save_plot"):
        print("Config saved to disk.")
    else:
        print("Config not saved (save_plot was False).")
