import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import pandas as pd
import warnings
import numpy as np

from datetime import datetime
from pathlib import Path
from constants import ENERGY_SOURCES
from errors import PlotNotFoundError, DataProcessingError, WarningMessage
from data_processing import gen

def plot_auto(config_manager, manager, plot_identifier, show=True, save=False, output_dir=None, darkmode=False):
	"""Automatically generates a plot based on configuration data with improved styling.

	This function reads the plot settings (time range, energy sources, type, etc.)
	from the ConfigManager, retrieves the relevant DataFrame from the DataManager,
	filters it by date, and calls the appropriate plotting function.

	Args:
		config_manager (ConfigManager):
			Instance providing plot definitions and global configuration.
		manager (DataManager):
			Instance providing loaded pandas DataFrames.
		plot_identifier (int | str):
			ID or name of the plot to generate.
		show (bool, optional):
			If True, the plot is displayed interactively (default = True).
		save (bool, optional):
			If True, the plot image is saved to the configured output directory (default = False).
		output_dir (Path, optional):
			Custom output directory. If None, the path is taken from config.GLOBAL["output_dir"].
		darkmode (bool, optional):
			If True, uses dark color scheme (default = False).

	Raises:
		PlotNotFoundError: If the requested plot configuration does not exist.
		DataProcessingError: If associated data cannot be found or processed.
		NotImplementedError: If the plot type is not supported.
	"""
	try:
		# Retrieve plot configuration
		PLOTS = config_manager.get_plots()
		output_dir = output_dir or config_manager.get_global("output_dir")

		if isinstance(plot_identifier, int):
			plot_cfg = next((p for p in PLOTS if p["id"] == plot_identifier), None)
		elif isinstance(plot_identifier, str):
			plot_cfg = next((p for p in PLOTS if p["name"] == plot_identifier), None)
		else:
			raise TypeError("plot_identifier must be an int (ID) or str (name).")

		if not plot_cfg:
			raise PlotNotFoundError(f"No plot with identifier '{plot_identifier}' found.")

		# Check assigned DataFrames
		df_ids = plot_cfg.get("dataframes", [])
		if not df_ids:
			raise DataProcessingError(f"Plot '{plot_cfg['name']}' has no DataFrames assigned.")
        
		# Histogram plot type requires exactly 2 DataFrames (generation + consumption)
		plot_type = plot_cfg.get("plot_type", "stacked_bar")
		if plot_type == "histogram":
			if len(df_ids) != 2:
				raise DataProcessingError(
					f"Plot '{plot_cfg['name']}' requires exactly 2 DataFrames (generation + consumption) for histogram."
				)
		elif len(df_ids) > 1:
			raise NotImplementedError(
				f"Plot '{plot_cfg['name']}' defines multiple datasets ({df_ids}). "
				"Combining multiple DataFrames is not yet supported."
			)

		# Load dataset(s)
		df_id = df_ids[0]
		df = manager.get(df_id)
		if df is None:
			raise DataProcessingError(
				f"DataFrame with ID '{df_id}' not found for plot '{plot_cfg['name']}'."
			)

		# Parse date range
		date_start = pd.to_datetime(plot_cfg["date_start"], format="%d.%m.%Y %H:%M", errors="coerce")
		date_end = pd.to_datetime(plot_cfg["date_end"], format="%d.%m.%Y %H:%M", errors="coerce")
		if pd.isna(date_start) or pd.isna(date_end):
			raise DataProcessingError(f"Invalid date format in plot '{plot_cfg['name']}'.")

		# Filter by date range
		df_filtered = df[(df["Zeitpunkt"] >= date_start) & (df["Zeitpunkt"] <= date_end)]
		if df_filtered.empty:
			raise DataProcessingError(f"No data found in the given time range for plot '{plot_cfg['name']}'.")

		# Choose plot type
		if plot_type == "stacked_bar":
			plot_stacked_bar(df_filtered, plot_cfg, show=show, save=save, output_dir=output_dir, darkmode=darkmode)
		elif plot_type == "line":
			cols = plot_cfg.get("columns")
			title = plot_cfg.get("name", "Line chart")
			description = plot_cfg.get("description", "")
			plot_line_chart(config_manager, df_filtered, columns=cols, title=title, description=description, show=show, save=save, output_dir=output_dir, darkmode=darkmode)
		elif plot_type == "balance":
			col1 = plot_cfg.get("column1")
			col2 = plot_cfg.get("column2")
			if not col1 or not col2:
				raise DataProcessingError(f"Plot '{plot_cfg['name']}' missing 'column1' or 'column2' for balance plot.")
			title = plot_cfg.get("name", "Balance plot")
			description = plot_cfg.get("description", "")
			plot_balance(config_manager, df_filtered, column1=col1, column2=col2, title=title, description=description, show=show, save=save, output_dir=output_dir, darkmode=darkmode)
		elif plot_type == "histogram":
			# Load second DataFrame for consumption data
			df_id_2 = df_ids[1]
			df_2 = manager.get(df_id_2)
			if df_2 is None:
				raise DataProcessingError(
					f"DataFrame with ID '{df_id_2}' not found for plot '{plot_cfg['name']}'."
				)
			# Filter second DataFrame by date range
			df_2_filtered = df_2[(df_2["Zeitpunkt"] >= date_start) & (df_2["Zeitpunkt"] <= date_end)]
			if df_2_filtered.empty:
				raise DataProcessingError(f"No consumption data found in the given time range for plot '{plot_cfg['name']}'.")
            
			title = plot_cfg.get("name", "Renewable Energy Share Histogram")
			description = plot_cfg.get("description", "")
			plot_ee_consumption_histogram(config_manager, df_filtered, df_2_filtered, title=title, description=description, show=show, save=save, output_dir=output_dir, darkmode=darkmode)
		else:
			raise NotImplementedError(f"Plot type '{plot_type}' is not implemented.")

	except Exception as e:
		# Catch both handled and unexpected errors for clean output
		warnings.warn(f"Plotting failed for '{plot_identifier}': {e}", WarningMessage)


