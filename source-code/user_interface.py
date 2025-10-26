import os
from pathlib import Path
from typing import Dict, List, Union, Optional
from datetime import datetime

from constants import ENERGY_SOURCES as CONST_ENERGY_SOURCES
from io_handler import load_data



def get_available_datasets(config_manager: Optional[object] = None) -> List[Dict[str, Union[int, str, Path]]]:
    """Get list of available datasets.

    If a `config_manager` is provided, datasets are taken from its configuration
    (so IDs match the config). Otherwise the function falls back to scanning
    the `raw-data` directory for CSV files.
    """
    datasets = []
    if config_manager is not None:
        try:
            cfg_dfs = config_manager.get_dataframes()
            for df in cfg_dfs:
                datasets.append({
                    "id": df.get("id"),
                    "name": df.get("name"),
                    "path": df.get("path"),
                    "description": df.get("description", "")
                })
            return datasets
        except Exception:
            # Fall back to file scanning
            pass

    raw_data_dir = Path("raw-data")
    for i, file in enumerate(sorted(raw_data_dir.glob("*.csv"))):
        datasets.append({
            "id": i,
            "name": file.stem,
            "path": file,
            "description": f"Dataset from {file.name}"
        })

    return datasets

def validate_date(date_str: str) -> bool:
    """Validate if the date string matches the required format."""
    try:
        datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        return True
    except ValueError:
        return False

def get_user_input(config_manager: Optional[object] = None) -> Dict[str, any]:
    """
    Interactive command-line interface for user input.
    Returns a dictionary with all user selections.
    """
    # Clear screen for better visibility
    os.system('clear')
    
    print("=== EcoVisionLabs Data Visualization Interface ===\n")
    
    # 1. Dataset selection
    datasets = get_available_datasets(config_manager=config_manager)
    print("\nAvailable Datasets:")
    for ds in datasets:
        print(f"[{ds['id']}] {ds['name']} - {ds['description']}")
    
    while True:
        try:
            dataset_id = int(input("\nSelect dataset by number: "))
            if any(ds['id'] == dataset_id for ds in datasets):
                selected_dataset = next(ds for ds in datasets if ds['id'] == dataset_id)
                break
            print("Invalid dataset ID. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

    # Try to read the selected dataset to obtain available date range
    available_start = None
    available_end = None
    try:
        ds_path = selected_dataset.get("path")
        ds_datatype = selected_dataset.get("datatype", "SMARD")
        if ds_path:
            df = load_data(path=ds_path, datatype=ds_datatype)
            if "Zeitpunkt" in df.columns:
                available_start = df["Zeitpunkt"].min()
                available_end = df["Zeitpunkt"].max()
    except Exception as e:
        # Loading failed - we still allow the user to provide dates manually
        print(f"Could not read dataset to determine available range: {e}")

    if available_start is not None and available_end is not None:
        print(f"\nAvailable data range for '{selected_dataset['name']}': {available_start.strftime('%d.%m.%Y %H:%M')}  -  {available_end.strftime('%d.%m.%Y %H:%M')}")

    # 2. Date range selection
    print("\nEnter date range (format: DD.MM.YYYY HH:MM)")
    while True:
        date_start = input("Start date: ")
        if validate_date(date_start):
            break
        print("Invalid date format. Please use DD.MM.YYYY HH:MM")
    
    while True:
        date_end = input("End date: ")
        if validate_date(date_end):
            break
        print("Invalid date format. Please use DD.MM.YYYY HH:MM")

    # 3. Energy sources selection
    energy_keys = list(CONST_ENERGY_SOURCES.keys())
    print("\nAvailable energy sources:")
    for i, source in enumerate(energy_keys):
        print(f"[{i}] {source} - {CONST_ENERGY_SOURCES[source]['name']}")
    
    print("\nSelect energy sources (enter numbers separated by spaces, or 'all' for all sources):")
    while True:
        sources_input = input("> ").strip()
        if sources_input.lower() == 'all':
            selected_sources = energy_keys
            break
        
        try:
            indices = [int(x) for x in sources_input.split()]
            selected_sources = [energy_keys[i] for i in indices if 0 <= i < len(energy_keys)]
            if selected_sources:
                break
            print("Please select at least one valid energy source.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter numbers separated by spaces or 'all'.")

    # 4. Plot name
    plot_name = input("\nEnter name for the plot: ").strip()
    while not plot_name:
        print("Plot name cannot be empty.")
        plot_name = input("Enter name for the plot: ").strip()

    # 4b. Plot description
    description = input("\nEnter an optional description for the plot (press Enter to skip): ").strip()

    # 5. Save option
    while True:
        save_option = input("\nDo you want to save the plot? (y/n): ").lower()
        if save_option in ['y', 'n']:
            save_plot = save_option == 'y'
            break
        print("Please enter 'y' for yes or 'n' for no.")

    # Return all selections
    return {
        "dataset": selected_dataset,
        "date_start": date_start,
        "date_end": date_end,
        "energy_sources": selected_sources,
        "plot_name": plot_name,
        "save_plot": save_plot,
        "description": description
    }

if __name__ == "__main__":
    # Test the interface
    result = get_user_input()
    print("\nSelected options:", result)
