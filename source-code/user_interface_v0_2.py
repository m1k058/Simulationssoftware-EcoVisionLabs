"""
EcoVisionLabs CLI v0.2

New menu-based interface with the following features:

- Generate Graph:
  - Select and render saved plots from config.json
  - Render session plots (temporary, current runtime only)
- Configure New Plot:
  - Create completely new plot (from scratch)
  - Load and edit a saved plot (as copy or overwrite)
- Manage Saved/Session Plots:
  - Edit or delete saved plots
  - Edit or delete session plots
- CSV Calculation Mode:
  - Calculate new columns based on existing data (sum of selected sources, total, renewable, conventional)
  - Save result for session only or export as new CSV file

Note: Session plots are not saved in config.json and will be lost after program termination.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any

import pandas as pd

from constants import ENERGY_SOURCES as CONST_ENERGY_SOURCES
from config_manager import ConfigManager
from data_manager import DataManager
from io_handler import save_data
from plotting import plot_auto, plot_stacked_bar
from data_processing import (
    add_total_generation,
    add_total_renewable_generation,
    add_total_conventional_generation,
    add_energy_source_generation_sum,
)

# We use the existing date validation from v0.1
from user_interface import validate_date


# ----------------------------- Session State ------------------------------
@dataclass
class SessionState:
    session_plots: List[Dict[str, Any]] = field(default_factory=list)

    def next_session_plot_id(self) -> int:
        # Negative IDs for session plots to avoid collisions with config IDs
        taken = [p.get("id", 0) for p in self.session_plots]
        min_id = min(taken) if taken else 0
        return min_id - 1 if min_id >= 0 else min_id - 1


# ----------------------------- Helper Functions ----------------------------
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def pause(msg: str = "Press Enter to continue…"):
    input(msg)


def prompt_yes_no(question: str, default: Optional[bool] = None) -> bool:
    suffix = " [Y/N]"
    while True:
        ans = input(f"{question}{suffix}: ").strip().lower()
        if ans in {"y", "yes"}:
            return True
        if ans in {"n", "no"}:
            return False
        print("Please answer with Y or N.")


def select_from_list(items: List[Dict[str, Any]], title: str, key_label: str = "id", name_label: str = "name") -> Optional[Dict[str, Any]]:
    if not items:
        print("No entries available.")
        return None
    print(f"\n{title}")
    for it in items:
        print(f"[{it.get(key_label)}] {it.get(name_label)}")
    while True:
        raw = input("Selection (ID) or Enter to cancel: ").strip()
        if raw == "":
            return None
        try:
            sel_id = int(raw)
        except ValueError:
            print("Please enter a valid ID.")
            continue
        for it in items:
            if it.get(key_label) == sel_id:
                return it
        print("ID not found. Please try again.")


def input_date(prompt_text: str, default: Optional[str] = None) -> str:
    while True:
        value = input(f"{prompt_text} (Format DD.MM.YYYY HH:MM){' ['+default+']' if default else ''}: ").strip()
        if value == "" and default:
            value = default
        if validate_date(value):
            return value
        print("Invalid date. Please use format: DD.MM.YYYY HH:MM")


def input_nonempty(prompt_text: str, default: Optional[str] = None) -> str:
    while True:
        value = input(f"{prompt_text}{' ['+default+']' if default else ''}: ").strip()
        if value == "" and default is not None:
            return default
        if value:
            return value
        print("Input cannot be empty.")


def choose_energy_sources(default: Optional[List[str]] = None) -> List[str]:
    keys = list(CONST_ENERGY_SOURCES.keys())
    print("\nAvailable energy sources:")
    for i, k in enumerate(keys):
        meta = CONST_ENERGY_SOURCES[k]
        print(f"[{i}] {k} - {meta['name']}")

    while True:
        raw = input("Selection (numbers separated by spaces, 'all' for all sources)" + (f" [{ ' '.join(str(keys.index(k)) for k in default) }]" if default else "") + ": ").strip()
        if raw == "" and default is not None:
            return default
        if raw.lower() == "all":
            return keys
        try:
            idxs = [int(x) for x in raw.split() if x != ""]
            picked = [keys[i] for i in idxs if 0 <= i < len(keys)]
            if picked:
                return picked
            print("Please select at least one valid source.")
        except Exception:
            print("Invalid input. Please use numbers or 'all'.")


def run_plot_from_cfg_like(config_manager: ConfigManager, data_manager: DataManager, plot_cfg: Dict[str, Any], show: bool, save: bool):
    """Plot based on a config dict (for session plots)."""
    df_ids = plot_cfg.get("dataframes", [])
    if not df_ids:
        print("Plot has no assigned DataFrames.")
        return
    if len(df_ids) > 1:
        print("Multiple DataFrames per plot are currently not supported.")
        return
    df_id = df_ids[0]
    try:
        df = data_manager.get(df_id)
    except Exception as e:
        print(f"Dataset {df_id} not found: {e}")
        return

    try:
        start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
        end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")
    except Exception as e:
        print(f"Date error: {e}")
        return

    df_f = df[(df["Zeitpunkt"] >= start) & (df["Zeitpunkt"] <= end)]
    if df_f.empty:
        print("No data in selected time range.")
        return
    try:
        plot_stacked_bar(df_f, plot_cfg, show=show, save=save, output_dir=config_manager.get_global("output_dir"))
    except Exception as e:
        print(f"Plotting failed: {e}")


# ------------------------------ Menus -------------------------------------
def menu_generate_graph(cm: ConfigManager, dm: DataManager, state: SessionState):
    clear_screen()
    print("=== Generate Graph ===\n")
    print("1) Render saved plot")
    print("2) Render session plot")
    print("0) Back")
    choice = input("> ").strip()

    if choice == "1":
        plots = cm.list_plots()
        sel = select_from_list(plots, "Saved Plots")
        if not sel:
            return
        save_img = prompt_yes_no("Save image?")
        plot_auto(cm, dm, sel["id"], show=True, save=save_img)
        pause()
    elif choice == "2":
        sel = select_from_list(state.session_plots, "Session Plots")
        if not sel:
            return
        save_img = prompt_yes_no("Save image?")
        run_plot_from_cfg_like(cm, dm, sel, show=True, save=save_img)
        pause()


def menu_configure_new_plot(cm: ConfigManager, dm: DataManager, state: SessionState):
    clear_screen()
    print("=== Configure New Plot ===\n")
    print("1) Completely new (from scratch)")
    print("2) Load and edit saved plot")
    print("0) Back")
    choice = input("> ").strip()

    if choice == "1":
        datasets = cm.get_dataframes()
        sel_ds = select_from_list(datasets, "Datasets")
        if not sel_ds:
            return
        date_start = input_date("Start date")
        date_end = input_date("End date")
        energy_sources = choose_energy_sources()
        name = input_nonempty("Plot name")
        desc = input("Description (optional): ").strip()
        save_flag = prompt_yes_no("Save plot to config.json?")

        plot_cfg = {
            "id": state.next_session_plot_id() if not save_flag else None,  # may be overridden by save
            "name": name,
            "dataframes": [sel_ds["id"]],
            "date_start": date_start,
            "date_end": date_end,
            "energy_sources": energy_sources,
            "plot_type": "stacked_bar",
            "description": desc,
        }

        if save_flag:
            new_id = cm.create_plot_from_ui({
                "dataset": sel_ds,
                "date_start": date_start,
                "date_end": date_end,
                "energy_sources": energy_sources,
                "plot_name": name,
                "save_plot": True,
                "description": desc,
            })
            cm.save()
            print(f"Saved (ID {new_id}).")
        else:
            state.session_plots.append(plot_cfg)
            print("Created as session plot.")
        pause()

    elif choice == "2":
        sel = select_from_list(cm.list_plots(), "Saved Plots to Edit")
        if not sel:
            return
        try:
            base = cm.get_plot(sel["id"])
        except Exception as e:
            print(f"Plot could not be loaded: {e}")
            pause()
            return

        # Interactive editing (Enter keeps value)
        name = input_nonempty("Name", default=base.get("name"))
        date_start = input_date("Start date", default=base.get("date_start"))
        date_end = input_date("End date", default=base.get("date_end"))
        energy_sources = choose_energy_sources(default=base.get("energy_sources"))
        desc = input("Description (optional)") or base.get("description", "")

        as_copy = prompt_yes_no("Save as session copy (instead of overwriting config)?")
        if as_copy:
            new_plot = dict(base)
            new_plot.update({
                "id": state.next_session_plot_id(),
                "name": name,
                "date_start": date_start,
                "date_end": date_end,
                "energy_sources": energy_sources,
                "description": desc,
            })
            state.session_plots.append(new_plot)
            print("Session copy created.")
        else:
            cm.edit_plot(base["id"], name=name, date_start=date_start, date_end=date_end,
                         energy_sources=energy_sources, description=desc)
            cm.save()
            print("Saved plot updated.")
        pause()


def menu_manage_plots(cm: ConfigManager, dm: DataManager, state: SessionState):
    clear_screen()
    print("=== Manage Plots (Edit/Delete) ===\n")
    print("1) Edit saved plots")
    print("2) Delete saved plots")
    print("3) Edit session plots")
    print("4) Delete session plots")
    print("0) Back")
    choice = input("> ").strip()

    if choice == "1":
        sel = select_from_list(cm.list_plots(), "Saved Plots")
        if not sel:
            return
        try:
            base = cm.get_plot(sel["id"])
        except Exception as e:
            print(f"Error: {e}")
            pause()
            return
        name = input_nonempty("Name", default=base.get("name"))
        date_start = input_date("Start date", default=base.get("date_start"))
        date_end = input_date("End date", default=base.get("date_end"))
        energy_sources = choose_energy_sources(default=base.get("energy_sources"))
        desc = input("Description (optional)") or base.get("description", "")
        cm.edit_plot(base["id"], name=name, date_start=date_start, date_end=date_end,
                     energy_sources=energy_sources, description=desc)
        cm.save()
        print("Plot updated.")
        pause()

    elif choice == "2":
        sel = select_from_list(cm.list_plots(), "Delete Saved Plots")
        if not sel:
            return
        if prompt_yes_no(f"Really delete plot '{sel['name']}'?"):
            if cm.delete_plot(sel["id"]):
                cm.save()
        pause()

    elif choice == "3":
        sel = select_from_list(state.session_plots, "Edit Session Plots")
        if not sel:
            return
        name = input_nonempty("Name", default=sel.get("name"))
        date_start = input_date("Start date", default=sel.get("date_start"))
        date_end = input_date("End date", default=sel.get("date_end"))
        energy_sources = choose_energy_sources(default=sel.get("energy_sources"))
        desc = input("Description (optional)") or sel.get("description", "")
        sel.update({
            "name": name,
            "date_start": date_start,
            "date_end": date_end,
            "energy_sources": energy_sources,
            "description": desc,
        })
        print("Session plot updated.")
        pause()

    elif choice == "4":
        sel = select_from_list(state.session_plots, "Delete Session Plots")
        if not sel:
            return
        if prompt_yes_no(f"Really delete plot '{sel['name']}'?"):
            state.session_plots = [p for p in state.session_plots if p is not sel]
            print("Session plot deleted.")
        pause()


def menu_csv_calc(cm: ConfigManager, dm: DataManager, state: SessionState):
    clear_screen()
    print("=== CSV Calculation Mode ===\n")

    datasets = cm.get_dataframes()
    sel_ds = select_from_list(datasets, "Select Dataset")
    if not sel_ds:
        return

    try:
        df = dm.get(sel_ds["id"])  # already loaded
    except Exception as e:
        print(f"Dataset could not be loaded: {e}")
        pause()
        return

    while True:
        clear_screen()
        print("=== CSV Calculation Mode: Choose Operation ===\n")
        print("1) Sum of selected energy sources as new column")
        print("2) Add total generation (all sources)")
        print("3) Add total renewable generation")
        print("4) Add total conventional generation")
        print("0) Back")
        choice = input("> ").strip()

        if choice == "0":
            return

        df_mod = df.copy()
        try:
            if choice == "1":
                sources = choose_energy_sources()
                colname_base = input_nonempty("Column name base (e.g. 'My Sum')")
                df_mod = add_energy_source_generation_sum(df_mod, sources=sources, name=colname_base)
            elif choice == "2":
                df_mod = add_total_generation(df_mod)
            elif choice == "3":
                df_mod = add_total_renewable_generation(df_mod)
            elif choice == "4":
                df_mod = add_total_conventional_generation(df_mod)
            else:
                print("Invalid selection.")
                pause()
                continue
        except Exception as e:
            print(f"Calculation failed: {e}")
            pause()
            continue

        print("\nCalculation completed. Preview of last columns:")
        try:
            tail_cols = df_mod.columns[-5:]
            print(df_mod[tail_cols].head(3).to_string(index=False))
        except Exception:
            print("Preview not available.")

        only_session = prompt_yes_no("Keep for this session only?")
        if only_session:
            # Replace in DataManager memory
            dm.dataframes[sel_ds["id"]] = df_mod
            print("Changes applied in memory (session only).")
            pause()
            return
        else:
            # Save as new file
            outdir = Path(cm.get_global("output_dir") or "output")
            outdir.mkdir(parents=True, exist_ok=True)
            filename = input_nonempty("Filename (without extension)") + ".csv"
            outpath = outdir / filename
            try:
                save_data(df_mod, outpath, datatype=sel_ds.get("datatype", "SMARD"))
                print(f"File saved: {outpath}")
            except Exception as e:
                print(f"Saving failed: {e}")
            pause()
            return


def main():
    clear_screen()
    print("=== EcoVisionLabs Interface v0.2 ===\n")

    cm = ConfigManager()
    dm = DataManager(config_manager=cm)  # loads defined datasets automatically
    state = SessionState()

    while True:
        clear_screen()
        print("=== EcoVisionLabs Interface v0.2 ===\n")
        print("1) Generate Graph")
        print("2) Configure New Plot")
        print("3) Manage Saved/Session Plots (Edit/Delete)")
        print("4) CSV Calculation Mode")
        print("0) Exit")
        choice = input("> ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            menu_generate_graph(cm, dm, state)
        elif choice == "2":
            menu_configure_new_plot(cm, dm, state)
        elif choice == "3":
            menu_manage_plots(cm, dm, state)
        elif choice == "4":
            menu_csv_calc(cm, dm, state)
        else:
            print("Invalid selection.")
            pause()


if __name__ == "__main__":
    main()
