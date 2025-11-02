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
    df = add_energy_source_generation_sum(df, "All", "Gesamterzeugung")
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
    df = add_energy_source_generation_sum(df, "Renewable", "Gesamterzeugung Erneuerbare")
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
    df = add_energy_source_generation_sum(df, "Conventional", "Gesamterzeugung Konventionelle")
    return df

def add_energy_source_generation_sum(df: pd.DataFrame, sources="All", name="Summe Erzeugung") -> pd.DataFrame:
    """
    Calculates the sum of energy sources specified in the 'sources' argument
    for each timestamp and adds it as a new column to the DataFrame.

    Args:
        df: The input DataFrame with generation data.
        sources: A list of energy source shortcodes to sum up (e.g., ["KE", "BK"], "All", "Renewable").
        name: The name of the new column to be added (default is "Summe Erzeugung").

    Returns:
        The DataFrame with the additional column 'name' containing the sum of specified energy sources.
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
        
        # 2. Check if the columns exist in the DataFrame
        valid_cols = [col for col in renewable_sources_cols if col in df.columns]

        # 3. Calculate the sum
        df[name + " [MWh]"] = df[valid_cols].sum(axis=1)
        
        return df

    except KeyError as e:
        print(f"Fehler bei add_renewable_generation: Spalte nicht gefunden. {e}")
        return df
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return df
    
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