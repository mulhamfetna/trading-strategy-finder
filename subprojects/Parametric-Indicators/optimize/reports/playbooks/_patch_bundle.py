"""Patch the bundle's data.py + strategy.py to read a single portable data/ folder (<INST>_<tf>.csv,
<INST>_1m.csv, <INST>_box.csv) instead of the server's instrument registry. Idempotent-ish (guards on
marker)."""
import os, pathlib

d = pathlib.Path("optimize/data.py"); s = d.read_text()
if "_BUNDLE_DATA" not in s:
    s = s.replace(
        '_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"   # config.DATA_ROOT honours WSG_DATA_ROOT',
        '_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"   # config.DATA_ROOT honours WSG_DATA_ROOT\n'
        '# Shareable bundle: every instrument CSV lives in one folder, named <INST>_<tf>.csv (decision frame),\n'
        '# <INST>_1m.csv (1-minute frame), <INST>_box.csv (per-day box levels). Override the folder with WSH_BUNDLE_DATA.\n'
        '_BUNDLE_DATA = Path(os.environ.get("WSH_BUNDLE_DATA", str(Path(__file__).resolve().parents[1] / "data")))')
    s = s.replace(
        '''    if instrument == "NQ":
        box_csv = str(_BOX_CSV)
    else:
        from optimize import instruments
        box_csv = instruments.resolve_paths(instrument, "4h")[2]''',
        '''    box_csv = str(_BUNDLE_DATA / f"{instrument}_box.csv")''')
    s = s.replace(
        '''    if instrument == "NQ":
        dec_csv, min_csv = str(_RAW / f"NQ_{tf.name}.csv"), str(_RAW / "NQ_1m.csv")
    else:
        from optimize import instruments
        dec_csv, min_csv, _ = instruments.resolve_paths(instrument, tf.name)''',
        '''    dec_csv = str(_BUNDLE_DATA / f"{instrument}_{tf.name}.csv")
    min_csv = str(_BUNDLE_DATA / f"{instrument}_1m.csv")''')
    d.write_text(s); print("patched optimize/data.py")
else:
    print("data.py already patched")

st = pathlib.Path("strategy.py"); t = st.read_text()
if "uniform portable loader" not in t:
    t = t.replace(
        '''        from optimize.data import load_inputs as _load_tf
        if instrument == "NQ" and tf_name == "4h":
            _BUNDLE_CACHE[key] = load_inputs()                     # NQ-4h per-year split (parity-locked)
        elif instrument == "NQ":
            _BUNDLE_CACHE[key] = _load_tf(tf_name)                 # NQ all-history per-TF (unchanged)
        else:
            _BUNDLE_CACHE[key] = _load_tf(tf_name, instrument)     # ES all-history per-TF''',
        '''        from optimize.data import load_inputs as _load_tf
        _BUNDLE_CACHE[key] = _load_tf(tf_name, instrument)         # shareable bundle: uniform portable loader''')
    st.write_text(t); print("patched strategy.py get_bundle")
else:
    print("strategy.py already patched")
