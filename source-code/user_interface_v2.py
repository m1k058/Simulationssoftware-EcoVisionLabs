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

# from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd

from constants import ENERGY_SOURCES as CONST_ENERGY_SOURCES
from config_manager import ConfigManager
from data_manager import DataManager
from io_handler import save_data, save_data_excel
from plotting_formated import (
    plot_auto,
    plot_stacked_bar,
    plot_line_chart,
    plot_balance,
    plot_ee_consumption_histogram,
)
from data_processing import gen, col


def validate_date(date_str: str) -> bool:
    """Validate if the date string matches the required format."""
    try:
        datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        return True
    except ValueError:
        return False


# ----------------------------- Session State ------------------------------
@dataclass
class SessionState:
    session_plots: List[Dict[str, Any]] = field(default_factory=list)
    # Selected scenario for Simulation menu (placeholder structure)
    selected_scenario: Optional[Dict[str, Any]] = None

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


def choose_columns_from_df(df: pd.DataFrame, multi: bool = True, exclude: Optional[List[str]] = None, prompt_text: str = "Select columns") -> List[str] | str:
    """Interactive column picker for a DataFrame.

    Args:
        df: DataFrame to list columns from.
        multi: Allow picking multiple columns if True; otherwise returns a single string.
        exclude: Optional list of column names to exclude from choices.
        prompt_text: Prompt text for input.

    Returns:
        List of selected column names or a single column name (str) if multi=False.
    """
    cols = list(df.columns)
    if exclude:
        cols = [c for c in cols if c not in exclude]
    if not cols:
        print("No selectable columns available.")
        return [] if multi else ""

    print("\nAvailable columns:")
    for i, c in enumerate(cols):
        print(f"[{i}] {c}")

    while True:
        raw = input(f"{prompt_text} (indices separated by spaces){' [multiple allowed]' if multi else ''}: ").strip()
        try:
            idxs = [int(x) for x in raw.split() if x != ""]
            picked = [cols[i] for i in idxs if 0 <= i < len(cols)]
            if not picked:
                print("Please select at least one valid index.")
                continue
            return picked if multi else picked[0]
        except Exception:
            print("Invalid input. Please use numeric indices.")


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


def get_all_available_datasets(cm: ConfigManager, dm: DataManager) -> List[Dict[str, Any]]:
    """Get all available datasets from both ConfigManager and DataManager.
    
    Returns a unified list of datasets that can be used for selection,
    including both config-defined and dynamically added datasets.
    """
    # Start with config datasets
    config_datasets = cm.get_dataframes()
    
    # Get all datasets from DataManager
    dm_info = dm.list_datasets()
    
    # Create a set of IDs that are already in config
    config_ids = {ds["id"] for ds in config_datasets}
    
    # Add datasets from DataManager that aren't in config
    combined = list(config_datasets)
    for dm_ds in dm_info:
        if dm_ds["ID"] not in config_ids:
            # Format to match config dataset structure
            combined.append({
                "id": dm_ds["ID"],
                "name": dm_ds["Name"],
                "path": dm_ds.get("Path", "N/A"),
                "datatype": dm_ds.get("Datatype", "Custom"),
                "description": ""
            })
    
    return combined


