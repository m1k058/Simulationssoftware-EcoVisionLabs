import pandas as pd
from constants import ENERGY_SOURCES, SOURCES_GROUPS

def add_total_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the total generation from all energy sources
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.

    Returns:
        The DataFrame with the additional column 'Gesamterzeugung [MWh]'.
    """
    df = sum_energy_sources(df, "All", "Gesamterzeugung")
    return df

def add_total_renewable_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the total generation from all renewable energy sources
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.

    Returns:
        The DataFrame with the additional column 'Gesamterzeugung Erneuerbare [MWh]'.
    """
    df = sum_energy_sources(df, "Renewable", "Gesamterzeugung Erneuerbare")
    return df

def add_total_conventional_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the total generation from all conventional energy sources
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.

    Returns:
        The DataFrame with the additional column 'Gesamterzeugung Konventionelle [MWh]'.
    """
    df = sum_energy_sources(df, "Conventional", "Gesamterzeugung Konventionelle")
    return df

def sum_energy_sources(df: pd.DataFrame, sources="All", name="Summe Erzeugung") -> pd.DataFrame:
    """
    Calculates the sum of energy sources specified in the 'sources' argument
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.
        sources: A list of energy source shortcodes to sum up (e.g., ["KE", "BK"], "All", "Renewable").
        name: The name of the new column to be added (default is "Summe Erzeugung").

    Returns:
        The DataFrame with the additional column 'name [MWh]' containing the sum of specified energy sources.
    """
    try:
        # Get the list of shortcodes based on the input
        if isinstance(sources, str):
            shortcodes = SOURCES_GROUPS.get(sources, [sources])
        else:
            shortcodes = []
            for item in sources:
                if isinstance(item, str) and item in SOURCES_GROUPS:
                    shortcodes.extend(SOURCES_GROUPS[item])
                else:
                    shortcodes.append(item)

        sources_cols = [
            ENERGY_SOURCES[sc]["colname"]
            for sc in shortcodes
            if sc in ENERGY_SOURCES
        ]
        renewable_sources_cols = sources_cols
        
        # Check if the columns exist in the DataFrame
        valid_cols = [col for col in renewable_sources_cols if col in df.columns]

        # Calculate the sum
        df[name + " [MWh]"] = df[valid_cols].sum(axis=1)
        
        return df

    except KeyError as e:
        print(f"Error in sum_energy_sources: Column not found. {e}")
        return df
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return df


# Legacy function name for backward compatibility
def add_energy_source_generation_sum(df: pd.DataFrame, sources="All", name="Summe Erzeugung") -> pd.DataFrame:
    """
    Legacy function name. Use sum_energy_sources() instead.
    
    Calculates the sum of energy sources specified in the 'sources' argument
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.
        sources: A list of energy source shortcodes to sum up (e.g., ["KE", "BK"], "All", "Renewable").
        name: The name of the new column to be added (default is "Summe Erzeugung").

    Returns:
        The DataFrame with the additional column 'name [MWh]' containing the sum of specified energy sources.
    """
    return sum_energy_sources(df, sources, name)


def sum_columns(df: pd.DataFrame, columns: list, new_column_name: str) -> pd.DataFrame:
    """
    Sums up specified columns and adds the result as a new column.

    Args:
        df: The input DataFrame.
        columns: List of column names to sum up.
        new_column_name: Name for the new column containing the sum.

    Returns:
        The DataFrame with the additional column containing the sum.
    """
    try:
        # Check if columns exist
        valid_cols = [col for col in columns if col in df.columns]
        
        if not valid_cols:
            print(f"Error: None of the specified columns found in DataFrame.")
            return df
        
        if len(valid_cols) < len(columns):
            missing = [col for col in columns if col not in df.columns]
            print(f"Warning: The following columns were not found and will be skipped: {missing}")
        
        # Calculate sum
        df[new_column_name] = df[valid_cols].sum(axis=1)
        print(f"Successfully created column '{new_column_name}' as sum of {len(valid_cols)} columns.")
        
        return df
    
    except Exception as e:
        print(f"Error in sum_columns: {e}")
        return df


def multiply_column(df: pd.DataFrame, column: str, factor: float, new_column_name: str = None) -> pd.DataFrame:
    """
    Multiplies all values in a column by a given factor.

    Args:
        df: The input DataFrame.
        column: Name of the column to multiply.
        factor: The multiplication factor.
        new_column_name: Name for the new column (optional). If None, overwrites the original column.

    Returns:
        The DataFrame with the multiplied values.
    """
    try:
        if column not in df.columns:
            print(f"Error: Column '{column}' not found in DataFrame.")
            return df
        
        target_col = new_column_name if new_column_name else column
        df[target_col] = df[column] * factor
        
        if new_column_name:
            print(f"Successfully created column '{new_column_name}' = '{column}' * {factor}")
        else:
            print(f"Successfully multiplied column '{column}' by {factor}")
        
        return df
    
    except Exception as e:
        print(f"Error in multiply_column: {e}")
        return df


def add_column_from_other_df(df_target: pd.DataFrame, df_source: pd.DataFrame, 
                             column_name: str, new_column_name: str = None) -> pd.DataFrame:
    """
    Adds a column from one DataFrame to another DataFrame.

    Args:
        df_target: The DataFrame to which the column will be added.
        df_source: The DataFrame from which the column will be copied.
        column_name: Name of the column to copy from source DataFrame.
        new_column_name: Name for the column in target DataFrame (optional). If None, uses original name.

    Returns:
        The target DataFrame with the additional column.
    """
    try:
        if column_name not in df_source.columns:
            print(f"Error: Column '{column_name}' not found in source DataFrame.")
            return df_target
        
        target_col = new_column_name if new_column_name else column_name
        
        # Check if both DataFrames have the same length
        if len(df_target) != len(df_source):
            print(f"Warning: DataFrames have different lengths (target: {len(df_target)}, source: {len(df_source)})")
            print("Copying as many rows as possible...")
            min_len = min(len(df_target), len(df_source))
            df_target.loc[:min_len-1, target_col] = df_source.loc[:min_len-1, column_name].values
        else:
            df_target[target_col] = df_source[column_name].values
        
        print(f"Successfully added column '{target_col}' from source DataFrame.")
        
        return df_target
    
    except Exception as e:
        print(f"Error in add_column_from_other_df: {e}")
        return df_target
    
def generate_df_with_col_sums(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates a DataFrame with sums for each column from the input DataFrame.
    Args:
        df: The input DataFrame.
        Returns:
        A DataFrame containing the sums of each column.
    """
    col_sums = df.sum(numeric_only=True)
    sums_df = pd.DataFrame(col_sums).transpose()
    return sums_df