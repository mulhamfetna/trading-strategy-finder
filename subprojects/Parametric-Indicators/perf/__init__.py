"""Performance / golden-gate tooling.

⚠️ THIS FILE IS LOAD-BEARING — do not delete it because it looks empty.

Without an __init__.py this directory is only a NAMESPACE package, and namespace packages have the
LOWEST priority in Python's import system: they are used only when no regular module of that name is
found anywhere on sys.path. On any machine that has the Linux perf-tool Python bindings installed
(/usr/lib/python3/dist-packages/perf.cpython-*.so) that system module WINS, even with
sys.path.insert(0, ".") — and every `from perf._common import ...` fails with the confusing

    ModuleNotFoundError: No module named 'perf._common'; 'perf' is not a package

which reads like the file is missing when it is sitting right there. That broke
optimize/test_news_veto.py at collection time and made study_vol_target.py (sizing Z3) and
run_nulltest.py unrunnable on such machines, while working fine on machines without the system module
— the worst kind of environment-dependent failure.

Making this a REGULAR package fixes it: sys.path[0] then wins outright.
"""