def run_plot_from_cfg_like(config_manager: ConfigManager, data_manager: DataManager, plot_cfg: Dict[str, Any], show: bool, save: bool, darkmode: bool = False):
    """Plot based on a config dict (for session plots)."""
    df_ids = plot_cfg.get("dataframes", [])
    if not df_ids:
        print("Plot has no assigned DataFrames.")
        return
    
    plot_type = plot_cfg.get("plot_type", "stacked_bar")
    
    # Histogram requires exactly 2 DataFrames
    if plot_type == "histogram":
        if len(df_ids) != 2:
            print("Histogram plot type requires exactly 2 DataFrames (generation + consumption).")
            return
    elif len(df_ids) > 1:
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
        outdir = config_manager.get_global("output_dir")
        description = plot_cfg.get("description", "")
        if plot_type == "stacked_bar":
            plot_stacked_bar(df_f, plot_cfg, show=show, save=save, output_dir=outdir, darkmode=darkmode)
        elif plot_type == "line":
            cols = plot_cfg.get("columns")
            title = plot_cfg.get("name", "Line chart")
            plot_line_chart(config_manager, df_f, columns=cols, title=title, description=description, show=show, save=save, output_dir=outdir, darkmode=darkmode)
        elif plot_type == "balance":
            col1 = plot_cfg.get("column1")
            col2 = plot_cfg.get("column2")
            title = plot_cfg.get("name", "Balance plot")
            plot_balance(config_manager, df_f, column1=col1, column2=col2, title=title, description=description, show=show, save=save, output_dir=outdir, darkmode=darkmode) # type: ignore
        elif plot_type == "histogram":
            # Load second DataFrame for consumption data
            df_id_2 = df_ids[1]
            try:
                df_2 = data_manager.get(df_id_2)
            except Exception as e:
                print(f"Consumption dataset {df_id_2} not found: {e}")
                return
            
            df_2_f = df_2[(df_2["Zeitpunkt"] >= start) & (df_2["Zeitpunkt"] <= end)]
            if df_2_f.empty:
                print("No consumption data in selected time range.")
                return
            
            title = plot_cfg.get("name", "Renewable Energy Share Histogram")
            plot_ee_consumption_histogram(config_manager, df_f, df_2_f, title=title, description=description, show=show, save=save, output_dir=outdir, darkmode=darkmode)
        else:
            print(f"Unsupported plot type: {plot_type}")
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
        use_dark = prompt_yes_no("Dark mode?")
        plot_auto(cm, dm, sel["id"], show=True, save=save_img, darkmode=use_dark)
        pause()
    elif choice == "2":
        sel = select_from_list(state.session_plots, "Session Plots")
        if not sel:
            return
        save_img = prompt_yes_no("Save image?")
        use_dark = prompt_yes_no("Dark mode?")
        run_plot_from_cfg_like(cm, dm, sel, show=True, save=save_img, darkmode=use_dark)
        pause()


