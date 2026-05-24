---
name: list_data_files
file: src/api/app.py
signature: GET /api/data-files  → { files: List[str] }
responsibility: Return the list of `.csv` filenames sitting in the project root. The frontend's FilePicker uses it to populate the dropdowns the user picks the candle / box CSVs from — without this the user would have to type paths by hand.
related: [[get_candles]], [[fe_components_chartpane]]
---

# `GET /api/data-files` → `list_data_files()`

Trivial directory listing scoped to the project root.

## Implementation

```python
root = three-dirname-walks-up-from(__file__)     # → repo root
files = sorted(
    f for f in os.listdir(root)
    if f.lower().endswith('.csv') and os.path.isfile(os.path.join(root, f))
)
return { "files": files }
```

The `three-dirname-walks-up` is `src/api/app.py → src/api → src → repo root`. The path is computed at request time rather than cached so renaming / moving the file during development just works.

## What appears in the result

Only `.csv` files. Subdirectories are not recursed. The active files the chart needs — `NQ_4h.csv`, `NQ_1m.csv`, `NQ_full_data.csv` — appear here; transient uploads land in this same directory via `POST /api/upload-data-file` so they show up too.

## What does NOT appear

- Files outside the repo root (no traversal).
- HTML, JSON, parquet — extension filter is hard-`'.csv'`.
- Directories.

## Frontend caller

The settings panel's FilePicker calls this on mount to build its dropdown of choices for the 4h, 1-min, and box CSV pickers. From the chart's point of view this endpoint is upstream of every candle / box render — without a valid `dataPath` the chart can't load anything.
