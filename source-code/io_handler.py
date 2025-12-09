from pathlib import Path
import pandas as pd
import csv
import re
import warnings
from errors import FileLoadError, DataProcessingError, WarningMessage
from constants import HEADER_CLEAN_PATTERNS, EXPECTED_HEADERS, FILE_FORMAT_OPTIONS


def load_data(path: Path, datatype: str = "SMARD"):
    """Load and validate a CSV or TXT dataset in a safe, structured way.

    Features:
        - Basic path and extension validation
        - Header validation against predefined formats
        - Proper parsing of separators, decimal/thousands format, NA values, and date columns
        - Automatic cleanup of known suffix patterns in headers
        - Automatic creation of midpoint timestamp column ("Zeitpunkt")

    Args:
        path (Path | str): Path to the dataset file.
        datatype (str, optional): Key used to identify header layout and format options.
            Must exist in EXPECTED_HEADERS and FILE_FORMAT_OPTIONS. Defaults to "SMARD".

    Returns:
        pd.DataFrame: Cleaned and formatted DataFrame ready for analysis.

    Raises:
        FileLoadError: If file is missing, not a file, or cannot be read.
        DataProcessingError: If header validation or parsing fails.
    """
    # --- Validate datatype
    if not datatype:
        raise DataProcessingError("Datatype must be provided and cannot be None.")

    if datatype not in EXPECTED_HEADERS:
        raise DataProcessingError(
            f"Unsupported datatype '{datatype}'. "
            f"Supported types: {list(EXPECTED_HEADERS.keys())}. "
            f"Update constants.py to add support."
        )
    if datatype not in FILE_FORMAT_OPTIONS:
        raise DataProcessingError(
            f"Unsupported datatype '{datatype}'. "
            f"Supported types: {list(FILE_FORMAT_OPTIONS.keys())}. "
            f"Update constants.py to add support."
        )

    cfg = FILE_FORMAT_OPTIONS[datatype]

    # --- Normalize and verify path
    path = Path(path)
    if not path.exists():
        raise FileLoadError(f"File not found: {path}")
    if not path.is_file():
        raise FileLoadError(f"Path is not a valid file: {path}")

    if path.suffix.lower() not in {".csv", ".txt"}:
        warnings.warn(
            f"File extension '{path.suffix}' is unexpected. Attempting to read anyway.",
            WarningMessage
        )

    # --- Read and clean header line
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=cfg["sep"])
            raw_header = next(reader)
            if not raw_header:
                raise DataProcessingError(f"Header line could not be read from {path}")
            header = [c.strip() for c in raw_header if c.strip() != ""]
    except Exception as e:
        raise FileLoadError(f"Failed to read file header: {e}")

    clean_header = header[:]
    for pattern in HEADER_CLEAN_PATTERNS:
        clean_header = [re.sub(rf"\s*{pattern}\s*", "", c).strip() for c in clean_header]

    # --- Validate header
    expected = EXPECTED_HEADERS[datatype]
    unexpected = [c for c in clean_header if c not in expected]
    if clean_header != expected:
        raise DataProcessingError(
            f"Header mismatch in file {path} for datatype '{datatype}'.\n"
            f"Unexpected columns: {unexpected}\n"
            f"Expected: {expected}\n"
            f"Found:    {clean_header}"
        )

    # --- Load data into DataFrame
    try:
        # Identifiziere Datumsspalten anhand der erwarteten Header
        date_columns = [i for i, col in enumerate(clean_header) if "Datum" in col]
        
        df = pd.read_csv(
            path,
            sep=cfg["sep"],
            encoding=cfg["encoding"],
            skiprows=1,
            header=None,
            decimal=cfg["decimal"],
            thousands=cfg["thousands"],
            na_values=cfg["na_values"],
            dtype={i: str for i in date_columns},  # Datumsspalten als String einlesen
        )
        df.columns = clean_header
    except Exception as e:
        raise DataProcessingError(f"Failed to parse CSV data from {path}: {e}")

    # --- Convert date columns
    try:
        for col in [c for c in df.columns if "Datum" in c]:
            date_format = cfg["date_format"]
            if date_format == "dayfirst":
                # Deutsches Datumsformat (dd.mm.yyyy) - robuster als striktes Format
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            else:
                # Verwende spezifisches Format wenn angegeben
                df[col] = pd.to_datetime(df[col], format=date_format, errors="coerce")
    except Exception as e:
        warnings.warn(f"Failed to convert date columns in {path}: {e}", WarningMessage)

    # --- Create midpoint timestamp column if applicable
    if "Datum von" in df.columns and "Datum bis" in df.columns:
        try:
            # Für jährliche Daten (z.B. installierte Leistung): extrahiere nur das Jahr
            if datatype == "SMARD-Inst":
                df["Zeitpunkt"] = df["Datum von"]
                df["Jahr"] = df["Datum von"].dt.year
            else:
                # Für zeitlich höher aufgelöste Daten: Mittelwert berechnen
                df["Zeitpunkt"] = df["Datum von"] + (df["Datum bis"] - df["Datum von"]) / 2
        except Exception as e:
            warnings.warn(f"Could not calculate 'Zeitpunkt' for {path}: {e}", WarningMessage)

    # --- Fill NaN with 0 to let MatPlot handle it
    numeric_cols = [c for c in df.columns if "[MWh]" in c]
    if numeric_cols:
        missing_count = df[numeric_cols].isna().sum().sum()
        if missing_count > 0:
            print(f"Info: Replacing {int(missing_count)} missing values with 0 in file '{path.name}'")

    df[numeric_cols] = df[numeric_cols].fillna(0)

    return df

def save_data(df: pd.DataFrame, path: Path, datatype: str = "SMARD") -> None:
    """Save a DataFrame to CSV with proper formatting based on datatype.

    Args:
        df (pd.DataFrame): DataFrame to save.
        path (Path | str): Destination file path.
        datatype (str, optional): Key used to identify format options.
            Must exist in FILE_FORMAT_OPTIONS. Defaults to "SMARD".

    Raises:
        DataProcessingError: If datatype is unsupported or saving fails.
    """
    # --- Validate datatype
    if not datatype:
        raise DataProcessingError("Datatype must be provided and cannot be None.")

    if datatype not in FILE_FORMAT_OPTIONS:
        raise DataProcessingError(
            f"Unsupported datatype '{datatype}'. "
            f"Supported types: {list(FILE_FORMAT_OPTIONS.keys())}. "
            f"Update constants.py to add support."
        )

    cfg = FILE_FORMAT_OPTIONS[datatype]

    # --- Save DataFrame to CSV
    try:
        df.to_csv(
            path,
            sep=cfg["sep"],
            encoding=cfg["encoding"],
            index=False,
            decimal=cfg["decimal"],
            na_rep=cfg["na_values"][0] if cfg["na_values"] else "",
        )
    except Exception as e:
        raise DataProcessingError(f"Failed to save DataFrame to {path}: {e}")


def save_data_excel(df: pd.DataFrame, path: Path) -> None:
    """Save a DataFrame to Excel format (.xlsx).

    Args:
        df (pd.DataFrame): DataFrame to save.
        path (Path | str): Destination file path.

    Raises:
        DataProcessingError: If saving fails or openpyxl is not installed.
    """
    try:
        df.to_excel(
            path,
            index=False,
            engine='openpyxl'
        )
    except ImportError:
        raise DataProcessingError(
            "Excel export requires 'openpyxl' library. "
            "Install it with: pip install openpyxl"
        )
    except Exception as e:
        raise DataProcessingError(f"Failed to save DataFrame to Excel {path}: {e}")