def menu_configure_new_plot(cm: ConfigManager, dm: DataManager, state: SessionState):
    clear_screen()
    print("=== Configure New Plot ===\n")
    print("1) Completely new (from scratch)")
    print("2) Load and edit saved plot")
    print("0) Back")
    choice = input("> ").strip()

    if choice == "1":
        datasets = get_all_available_datasets(cm, dm)
        
        # Choose plot type first to determine dataset requirements
        print("\nPlot type:")
        print("1) Stacked area (generation by sources)")
        print("2) Line chart (select columns)")
        print("3) Balance plot (column1 - column2)")
        print("4) Histogram (renewable energy share)")
        print("0) Cancel")
        pt_choice = input("> ").strip()
        if pt_choice == "0":
            return

        plot_type = "stacked_bar" if pt_choice == "1" else ("line" if pt_choice == "2" else ("balance" if pt_choice == "3" else ("histogram" if pt_choice == "4" else None)))
        if not plot_type:
            print("Invalid selection.")
            pause()
            return
        
        # For histogram, we need 2 datasets (generation + consumption)
        if plot_type == "histogram":
            print("\nHistogram requires 2 datasets: generation and consumption data")
            sel_ds_gen = select_from_list(datasets, "Generation Dataset")
            if not sel_ds_gen:
                return
            sel_ds_cons = select_from_list(datasets, "Consumption Dataset")
            if not sel_ds_cons:
                return
            selected_dataframes = [sel_ds_gen["id"], sel_ds_cons["id"]]
            # For histogram, we don't need column selection
            type_specific = {}
        else:
            # Other plot types use single dataset
            sel_ds = select_from_list(datasets, "Datasets")
            if not sel_ds:
                return
            selected_dataframes = [sel_ds["id"]]
            
            # Fetch DataFrame columns for selection if needed
            try:
                df_for_cols = dm.get(sel_ds["id"])  # get loaded DataFrame
            except Exception as e:
                print(f"Dataset could not be loaded for column selection: {e}")
                pause()
                return

            type_specific = {}
            if plot_type == "stacked_bar":
                type_specific["energy_sources"] = choose_energy_sources()
            elif plot_type == "line":
                cols = choose_columns_from_df(df_for_cols, multi=True, exclude=["Zeitpunkt"], prompt_text="Select columns for line chart")
                type_specific["columns"] = cols
            elif plot_type == "balance":
                col1 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Select column1 (minuend)")
                col2 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Select column2 (subtrahend)")
                type_specific["column1"] = col1
                type_specific["column2"] = col2
        
        date_start = input_date("Start date")
        date_end = input_date("End date")
        name = input_nonempty("Plot name")
        desc = input("Description (optional): ").strip()
        save_flag = prompt_yes_no("Save plot to config.json?")

        plot_cfg = {
            "id": state.next_session_plot_id() if not save_flag else None,
            "name": name,
            "dataframes": selected_dataframes,
            "date_start": date_start,
            "date_end": date_end,
            "plot_type": plot_type,
            "description": desc,
            **type_specific,
        }

        if save_flag:
            payload = {
                "dataframes": selected_dataframes,
                "date_start": date_start,
                "date_end": date_end,
                "plot_name": name,
                "save_plot": True,
                "description": desc,
                "plot_type": plot_type,
                **type_specific,
            }
            new_id = cm.create_plot_from_ui(payload)
            cm.save()
            print(f"Saved (ID {new_id}).")
            # Ask to generate now
            if prompt_yes_no("Generate this plot now?"):
                save_img = prompt_yes_no("Save image as PNG?")
                use_dark = prompt_yes_no("Dark mode?")
                try:
                    plot_auto(cm, dm, new_id, show=True, save=save_img, darkmode=use_dark)
                except Exception as e:
                    print(f"Rendering failed: {e}")
                    print(f"Rendering failed: {e}")
        else:
            state.session_plots.append(plot_cfg)
            print("Created as session plot.")
            # Ask to generate now
            if prompt_yes_no("Generate this plot now?"):
                save_img = prompt_yes_no("Save image as PNG?")
                use_dark = prompt_yes_no("Dark mode?")
                try:
                    run_plot_from_cfg_like(cm, dm, plot_cfg, show=True, save=save_img, darkmode=use_dark)
                except Exception as e:
                    print(f"Rendering failed: {e}")
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
        desc = input("Description (optional)") or base.get("description", "")

        plot_type = base.get("plot_type", "stacked_bar")
        print(f"Plot type: {plot_type}")
        updates: Dict[str, Any] = {}
        if plot_type == "stacked_bar":
            energy_sources = choose_energy_sources(default=base.get("energy_sources"))
            updates["energy_sources"] = energy_sources
        elif plot_type == "line":
            try:
                df_for_cols = dm.get(base["dataframes"][0])
            except Exception:
                df_for_cols = None
            default_cols = base.get("columns") or []
            if df_for_cols is not None:
                columns = choose_columns_from_df(df_for_cols, multi=True, exclude=["Zeitpunkt"], prompt_text="Update columns (line chart)")
            else:
                # Fallback to simple input when DF not available
                print("Dataset not available for column selection. Keeping existing columns.")
                columns = default_cols
            updates["columns"] = columns
        elif plot_type == "balance":
            try:
                df_for_cols = dm.get(base["dataframes"][0])
            except Exception:
                df_for_cols = None
            if df_for_cols is not None:
                col1 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Column1 (minuend)")
                col2 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Column2 (subtrahend)")
            else:
                col1 = base.get("column1")
                col2 = base.get("column2")
            updates["column1"] = col1
            updates["column2"] = col2

        as_copy = prompt_yes_no("Save as session copy (instead of overwriting config)?")
        if as_copy:
            new_plot = dict(base)
            new_plot.update({
                "id": state.next_session_plot_id(),
                "name": name,
                "date_start": date_start,
                "date_end": date_end,
                "description": desc,
            })
            new_plot.update(updates)
            state.session_plots.append(new_plot)
            print("Session copy created.")
            # Ask to generate now
            if prompt_yes_no("Generate this plot now?"):
                save_img = prompt_yes_no("Save image as PNG?")
                use_dark = prompt_yes_no("Dark mode?")
                try:
                    run_plot_from_cfg_like(cm, dm, new_plot, show=True, save=save_img, darkmode=use_dark)
                except Exception as e:
                    print(f"Rendering failed: {e}")
        else:
            cm.edit_plot(base["id"], name=name, date_start=date_start, date_end=date_end,
                         description=desc, **updates)
            cm.save()
            print("Saved plot updated.")
            # Ask to generate now
            if prompt_yes_no("Generate this plot now?"):
                save_img = prompt_yes_no("Save image as PNG?")
                use_dark = prompt_yes_no("Dark mode?")
                try:
                    plot_auto(cm, dm, base["id"], show=True, save=save_img, darkmode=use_dark)
                except Exception as e:
                    print(f"Rendering failed: {e}")
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
        desc = input("Description (optional)") or base.get("description", "")

        plot_type = base.get("plot_type", "stacked_bar")
        updates: Dict[str, Any] = {}
        if plot_type == "stacked_bar":
            energy_sources = choose_energy_sources(default=base.get("energy_sources"))
            updates["energy_sources"] = energy_sources
        elif plot_type == "line":
            try:
                df_for_cols = dm.get(base["dataframes"][0])
            except Exception:
                df_for_cols = None
            if df_for_cols is not None:
                columns = choose_columns_from_df(df_for_cols, multi=True, exclude=["Zeitpunkt"], prompt_text="Update columns (line chart)")
            else:
                columns = base.get("columns", [])
            updates["columns"] = columns
        elif plot_type == "balance":
            try:
                df_for_cols = dm.get(base["dataframes"][0])
            except Exception:
                df_for_cols = None
            if df_for_cols is not None:
                col1 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Column1 (minuend)")
                col2 = choose_columns_from_df(df_for_cols, multi=False, exclude=["Zeitpunkt"], prompt_text="Column2 (subtrahend)")
            else:
                col1 = base.get("column1")
                col2 = base.get("column2")
            updates["column1"] = col1
            updates["column2"] = col2

        cm.edit_plot(base["id"], name=name, date_start=date_start, date_end=date_end, description=desc, **updates)
        cm.save()
        print("Plot updated.")
        # Ask to generate now
        if prompt_yes_no("Generate this plot now?"):
            save_img = prompt_yes_no("Save image as PNG?")
            use_dark = prompt_yes_no("Dark mode?")
            try:
                plot_auto(cm, dm, base["id"], show=True, save=save_img, darkmode=use_dark)
            except Exception as e:
                print(f"Rendering failed: {e}")
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
    """CSV Calculation Mode - Work with datasets and perform calculations."""
    clear_screen()
    print("=== CSV Calculation Mode ===\n")
    print("1) Select CSV and perform operations")
    print("2) Calculate DataFrame with column sums (quick)")
    print("0) Back")
    
    main_choice = input("> ").strip()
    
    if main_choice == "0":
        return
    elif main_choice == "2":
        # Quick column sum calculation
        datasets = get_all_available_datasets(cm, dm)
        sel_ds = select_from_list(datasets, "Select Dataset")
        if not sel_ds:
            return
        
        try:
            df = dm.get(sel_ds["id"])
        except Exception as e:
            print(f"Dataset could not be loaded: {e}")
            pause()
            return
        from data_processing import col
        df_sums = col.generate_df_with_col_sums(df)
        
        clear_screen()
        print("=== Column Sum Result ===\n")
        print(df_sums.to_string(index=False))
        print()
        
        if prompt_yes_no("Save this result?"):
            save_format = input("Format (1=CSV, 2=Excel): ").strip()
            outdir = Path(cm.get_global("output_dir") or "output")
            outdir.mkdir(parents=True, exist_ok=True)
            
            if save_format == "1":
                filename = input_nonempty("Filename (without extension)") + ".csv"
                outpath = outdir / filename
                try:
                    save_data(df_sums, outpath, datatype=sel_ds.get("datatype", "SMARD"))
                    print(f"CSV file saved: {outpath}")
                except Exception as e:
                    print(f"Saving failed: {e}")
            elif save_format == "2":
                filename = input_nonempty("Filename (without extension)") + ".xlsx"
                outpath = outdir / filename
                try:
                    save_data_excel(df_sums, outpath)
                    print(f"Excel file saved: {outpath}")
                except Exception as e:
                    print(f"Saving failed: {e}")
        pause()
        return
    
    elif main_choice == "1":
        # Full interactive mode with multiple operations
        datasets = get_all_available_datasets(cm, dm)
        sel_ds = select_from_list(datasets, "Select Dataset to Work With")
        if not sel_ds:
            return
        
        try:
            df_working = dm.get(sel_ds["id"]).copy()
            working_name = sel_ds["name"]
        except Exception as e:
            print(f"Dataset could not be loaded: {e}")
            pause()
            return
        
        # Interactive operation loop
        while True:
            clear_screen()
            print(f"=== Working with: {working_name} ===")
            print(f"Rows: {len(df_working)}, Columns: {len(df_working.columns)}\n")
            
            print("Operations:")
            print("1) Sum columns (custom selection)")
            print("2) Sum energy sources (predefined)")
            print("3) Multiply column by factor")
            print("4) Add column from another DataFrame")
            print("5) Add total generation (all sources)")
            print("6) Add total renewable generation")
            print("7) Add total conventional generation")
            print("8) View current columns")
            print("9) Preview data (first 10 rows)")
            print()
            print("S) Save result (Session/Permanent/Copy)")
            print("0) Back to main menu")
            
            op_choice = input("> ").strip().upper()
            
            if op_choice == "0":
                break
            
            elif op_choice == "1":
                # Sum custom columns
                print("\nAvailable columns:")
                for i, col in enumerate(df_working.columns):
                    print(f"[{i}] {col}")
                
                try:
                    indices_str = input("Enter column indices to sum (space-separated): ").strip()
                    indices = [int(x) for x in indices_str.split()]
                    cols_to_sum = [df_working.columns[i] for i in indices if 0 <= i < len(df_working.columns)]
                    
                    if not cols_to_sum:
                        print("No valid columns selected.")
                        pause()
                        continue
                    
                    new_col_name = input_nonempty("Name for new sum column")
                    from data_processing import col
                    df_working = col.sum_columns(df_working, cols_to_sum, new_col_name)
                    print(f"✓ Column '{new_col_name}' created successfully.")
                    pause()
                    
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "2":
                # Sum energy sources
                sources = choose_energy_sources()
                colname_base = input_nonempty("Column name base (e.g. 'My Sum')")
                try:
                    df_working = gen.sum_energy_sources(df_working, sources=sources, name=colname_base) # type: ignore
                    print(f"✓ Column '{colname_base} [MWh]' created successfully.")
                    pause()
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "3":
                # Multiply column
                print("\nAvailable columns:")
                for i, col in enumerate(df_working.columns):
                    print(f"[{i}] {col}")
                
                try:
                    col_idx = int(input("Enter column index to multiply: ").strip())
                    if not (0 <= col_idx < len(df_working.columns)):
                        print("Invalid index.")
                        pause()
                        continue
                    
                    col_name = df_working.columns[col_idx]
                    factor = float(input("Enter multiplication factor: ").strip())
                    
                    create_new = prompt_yes_no("Create new column (otherwise overwrite)?")
                    new_name = None
                    if create_new:
                        new_name = input_nonempty("Name for new column")
                    
                    from data_processing import col
                    df_working = col.multiply_column(df_working, col_name, factor, new_name)
                    pause()
                    
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "4":
                # Add column from other DataFrame
                other_datasets = [ds for ds in datasets if ds["id"] != sel_ds["id"]]
                if not other_datasets:
                    print("No other datasets available.")
                    pause()
                    continue
                
                other_ds = select_from_list(other_datasets, "Select Source Dataset")
                if not other_ds:
                    continue
                
                try:
                    df_other = dm.get(other_ds["id"])
                    
                    print("\nAvailable columns in source DataFrame:")
                    for i, col in enumerate(df_other.columns):
                        print(f"[{i}] {col}")
                    
                    col_idx = int(input("Enter column index to copy: ").strip())
                    if not (0 <= col_idx < len(df_other.columns)):
                        print("Invalid index.")
                        pause()
                        continue
                    
                    source_col = df_other.columns[col_idx]
                    
                    rename = prompt_yes_no("Rename column in target DataFrame?")
                    new_name = None
                    if rename:
                        new_name = input_nonempty("New column name")
                    
                    from data_processing import col
                    df_working = col.add_column_from_other_df(df_working, df_other, source_col, new_name)
                    pause()
                    
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "5":
                # Add total generation
                try:
                    df_working = gen.add_total_generation(df_working)
                    df_working = gen.add_total_generation(df_working)
                    print("✓ Total generation column added.")
                    pause()
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "6":
                # Add total renewable
                try:
                    df_working = gen.add_total_renewable_generation(df_working)
                    print("✓ Total renewable generation column added.")
                    pause()
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "7":
                # Add total conventional
                try:
                    df_working = gen.add_total_conventional_generation(df_working)
                    print("✓ Total conventional generation column added.")
                    pause()
                except Exception as e:
                    print(f"Error: {e}")
                    pause()
            
            elif op_choice == "8":
                # View columns
                clear_screen()
                print(f"=== Columns in {working_name} ===\n")
                for i, col in enumerate(df_working.columns):
                    print(f"[{i}] {col}")
                pause()
            
            elif op_choice == "9":
                # Preview data
                clear_screen()
                print(f"=== Preview: {working_name} (first 10 rows) ===\n")
                print(df_working.head(10).to_string())
                pause()
            
            elif op_choice == "S":
                # Save result
                clear_screen()
                print("=== Save Result ===\n")
                print("1) Save to session only (temporary)")
                print("2) Save permanently (overwrite original dataset)")
                print("3) Save as new dataset (create copy)")
                print("4) Export as CSV/Excel file")
                print("0) Cancel")
                
                save_choice = input("> ").strip()
                
                if save_choice == "0":
                    continue
                
                elif save_choice == "1":
                    # Session only - update in DataManager temporarily
                    dm.dataframes[sel_ds["id"]] = df_working
                    print(f"✓ Changes saved to session. Will be lost when program closes.")
                    pause()
                
                elif save_choice == "2":
                    # Permanent - overwrite original file
                    if prompt_yes_no(f"Really overwrite original file '{sel_ds['name']}'?"):
                        try:
                            original_path = Path(sel_ds["path"])
                            save_data(df_working, original_path, datatype=sel_ds.get("datatype", "SMARD"))
                            dm.dataframes[sel_ds["id"]] = df_working  # Update in memory too
                            print(f"✓ Original file overwritten: {original_path}")
                            pause()
                        except Exception as e:
                            print(f"Error saving: {e}")
                            pause()
                
                elif save_choice == "3":
                    # Save as new dataset
                    new_name = input_nonempty("New dataset name")
                    new_filename = input_nonempty("New filename (without extension)") + ".csv"
                    
                    outdir = Path(cm.get_global("output_dir") or "output")
                    outdir.mkdir(parents=True, exist_ok=True)
                    new_path = outdir / new_filename
                    
                    try:
                        save_data(df_working, new_path, datatype=sel_ds.get("datatype", "SMARD"))
                        print(f"✓ New dataset saved: {new_path}")
                        
                        # Optionally add to config
                        if prompt_yes_no("Add to config.json as new dataset?"):
                            new_df_config = {
                                "id": max([d["id"] for d in cm.get_dataframes()], default=-1) + 1,
                                "name": new_name,
                                "path": str(new_path),
                                "datatype": sel_ds.get("datatype", "SMARD"),
                                "description": f"Derived from {sel_ds['name']}"
                            }
                            cm.config["DATAFRAMES"].append(new_df_config)
                            cm.save()
                            print(f"✓ Dataset added to config with ID {new_df_config['id']}")
                        pause()
                    except Exception as e:
                        print(f"Error saving: {e}")
                        pause()
                
                elif save_choice == "4":
                    # Export as file
                    export_format = input("Format (1=CSV, 2=Excel): ").strip()
                    outdir = Path(cm.get_global("output_dir") or "output")
                    outdir.mkdir(parents=True, exist_ok=True)
                    
                    if export_format == "1":
                        filename = input_nonempty("Filename (without extension)") + ".csv"
                        outpath = outdir / filename
                        try:
                            save_data(df_working, outpath, datatype=sel_ds.get("datatype", "SMARD"))
                            print(f"✓ CSV file saved: {outpath}")
                        except Exception as e:
                            print(f"Error saving: {e}")
                    elif export_format == "2":
                        filename = input_nonempty("Filename (without extension)") + ".xlsx"
                        outpath = outdir / filename
                        try:
                            save_data_excel(df_working, outpath)
                            print(f"✓ Excel file saved: {outpath}")
                        except Exception as e:
                            print(f"Error saving: {e}")
                    else:
                        print("Invalid format.")
                    pause()
            
            else:
                print("Invalid selection.")
                pause()