def _setup_plot_style(darkmode=False):
	"""Set up the visual style for plots based on the main_custom_calc.py design.
    
	Args:
		darkmode (bool): If True, uses dark color scheme.
        
	Returns:
		dict: Dictionary containing all style parameters.
	"""
	# Update font manager
	fm.fontManager.__init__()
    
	# Color scheme
	if darkmode:
		COLOR_BG = "#1a1a1a"
		COLOR_BORDER = "#3B3B3B"
		COLOR_GRID = "#FFFFFF"
		COLOR_TEXT = "#FFFFFF"
	else:
		COLOR_BG = "#ffffff"
		COLOR_BORDER = "#3B3B3B"
		COLOR_GRID = "#000000"
		COLOR_TEXT = "#000000"
    
	# Fonts with fallback
	FONT_MAIN = 'Open Sans'
	FONT_WEIGHT_MAIN = 'normal'
	FONT_TITLE = 'Druk Wide Trial'
    
	# Check if custom fonts are available, otherwise use fallbacks
	available_fonts = [f.name for f in fm.fontManager.ttflist]
	if FONT_MAIN not in available_fonts:
		FONT_MAIN = 'Arial'
	if FONT_TITLE not in available_fonts:
		FONT_TITLE = 'Arial'
    
	# Matplotlib default settings
	plt.rcParams.update({
		'font.family': 'sans-serif',
		'font.sans-serif': [FONT_MAIN, 'Arial'],
		'font.size': 16,
		'font.weight': FONT_WEIGHT_MAIN
	})
    
	return {
		'COLOR_BG': COLOR_BG,
		'COLOR_BORDER': COLOR_BORDER,
		'COLOR_GRID': COLOR_GRID,
		'COLOR_TEXT': COLOR_TEXT,
		'FONT_MAIN': FONT_MAIN,
		'FONT_WEIGHT_MAIN': FONT_WEIGHT_MAIN,
		'FONT_TITLE': FONT_TITLE
	}
