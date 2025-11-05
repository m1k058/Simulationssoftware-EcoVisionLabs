# CSV Calculation Mode - Enhanced Features

## Overview
The CSV Calculation Mode has been significantly enhanced to provide flexible and powerful data manipulation capabilities. Users can now perform various operations on datasets, combine data from multiple sources, and save results in different ways.

## New Functions in `data_processing.py`

### 1. `sum_columns(df, columns, new_column_name)`
**Purpose:** Sum up any selection of columns and create a new column with the result.

**Parameters:**
- `df`: The DataFrame to work with
- `columns`: List of column names to sum
- `new_column_name`: Name for the new column containing the sum

**Example:**
```python
df = sum_columns(df, ["Wind [MWh]", "Solar [MWh]"], "Wind+Solar Total")
```

**Features:**
- Validates that columns exist
- Warns about missing columns
- Creates new column with sum of all valid columns

---

### 2. `multiply_column(df, column, factor, new_column_name=None)`
**Purpose:** Multiply all values in a column by a given factor.

**Parameters:**
- `df`: The DataFrame to work with
- `column`: Name of the column to multiply
- `factor`: Multiplication factor (float)
- `new_column_name`: Optional - name for new column. If None, overwrites original

**Example:**
```python
# Convert MWh to GWh
df = multiply_column(df, "Generation [MWh]", 0.001, "Generation [GWh]")

# Double values in-place
df = multiply_column(df, "Price", 2.0)
```

**Use Cases:**
- Unit conversion (MWh → GWh, MW → kW)
- Apply scaling factors
- Calculate percentages
- Apply corrections to data

---

### 3. `add_column_from_other_df(df_target, df_source, column_name, new_column_name=None)`
**Purpose:** Copy a column from one DataFrame to another.

**Parameters:**
- `df_target`: DataFrame to add column to
- `df_source`: DataFrame to copy column from
- `column_name`: Name of column in source DataFrame
- `new_column_name`: Optional - name for column in target. If None, uses original name

**Example:**
```python
df_generation = add_column_from_other_df(
    df_generation, 
    df_consumption, 
    "Netzlast [MWh]",
    "Consumption [MWh]"
)
```

**Features:**
- Validates column exists in source
- Handles DataFrames of different lengths with warning
- Can rename column during copy

---

### 4. `sum_energy_sources(df, sources, name)` (renamed from `add_energy_source_generation_sum`)
**Purpose:** Sum energy sources based on predefined groups or custom selection.

**Parameters:**
- `df`: DataFrame with generation data
- `sources`: Energy source codes, list of codes, or group name ("All", "Renewable", "Conventional")
- `name`: Base name for new column (will add " [MWh]")

**Backward Compatibility:**
- Old function name `add_energy_source_generation_sum()` still works
- Internally calls the new `sum_energy_sources()` function

---

## Enhanced UI v2 - CSV Calculation Mode

### Main Menu Structure
```
=== CSV Calculation Mode ===

1) Select CSV and perform operations
2) Calculate DataFrame with column sums (quick)
0) Back
```

### Option 1: Interactive Operations Mode

When selecting a dataset, you enter an interactive workspace where you can:

**Available Operations:**

1. **Sum columns (custom selection)**
   - Select any columns by index
   - Give custom name to sum column
   - Works with any numeric columns

2. **Sum energy sources (predefined)**
   - Choose from predefined energy source groups
   - Uses constants from ENERGY_SOURCES
   - Automatic column name with [MWh] unit

3. **Multiply column by factor**
   - Select column to multiply
   - Enter multiplication factor
   - Option to create new column or overwrite

4. **Add column from another DataFrame**
   - Select source dataset
   - Choose column to copy
   - Optional: rename in target DataFrame
   - Handles length mismatches

5. **Add total generation (all sources)**
   - Quick operation for total generation
   - Creates "Gesamterzeugung [MWh]" column

6. **Add total renewable generation**
   - Quick operation for renewable sources
   - Creates "Gesamterzeugung Erneuerbare [MWh]" column

7. **Add total conventional generation**
   - Quick operation for conventional sources
   - Creates "Gesamterzeugung Konventionelle [MWh]" column

8. **View current columns**
   - List all columns with indices
   - Useful for reference before operations

9. **Preview data (first 10 rows)**
   - Quick view of current data state
   - Shows all columns

**S) Save Result** (see below)

---

### Save Options

When pressing **S** in the operations menu:

```
1) Save to session only (temporary)
   - Updates DataFrame in memory
   - Changes lost when program closes
   - Useful for quick testing

2) Save permanently (overwrite original dataset)
   - Overwrites the original file
   - Requires confirmation
   - Updates both file and memory

3) Save as new dataset (create copy)
   - Creates new CSV file
   - Optional: add to config.json
   - Original file unchanged

4) Export as CSV/Excel file
   - One-time export
   - Not tracked in config
   - Choose format (CSV or Excel)
```

---

### Option 2: Quick Column Sums

Fast path for calculating column sums:
- Select dataset
- Automatically generates single-row DataFrame with sum of each column
- Display in terminal
- Option to save as CSV or Excel

---

## Usage Examples

### Example 1: Create Combined Wind+Solar Column
```
1. CSV Calculation Mode → Select CSV
2. Choose generation dataset
3. Operation 1 (Sum columns)
4. Select wind and solar column indices
5. Name: "Combined_Renewables"
6. S → Save to session or permanent
```

### Example 2: Convert MWh to GWh
```
1. CSV Calculation Mode → Select CSV
2. Choose dataset
3. Operation 3 (Multiply column)
4. Select generation column
5. Factor: 0.001
6. New column name: "Generation [GWh]"
7. S → Save result
```

### Example 3: Combine Generation + Consumption Data
```
1. CSV Calculation Mode → Select CSV
2. Choose generation dataset
3. Operation 4 (Add column from another DF)
4. Select consumption dataset
5. Choose "Netzlast [MWh]" column
6. Rename to "Consumption [MWh]"
7. Continue with more operations or save
```

### Example 4: Calculate Balance (Generation - Consumption)
```
1. First add consumption column to generation dataset (Example 3)
2. Operation 1 (Sum columns)
3. Select generation column(s)
4. Name: "Total_Generation"
5. Operation 3 (Multiply column)
6. Select consumption column, factor: -1, new name: "Neg_Consumption"
7. Operation 1 (Sum columns again)
8. Select "Total_Generation" and "Neg_Consumption"
9. Name: "Balance"
10. S → Save result
```

---

## Benefits

### Flexibility
- Perform multiple operations in sequence
- See results immediately with preview
- Undo by restarting (load dataset again)

### Workflow Integration
- Session-only changes for experimentation
- Permanent save for finalized data
- Export options for sharing

### Power User Features
- Chain operations without saving between steps
- Combine data from multiple sources
- Create complex calculated columns

### Safety
- Original files never modified without confirmation
- Preview before saving
- Session mode for risk-free testing

---

## Technical Notes

### Column Name Handling
- Custom names for all operations
- Automatic unit suffix for energy sources " [MWh]"
- Rename on copy from other DataFrames

### Error Handling
- Validates column existence
- Handles DataFrame length mismatches
- Clear error messages
- Operations fail gracefully without data loss

### Performance
- All operations work on copies
- Original data preserved until save
- Efficient pandas operations

---

## Future Enhancements

Potential additions:
- Division operation
- Subtraction (column1 - column2)
- Percentage calculations
- Moving averages
- Filtering rows by criteria
- Merging DataFrames on timestamp
- Batch operations from script
