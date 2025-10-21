from pathlib import Path
import pandas as pd
from typing import Optional, Sequence, List
import os
import csv
import re

def load_data(
    path: Path,
    datatype: str = "SMARD",
    sep: str = ";",
    date_cols: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Simple and safe CSV loader focused on your requested features:

    - Basic path and extension checks
    - Read and validate the header / first line against expected headers for `datatype`
    - Convert specified German-formatted datetime columns to pandas datetimes

    Args:
        path: Path to the CSV file
        datatype: A short identifier for expected layout (e.g. 'SMARD'). Used to choose expected headers.
        sep: Field delimiter (default ';')

    Returns:
        pd.DataFrame: Loaded and lightly-normalized DataFrame
    """

    # Validate datatype
    if datatype==None:
        raise ValueError("datatype must be provided and cannot be None")
    if datatype not in {"SMARD", "OTHER"}:
        raise ValueError(f"Unsupported datatype '{datatype}'. Supported: 'SMARD', 'OTHER'.")

    # Normalize path for Linux/Windows
    if not isinstance(path, Path):
        path = Path(path)

    # Path checks
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Path is not a file: {path}")

    # File Extension check
    if path.suffix.lower() not in {".csv", ".txt"}:
        print(f"Warn: file extension '{path.suffix}' is unexpected. Attempting to read anyway ;)")

    # Read first line to check headers
    with path.open("r") as f:
        reader = csv.reader(f, delimiter=sep)
        header = next(reader)
        if not header:
            raise ValueError(f"Could not read header line from {path}")
        header = [c.strip() for c in header]

    # Validate header based on datatype
    # For SMARD we may encounter several header variants. We'll detect by normalizing
    # header names and ensuring required core columns exist. Then we'll later unify
    # (simplify) all column names so downstream code can rely on a consistent naming.
    def _normalize_for_matching(name: str) -> str:
        n = name.lower()
        # remove common words
        n = n.replace("berechnete auflösungen", "")
        n = n.replace("berechnete", "")
        n = n.replace("auflösungen", "")
        return n.strip()

    normalized_header = {h: _normalize_for_matching(h) for h in header}

    if datatype == "SMARD":
        # Core required columns (in various header variants these may appear with extra words)
        required = ["datumvon", "datumbis"]
        norm_values = set(normalized_header.values())
        missing_required = [r for r in required if r not in norm_values]
        if missing_required:
            raise ValueError(f"Header validation failed for datatype='SMARD'. Missing core columns (after normalization): {missing_required}. Header read: {header}")
    else:
        # OTHER expects at least 'datum' or similar
        req = ["datum"]
        if not any(x in normalized_header.values() for x in req):
            raise ValueError(f"Header validation failed for datatype='{datatype}'. Expected a 'Datum' column. Header read: {header}")

    # Read full CSV
    df = pd.read_csv(path, sep=sep)

    # Simplify/unify column names so later code can work with consistent names.
    # datatype-specific removal phrases (case-insensitive). These phrases will be removed
    # from the column name but bracketed units like '[MWh]' are preserved.
    removals_by_datatype = {
        "SMARD": [
            "berechnete auflösungen",
            "berechneteauflösungen",
            "berechnete aufloesungen",
            "berechnete",
            "auflösungen",
            "originalauflösung",
            "originalauflösungen",
            "originalaufloesung",
        ],
        "OTHER": [],
    }

    def _simplify_col(name: str) -> str:
        s = name
        # remove the configured phrases for this datatype only (case-insensitive)
        removals = removals_by_datatype.get(datatype, [])
        for r in removals:
            s = re.sub(r, "", s, flags=re.IGNORECASE)
        # normalize whitespace
        s = re.sub(r"\s+", " ", s).strip()
        return s

    new_columns = {old: _simplify_col(old) for old in df.columns}
    df = df.rename(columns=new_columns)

    # Parse German datetime columns if requested
    if date_cols:
        for col in date_cols:
            # after renaming, user might pass original names or simplified names; support both
            target_col = None
            if col in df.columns:
                target_col = col
            else:
                # try simplified form
                simp = _simplify_col(col)
                if simp in df.columns:
                    target_col = simp

            if target_col:
                s = df[target_col].astype(str).str.strip()
                s = s.replace('\u00a0', ' ')
                df[target_col] = pd.to_datetime(s, dayfirst=True, errors='coerce')
            else:
                print(f"Warn: requested date column '{col}' not found in file columns after normalization")

    return df