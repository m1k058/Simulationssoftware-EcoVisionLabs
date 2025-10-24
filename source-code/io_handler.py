from pathlib import Path
import pandas as pd
import csv
import re
from constants import HEADER_CLEAN_PATTERNS, EXPECTED_HEADERS, FILE_FORMAT_OPTIONS

def load_data(
    path: Path,
    datatype: str = "SMARD",
) -> pd.DataFrame:
    """Simple and safe File loader with following features:

    - Basic path and extension checks
    - Read and validate the header / first line against expected headers for `datatype`
    - Load File with proper separators, decimal/thousands formats, NA values and date formats
    - Light normalization of header names (removal of known patterns)
    - Create midpoint timestamp column 'Zeitpunkt' if 'Datum von' and 'Datum bis' are present

    Args:
        path: Path to the file
        datatype: A short identifier for expected layout (e.g. 'SMARD'). Used to choose expected headers and file format options.

    Returns:
        pd.DataFrame: Loaded and normalized DataFrame
    """

    # Validate datatype
    if not datatype:
        raise ValueError("datatype must be provided and cannot be None")
    if datatype not in EXPECTED_HEADERS:
        raise ValueError(
            f"Unsupported datatype '{datatype}'. "
            f"Supported: {list(EXPECTED_HEADERS.keys())}"
            f"You need to update constants.py to add support for this datatype."
            )
    if datatype not in FILE_FORMAT_OPTIONS:
        raise ValueError(
            f"Unsupported datatype '{datatype}'. "
            f"Supported: {list(FILE_FORMAT_OPTIONS.keys())}"
            f"You need to update constants.py to add support for this datatype."
        )

    
    cfg = FILE_FORMAT_OPTIONS[datatype]

    # Normalize path for Windows/Linux
    if not isinstance(path, Path):
        path = Path(path)

    # Path checks
    if not path.exists():
        raise FileNotFoundError("File not found: {0}".format(path))
    if not path.is_file():
        raise FileNotFoundError("Path is not a file: {0}".format(path))

    # File extension check
    if path.suffix.lower() not in {".csv", ".txt"}:
        print("Warn: file extension '{0}' is unexpected. Attempting to read anyway ;)".format(path.suffix))

    # Read first line to check headers
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=cfg["sep"])
        raw_header = next(reader)
        if not raw_header:
            raise ValueError(f"Could not read header line from {path}")
        header = [c.strip() for c in raw_header if c.strip() != ""]

    # Clean header
    clean_header = header[:]
    for pattern in HEADER_CLEAN_PATTERNS:
        clean_header = [re.sub(rf"\s*{pattern}\s*", "", c).strip() for c in clean_header]

    # Validate header
    expected = EXPECTED_HEADERS[datatype]
    unexpected = [c for c in clean_header if c not in expected]

    if clean_header != expected:
        raise ValueError(
            f"Header mismatch for datatype '{datatype}' in file {path}.\n"
            f"Unexpected columns: {unexpected}\n"
            f"Expected: {expected}\n"
            f"Found:    {clean_header}"
        )
    
    # Load Data into DataFrame fromated properly
    df = pd.read_csv(
        path,
        sep=cfg["sep"],
        encoding=cfg["encoding"],
        skiprows=1,
        header=None,
        decimal=cfg["decimal"],
        thousands=cfg["thousands"],
        na_values=cfg["na_values"],
        )
    df.columns = clean_header

    # Convert date columns
    for col in [c for c in df.columns if "Datum" in c]:
        df[col] = pd.to_datetime(df[col], format=cfg["date_format"], errors="coerce")

    # Create midpoint timestamp column
    if "Datum von" in df.columns and "Datum bis" in df.columns:
        df["Zeitpunkt"] = df["Datum von"] + (df["Datum bis"] - df["Datum von"]) / 2

    return df