def menu_list_overview(cm: ConfigManager, dm: DataManager, state: SessionState):
    """Display overview of all plots and datasets."""
    clear_screen()
    print("=== Overview: Plots & Datasets ===\n")
    
    # --- Saved Plots ---
    saved_plots = cm.list_plots()
    print(f"📊 SAVED PLOTS ({len(saved_plots)}):")
    if saved_plots:
        for plot in saved_plots:
            print(f"  [{plot['id']}] {plot['name']}")
    else:
        print("  (none)")
    
    # --- Session Plots ---
    print(f"\n📊 SESSION PLOTS ({len(state.session_plots)}):")
    if state.session_plots:
        for plot in state.session_plots:
            print(f"  [{plot['id']}] {plot['name']}")
    else:
        print("  (none)")
    
    # --- Loaded Datasets ---
    datasets_info = dm.list_datasets()
    print(f"\n📁 LOADED DATASETS ({len(datasets_info)}):")
    if datasets_info:
        for ds in datasets_info:
            print(f"  [{ds['ID']}] {ds['Name']} ({ds['Rows']} rows, {ds['Datatype']})")
    else:
        print("  (none)")
    
    pause("\nPress Enter to return to main menu...")


def menu_simulation(cm: ConfigManager, dm: DataManager, state: SessionState):
    """Simulation (Base Programm) - placeholders for scenario workflow."""

    scenarios = [
        {"id": 1, "name": "Agora", "description": "Agora Study Scenario"},
        {"id": 2, "name": "BDI - Klimapfade 2.0", "description": "BDI Klimapfade 2.0 Study Scenario"},
        {"id": 3, "name": "dena - KN100", "description": "dena Klimaneutrales 100% Study Scenario"},
        {"id": 4, "name": "BMWK - LFS TN-Strom", "description": "BMWK Langfristszenario Treibhausneutraler Stromsektor Study Scenario"},
        {"id": 5, "name": "Ariadne - REMIND-Mix", "description": "Ariadne REMIND-Mix Study Scenario"},
        {"id": 6, "name": "Ariadne - REMod-Mix", "description": "Ariadne REMod-Mix Study Scenario"},
        {"id": 7, "name": "Ariadne - TIMES PanEU-Mix", "description": "Ariadne TIMES PanEU-Mix Study Scenario"},
    ]

    while True:
        clear_screen()
        print("=== Simulation (Base Programm) ===\n")
        # Top info about selected scenario
        if state.selected_scenario:
            print(f"Selected scenario: {state.selected_scenario.get('name', '<unnamed>')}")
            print(f"Description: {state.selected_scenario.get('description', '')}\n")
        else:
            print("No scenario selected.\n")

        print("1) Scenario selector")
        print("2) Scenario editor")
        print("3) Simulate scenario")
        print("0) Back")
        choice = input("> ").strip()

        if choice == "0":
            break
        elif choice == "1":
            # Scenario selector
            clear_screen()
            print("=== Scenario Selector ===\n")
            print("Available study scenarios:")
            for i, scenario in enumerate(scenarios, 1):
                print(f"{i}) {scenario['name']}")
            print("0) Back")
            
            scenario_choice = input("> ").strip()
            
            if scenario_choice == "0":
                continue
            elif scenario_choice in ["1", "2", "3", "4", "5", "6", "7"]:
                idx = int(scenario_choice) - 1
                state.selected_scenario = scenarios[idx]
                print(f"\n✓ Scenario '{scenarios[idx]['name']}' selected.")
            else:
                print("Invalid selection.")
            pause()

        elif choice == "2":
            print("(Placeholder) Scenario editor - not implemented yet.")
            pause()

        elif choice == "3":
            # Simulate scenario
            if not state.selected_scenario:
                print("No scenario selected. Please select a scenario first.")
                pause()
                continue
            
            clear_screen()
            print("=== Simulate Scenario ===\n")
            print(f"Selected scenario: {state.selected_scenario.get('name', '<unnamed>')}")
            print(f"Description: {state.selected_scenario.get('description', '')}\n")
            
            print("1) Simulate one year consumption scaling")
            print("2) Simulate multi-year consumption scaling")
            print("0) Back")
            sim_choice = input("> ").strip()

            if sim_choice == "0":
                continue
            elif sim_choice == "1":

                # Single year simulation
                # Dataset for consumption scaling
                datasets = get_all_available_datasets(cm, dm)
                sel_ds = select_from_list(datasets, "Select Dataset for consumption scaling:")
                if not sel_ds:
                    pause()
                    continue
                try:
                    conDf = dm.get(sel_ds["id"])
                except Exception as e:
                    print(f"Dataset could not be loaded: {e}")
                    pause()
                    continue

                # Dataset for prognosis
                sel_ds = select_from_list(datasets, "Select Dataset for prognosis:")
                if not sel_ds:
                    pause()
                    continue
                try:
                    proDf = dm.get(sel_ds["id"])
                except Exception as e:
                    print(f"Dataset could not be loaded: {e}")
                    pause()
                    continue
                
                ref_jahr = input_nonempty("Enter year for consumption scaling reference (e.g., 2023):", "2023")
                simu_jahr = input_nonempty("Enter year to simulate (e.g., 2030):")

                import data_processing.simulation as sim
                df_simulation = sim.calc_scaled_consumption(
                    conDf, proDf,
                    state.selected_scenario.get("name", "Agora"),  # type: ignore
                    int(simu_jahr),
                    ref_jahr=int(ref_jahr)
                )
                dataset_id = dm.add(
                    df_simulation,
                    name=f"Simulation {state.selected_scenario.get('name', 'Scenario')} {simu_jahr}",  # type: ignore
                    description=f"Scaled consumption for {state.selected_scenario.get('name', 'Scenario')} in year {simu_jahr} based on prognosis data."  # type: ignore
                )
                
                print(f"\n✓ Added dataset with ID={dataset_id}.")

                if prompt_yes_no("Do you want to save the simulation result to a file?"):
                    filename = input_nonempty("Enter filename (without extension):")
                    outdir = Path(cm.get_global("output_dir_csv") or "output")
                    outdir.mkdir(parents=True, exist_ok=True)
                    outpath = outdir / f"{filename}.csv"
                    from io_handler import save_data
                    try:
                        save_data(df_simulation, outpath)
                        print(f"✓ File saved: {outpath}")
                    except Exception as e:
                        print(f"Error saving file: {e}")
                pause()
        
            elif sim_choice == "2":
                # Multi-year simulation
                # Dataset for consumption scaling
                datasets = get_all_available_datasets(cm, dm)
                sel_ds = select_from_list(datasets, "Select Dataset for consumption scaling:")
                if not sel_ds:
                    pause()
                    continue
                try:
                    conDf = dm.get(sel_ds["id"])
                except Exception as e:
                    print(f"Dataset could not be loaded: {e}")
                    pause()
                    continue

                # Dataset for prognosis
                sel_ds = select_from_list(datasets, "Select Dataset for prognosis:")
                if not sel_ds:
                    pause()
                    continue
                try:
                    proDf = dm.get(sel_ds["id"])
                except Exception as e:
                    print(f"Dataset could not be loaded: {e}")
                    pause()
                    continue
                
                ref_jahr = input_nonempty("Enter year for consumption scaling reference (e.g., 2023):", "2023")
                simu_jahr_von = input_nonempty("Enter year to simulate from (e.g., 2030):")
                simu_jahr_bis = input_nonempty("Enter year to simulate to (e.g., 2040):")

                import data_processing.simulation as sim
                df_simulation = sim.calc_scaled_consumption_multiyear(
                    conDf, proDf,
                    state.selected_scenario.get("name", "Agora"),  # type: ignore
                    int(simu_jahr_von), int(simu_jahr_bis),
                    ref_jahr=int(ref_jahr)
                )
                dataset_id = dm.add(
                    df_simulation,
                    name=f"Simulation {state.selected_scenario.get('name', 'Scenario')} {simu_jahr_von}-{simu_jahr_bis}",  # type: ignore
                    description=f"Scaled consumption for {state.selected_scenario.get('name', 'Scenario')} from year {simu_jahr_von} to {simu_jahr_bis} based on prognosis data."  # type: ignore
                )
                
                print(f"\n✓ Added dataset with ID={dataset_id}.")

                if prompt_yes_no("Do you want to save the simulation result to a file?"):
                    filename = input_nonempty("Enter filename (without extension):")
                    outdir = Path(cm.get_global("output_dir_csv") or "output")
                    outdir.mkdir(parents=True, exist_ok=True)
                    outpath = outdir / f"{filename}.csv"
                    from io_handler import save_data
                    try:
                        save_data(df_simulation, outpath)
                        print(f"✓ File saved: {outpath}")
                    except Exception as e:
                        print(f"Error saving file: {e}")
                pause()
            
            else:
                print("Invalid selection.")
                pause()


