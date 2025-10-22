from pathlib import Path
import csv
import re
import pandas as pd


def load_data(
    path: Path,
    datatype: str = "SMARD",
    sep: str = ";"
) -> pd.DataFrame:
    """CSV loader with strict header validation and column cleanup.

    - Checks path and file extension
    - Reads the header only, cleans datatype-specific suffix words, and validates structure
    - Loads the CSV and applies the same cleaning to column names
    - Optionally parses date columns (supports original or cleaned names)

    For SMARD, removes trailing resolution descriptors from column names such as
    "Berechnete Auflösung" or "Originalauflösung" so these words never appear in
    the DataFrame.
    """

    # Validate datatype
    if datatype is None:
        raise ValueError("datatype must be provided and cannot be None")
    if datatype not in {"SMARD", "OTHER"}:
        raise ValueError("Unsupported datatype '{0}'. Supported: 'SMARD', 'OTHER'.".format(datatype))

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

    # Helper: remove SMARD resolution suffixes from a column name
    def _strip_resolution_suffix(col: str) -> str:
        # Remove trailing resolution descriptors regardless of encoding glitches
        # Examples removed:
        # - " Berechnete Auflösung", " Berechnete Aufloesung", " Berechnete Auflösungen"
        # - " Originalauflösung", " Originalaufloesung", " Originalauflösungen"
        return re.sub(
            r"\s*(Berechnete\s+Aufl[oö]s(?:ung|ungen)|Berechnete\s+Aufloes(?:ung|ungen)|"
            r"Originalauf(?:l[oö]s(?:ung|ungen)|loes(?:ung|ungen))|Originalaufl.*)$",
            "",
            col,
            flags=re.IGNORECASE,
        )

    # Read first line to check headers
    with path.open("r") as f:
        reader = csv.reader(f, delimiter=sep)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("Could not read header line from {0}".format(path))
        if not header:
            raise ValueError("Could not read header line from {0}".format(path))
        header = [c.strip() for c in header]

    # Clean header for validation
    if datatype == "SMARD":
        cleaned_header = [_strip_resolution_suffix(h).strip() for h in header]
    else:
        cleaned_header = header[:]

    # Validate header shape depending on datatype
    if datatype == "SMARD":
        required = {"Datum von", "Datum bis"}
        missing = [r for r in required if r not in cleaned_header]
        if missing:
            raise ValueError(
                "Header validation failed for datatype='SMARD'. Missing required columns after cleaning: {0}. Read header: {1}".format(
                    missing, header
                )
            )
        # Ensure cleaning does not collapse columns into duplicates
        seen = set()
        dups = set()
        for c in cleaned_header:
            if c in seen:
                dups.add(c)
            seen.add(c)
        if dups:
            raise ValueError(
                "Header validation failed for datatype='SMARD'. Duplicate columns after cleaning: {0}. Please provide a file with a single resolution variant.".format(
                    sorted(dups)
                )
            )
    else:
        # Generic minimal check
        if not any(c.lower().startswith("datum") for c in cleaned_header):
            raise ValueError(
                "Header validation failed for datatype='{0}'. Expected at least one 'Datum' column. Read header: {1}".format(
                    datatype, header
                )
            )

    # Read full CSV
    df = pd.read_csv(path, sep=sep)

    # Clean/normalize column names so the resolution words never appear in the DataFrame
    if datatype == "SMARD":
        df = df.rename(columns=lambda c: _strip_resolution_suffix(str(c)).strip())
        # Safety: ensure no duplicates were introduced by renaming
        if df.columns.duplicated().any():
            dup_cols = sorted(list(pd.Index(df.columns)[df.columns.duplicated()]))
            raise ValueError(
                "Column rename produced duplicates after removing resolution suffixes: {0}. Please provide a file with only one resolution variant.".format(
                    dup_cols
                )
            )

    # Parse German datetime columns if requested
    if date_cols:
        for col in date_cols:
            target_col = None
            if col in df.columns:
                target_col = col
            else:
                # try the cleaned form used for SMARD
                simp = _strip_resolution_suffix(col)
                simp = re.sub(r"\s+", " ", simp).strip()
                if simp in df.columns:
                    target_col = simp

            if target_col:
                s = df[target_col].astype(str).str.strip()
                s = s.replace("\u00a0", " ")
                df[target_col] = pd.to_datetime(s, dayfirst=True, errors="coerce")
            else:
                print("Warn: requested date column '{0}' not found in file columns after normalization".format(col))

    return df

