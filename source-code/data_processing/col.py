import pandas as pd
from constants import ENERGY_SOURCES, SOURCES_GROUPS

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
        # print(f"Successfully created column '{new_column_name}' as sum of {len(valid_cols)} columns.")
        
        return df
    
    except Exception as e:
        print(f"Error in sum_columns: {e}")
        return df

def sum_columns_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sums up all valid numeric values from each column.

    Args:
        df: The input DataFrame.

        Returns: 
        A DataFrame containing the sums of each column.
    """
    try:
        col_sums = df.sum(numeric_only=True)
        sums_df = pd.DataFrame(col_sums).transpose()
        print("Successfully generated DataFrame with column sums.")
        return sums_df
    except Exception as e:
        print(f"Error in sum_columns_all: {e}")
        return pd.DataFrame()

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
    
def sum_rows(df: pd.DataFrame, new_column_name: str = None) -> pd.DataFrame:
    """
    Returns a new DataFrame containing the row-wise sums computed from the numeric
    columns of the input DataFrame.

    Args:
        df: The input DataFrame.
        new_column_name: Name for the new column containing the row sums.

    Returns:
        A new DataFrame with a single column named `new_column_name` that holds
        the sum of numeric values for each row. The original `df` is not modified.
    """
    try:
        sums = df.sum(axis=1, numeric_only=True)
        if not new_column_name:
            new_column_name = "Row_Sum"
        result_df = pd.DataFrame({new_column_name: sums})
        # print(f"Successfully generated new DataFrame with column '{new_column_name}' as sum of rows.")
        return result_df
    except Exception as e:
        print(f"Error in sum_rows: {e}")
        return pd.DataFrame()

def sum_all(df: pd.DataFrame) -> float:
    """
    Sums up all numeric values in the DataFrame.

    Args:
        df: The input DataFrame.

    Returns:
        The total sum of all numeric values in the DataFrame.
    """
    try:
        total_sum = df.select_dtypes(include='number').to_numpy().sum()
        # print(f"Successfully calculated total sum: {total_sum}")
        return total_sum
    except Exception as e:
        print(f"Error in sum_all: {e}")
        return 0.0

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