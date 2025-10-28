import pandas as pd
from constants import ENERGY_SOURCES, SOURCES_GROUPS

def add_total_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet die Summe aller Erzeugungsquellen pro Zeitpunkt und fügt 
    sie als neue Spalte 'Gesamterzeugung' zum DataFrame hinzu.

    Args:
        df: Das Eingabe-DataFrame mit den Erzeugungsdaten.

    Returns:
        Das DataFrame mit der zusätzlichen Spalte 'Gesamterzeugung'.
    """
    try:
        # 1. Hol dir die Spaltennamen aller Erzeuger
        all_sources_cols = [
            ENERGY_SOURCES[shortcode]["colname"]
            for shortcode in SOURCES_GROUPS["All"]
            if shortcode in ENERGY_SOURCES
        ]
        
        # 2. Überprüfe, ob die Spalten im DataFrame existieren
        valid_cols = [col for col in all_sources_cols if col in df.columns]
        
        # 3. Berechne die Summe für jede Zeile (axis=1)
        df['Gesamterzeugung'] = df[valid_cols].sum(axis=1)
        
        return df
        
    except KeyError as e:
        print(f"Fehler bei add_total_generation: Spalte nicht gefunden. Details: {e}")
        return df
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return df


def add_renewable_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet die Summe der regenerativen Erzeugungsquellen (ohne Pumpspeicher)
    pro Zeitpunkt und fügt sie als 'Summe Regenerativ' hinzu.

    Args:
        df: Das Eingabe-DataFrame mit den Erzeugungsdaten.

    Returns:
        Das DataFrame mit der zusätzlichen Spalte 'Summe Regenerativ'.
    """
    try:
        # 1. Hol dir die Spaltennamen der regenerativen Quellen
        renewable_sources_cols = [
            ENERGY_SOURCES[shortcode]["colname"]
            for shortcode in SOURCES_GROUPS["Renewable"]
            if shortcode in ENERGY_SOURCES
        ]
        
        # 2. Überprüfe, ob die Spalten im DataFrame existieren
        valid_cols = [col for col in renewable_sources_cols if col in df.columns]
        
        # 3. Berechne die Summe
        df['Summe_Regenerativ'] = df[valid_cols].sum(axis=1)
        
        return df

    except KeyError as e:
        print(f"Fehler bei add_renewable_generation: Spalte nicht gefunden. {e}")
        return df
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return df


def add_conventional_generation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berechnet die Summe der konventionellen Erzeugungsquellen (ohne Pumpspeicher)
    pro Zeitpunkt und fügt sie als 'Summe Konventionell' hinzu.

    Args:
        df: Das Eingabe-DataFrame mit den Erzeugungsdaten.

    Returns:
        Das DataFrame mit der zusätzlichen Spalte 'Summe Konventionell'.
    """
    try:
        # 1. Hol dir die Spaltennamen der konventionellen Quellen
        conventional_sources_cols = [
            ENERGY_SOURCES[shortcode]["colname"]
            for shortcode in SOURCES_GROUPS["Conventional"]
            if shortcode in ENERGY_SOURCES
        ]
        
        # 2. Überprüfe, ob die Spalten im DataFrame existieren
        valid_cols = [col for col in conventional_sources_cols if col in df.columns]
        
        # 3. Berechne die Summe
        df['Summe_Konventionell'] = df[valid_cols].sum(axis=1)
        
        return df
        
    except KeyError as e:
        print(f"Fehler bei add_conventional_generation: Spalte nicht gefunden. Details: {e}")
        return df
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return df