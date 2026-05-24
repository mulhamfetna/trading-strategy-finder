import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """Load CSV data into a pandas DataFrame.
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        DataFrame containing the CSV data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: For other CSV parsing errors
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    try:
        df = pd.read_csv(filepath)
        df.columns = df.columns.str.strip()
        col_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['open', 'high', 'low', 'close', 'volume']:
                col_mapping[col] = col.title()
            elif col_lower == 'time':
                col_mapping[col] = 'Time'
            elif col_lower == 'date':
                col_mapping[col] = 'Date'
            elif col_lower == 'datetime':
                # CSVs like NQ_4h.csv use a single 'datetime' column.
                # Map to 'Date' so the downstream pipeline can treat it
                # uniformly with the 1min/15min CSVs.
                col_mapping[col] = 'Date'
            elif col_lower == 'inc vol':
                col_mapping[col] = 'IncVol'
        if col_mapping:
            df = df.rename(columns=col_mapping)
        # Parse the Date column to real timestamps so downstream code can do
        # date arithmetic (e.g. walk_forward.split_folds). pandas 3.0
        # returns `str` dtype where pandas 2.x returned `object`, so check
        # both rather than gating on `== object`.
        if 'Date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Date']):
            try:
                df['Date'] = pd.to_datetime(df['Date'])
            except Exception:
                pass  # leave as-is; downstream code can still call to_datetime
        return df
    except Exception as e:
        raise Exception(f"Error reading CSV: {e}")