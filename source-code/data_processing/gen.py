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