def menu_analyze_plot(cm: ConfigManager, dm: DataManager, state: SessionState):
    """Group plotting-related menus under Analyze -> Plot."""
    while True:
        clear_screen()
        print("=== Analyze: Plot ===\n")
        print("1) Generate Graph (render saved/session plots)")
        print("2) Configure New Plot")
        print("3) Manage Saved/Session Plots (Edit/Delete)")
        print("4) List Overview (Plots & Datasets)")
        print("0) Back")
        choice = input("> ").strip()

        if choice == "0":
            break
        elif choice == "1":
            menu_generate_graph(cm, dm, state)
        elif choice == "2":
            menu_configure_new_plot(cm, dm, state)
        elif choice == "3":
            menu_manage_plots(cm, dm, state)
        elif choice == "4":
            menu_list_overview(cm, dm, state)
        else:
            print("Invalid selection.")
            pause()


def menu_analyze(cm: ConfigManager, dm: DataManager, state: SessionState):
    """Analyze (manual visualisation and calculation) - top-level analyze menu."""
    while True:
        clear_screen()
        print("=== Analyze (manual visualisation and calculation) ===\n")
        print("1) Plot")
        print("2) Calc (tools)")
        print("0) Back")
        choice = input("> ").strip()

        if choice == "0":
            break
        elif choice == "1":
            menu_analyze_plot(cm, dm, state)
        elif choice == "2":
            menu_csv_calc(cm, dm, state)
        else:
            print("Invalid selection.")
            pause()


def main():
    clear_screen()
    print("=== EcoVisionLabs Interface v0.2 ===\n")

    cm = ConfigManager()
    dm = DataManager(config_manager=cm)  # loads defined datasets automatically
    state = SessionState()

    while True:
        clear_screen()
        print("=== EcoVisionLabs Interface v0.2 ===\n")
        print("1) Simulation (Base Programm)")
        print("2) Analyze (manual visualisation and calculation)")
        print("0) Stop program")
        choice = input("> ").strip()

        if choice == "0":
            print("Stopping program. Goodbye!")
            break
        elif choice == "1":
            menu_simulation(cm, dm, state)
        elif choice == "2":
            menu_analyze(cm, dm, state)
        else:
            print("Invalid selection.")
            pause()


if __name__ == "__main__":
    main()
