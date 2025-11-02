# Histogram Plot Feature

## Overview
This document describes the histogram plot feature added to the EcoVisionLabs simulation software. The histogram visualizes the distribution of renewable energy share in total electricity consumption.

## What's New

### Histogram Plot Type
A new plot type `"histogram"` has been added to visualize the percentage share of renewable energy in total consumption over time.

**Key Features:**
- Shows distribution of renewable energy share in 10% bins (0-10%, 10-20%, ..., 90-100%)
- Includes an **overflow bin (100+)** for cases where renewable generation exceeds consumption
- Bins are displayed with proper labeling on the x-axis
- Y-axis shows the count of 15-minute intervals in each bin

### Technical Implementation

#### 1. Modified `plotting.py`
- Enhanced `plot_ee_consumption_histogram()` function:
  - Calculates renewable energy percentage automatically if needed
  - Creates bins from 0 to 100 in steps of 10
  - Adds overflow bin for values > 100%
  - Custom x-axis labels showing "100+" for the overflow bin
  - Comments and outputs in English

#### 2. Updated `plot_auto()` Function
- Added support for histogram plot type
- Handles dual DataFrames requirement (generation + consumption)
- Filters both datasets by the specified date range
- Passes data to histogram plotting function

#### 3. Enhanced UI v2 (`user_interface_v0_2.py`)
- Added histogram option (option 4) when creating new plots
- Prompts user to select two datasets:
  1. Generation dataset (containing renewable energy data)
  2. Consumption dataset (containing load data)
- Added histogram support in `run_plot_from_cfg_like()` for session plots
- Comments in English

#### 4. Updated `config_manager.py`
- Modified `create_plot_from_ui()` to support multiple DataFrames
- Added histogram plot type handling
- Backwards compatible with existing single-dataset plots

#### 5. Example Configuration (`config.json`)
Added a test histogram plot configuration:
```json
{
    "id": 3,
    "name": "Test Plot Renewable Energy Histogram",
    "dataframes": [1, 2],
    "date_start": "01.01.2023 00:00",
    "date_end": "31.01.2023 23:59",
    "plot_type": "histogram",
    "description": "Histogram showing distribution of renewable energy share in consumption"
}
```

## Usage

### Via UI v2
1. Run the application with UI v2
2. Select "Configure New Plot" → "Completely new (from scratch)"
3. Choose plot type 4 (Histogram - renewable energy share)
4. Select generation dataset (e.g., SMARD_2020-2025_Erzeugung)
5. Select consumption dataset (e.g., SMARD_2020-2025_Verbrauch)
6. Enter date range, name, and description
7. Choose whether to save to config.json
8. Generate the plot

### Via Configuration File
Add a histogram plot to `config.json`:
```json
{
    "id": <unique_id>,
    "name": "Your Histogram Name",
    "dataframes": [<generation_dataset_id>, <consumption_dataset_id>],
    "date_start": "DD.MM.YYYY HH:MM",
    "date_end": "DD.MM.YYYY HH:MM",
    "plot_type": "histogram",
    "description": "Your description"
}
```

### Programmatically
```python
from plotting import plot_ee_consumption_histogram

# Assuming df_generation and df_consumption are loaded DataFrames
plot_ee_consumption_histogram(
    config_manager=config_manager,
    df_erzeugung=df_generation,
    df_verbrauch=df_consumption,
    title="My Histogram",
    show=True,
    save=True,
    output_dir="output/test_plots"
)
```

## Interpretation

The histogram shows:
- **X-axis**: Renewable energy share in consumption (%)
- **Y-axis**: Number of 15-minute time intervals
- **Bins 0-90%**: Standard 10% intervals
- **Bin 100+**: Overflow bin containing all cases where renewable generation exceeded consumption

### Example Analysis
- High bars in lower bins (0-30%): Many periods with low renewable share
- High bars in upper bins (70-100+): Many periods with high renewable share or surplus
- Overflow bin (100+): Times when renewable generation exceeded total consumption

## Benefits
1. **Visual Distribution**: Clearly shows how often different renewable energy shares occur
2. **Surplus Detection**: Overflow bin highlights periods of renewable energy surplus
3. **Trend Analysis**: Compare histograms across different time periods
4. **Policy Planning**: Identify how often renewable targets are met

## Requirements
- Two datasets required:
  1. Generation data with renewable energy columns
  2. Consumption data with "Netzlast [MWh]" column
- Both datasets must cover the same time period
- Renewable generation column will be calculated automatically if not present

## Future Enhancements
- Customizable bin sizes
- Multiple histogram comparison
- Statistical summary (mean, median, percentiles)
- Export histogram data to CSV
