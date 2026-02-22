"""Thin config getters — delegiert direkt an constants.py.

Kein JSON, keine Klasse, kein State.
Alle Werte stehen statisch in constants.py und können auch direkt importiert werden.
"""

from ecovision.config import constants


def get_generation_year(tech: str, scenario: str = "average") -> int:
    """Gibt das SMARD-Referenzjahr für eine Technologie / Wetterprofil-Kombination zurück.

    Args:
        tech:     Technologie-Name, z.B. "Wind Onshore", "Photovoltaik"
        scenario: Wetterprofil — "good", "average" oder "bad"

    Returns:
        Vierstellige Jahreszahl als int (Fallback: default-Jahr aus constants)
    """
    table = constants.SIMULATION_SETTINGS["GENERATION_PARAMS"]["optimal_reference_years_by_technology"]
    tech_entry = table.get(tech, {})
    year = tech_entry.get(scenario)
    if year is None:
        year = table.get("default", 2022)
    return year


def get_generation_default_year() -> int:
    """Gibt das allgemeine SMARD-Referenz-Standardjahr zurück."""
    table = constants.SIMULATION_SETTINGS["GENERATION_PARAMS"]["optimal_reference_years_by_technology"]
    return table.get("default", 2022)


def get_ev_params() -> dict:
    """Gibt die statischen EV-Konfigurations-Parameter zurück."""
    return constants.SIMULATION_SETTINGS["EV_PARAMS"]


def get_temperature_dataset_names() -> list[str]:
    """Gibt die Namen aller Temperatur-Datensätze aus DATA_SOURCES zurück."""
    return [s["name"] for s in constants.DATA_SOURCES if s.get("datatype") == "Temperature"]
