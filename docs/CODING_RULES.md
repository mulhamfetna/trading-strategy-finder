# Coding Rules

This file lists the project-wide rules that every contributor (human or AI) must follow.

---

## 1. The no-fallback rule (strategy + data pipeline)

> **There is no silent fallback to a default value.**
> Every fallback site must raise an explicit error with the correct
> error type, a human-readable message, and a structured `system_status`
> payload that captures the context at the moment of failure.

### 1.1 Why

Silent fallbacks hide configuration drift. They were the root cause of
multiple bugs in the bug-bounty register (BUG-001, BUG-006, BUG-011,
BUG-015). When a parameter is missing, the system must say so loudly
instead of pretending it received a value.

### 1.2 Scope

The rule covers the **strategy + data pipeline**:

- All Pydantic request/response models in `src/api/schemas.py`.
- All Python dataclasses that carry strategy parameters
  (`ScalingParams`, `BoxStrategyParams`).
- All constructors and functions in `src/strategy/` and `src/data/`.
- All file-load + box-lookup paths.
- The SSE worker thread inside `src/api/app.py`.

The rule does **not** cover:

- Frontend `DEFAULT_*` constants — these are the *form's pre-populated
  starter state*, not engine fallbacks. The form always sends every
  field; the backend rejects partial payloads.
- Built-in Python sentinels (`None`, `[]`, `range()` over empty) when
  they represent *absence*, not a default value.
- Pure UI helpers (formatters, layout maths).

### 1.3 What's forbidden

```python
# Forbidden — silent fallback
policy = getattr(params, 'big_candle_resolution', 'big_candle_wins')
value  = data.get('key', 0)
score  = obj.field or 100
def run(params: Optional[ScalingParams] = None):
    params = params or ScalingParams()

# Forbidden — Pydantic field default
class BoxParamsModel(BaseModel):
    weekly_window_days: int = 7

# Forbidden — dataclass field default
@dataclass
class BoxStrategyParams:
    tp_target_points: float = 150.0
```

### 1.4 What's required

```python
# Required — raise on missing
policy = params.big_candle_resolution  # AttributeError if absent

if 'key' not in data:
    raise MissingParameterError('key', where='data dict in foo()')
value = data['key']

# Required — explicit None handling
if obj.field is None:
    raise ConfigurationError('field must be set', code='missing-field',
                             system_status={'object': repr(obj)})
score = obj.field

# Required — no Optional default
def run(params: ScalingParams) -> ...:
    ...  # caller must pass; TypeError if they forget

# Required — Pydantic Field(...)
class BoxParamsModel(BaseModel):
    weekly_window_days: int  # implicit Field(...) — required
    tp_target_points: float = Field(..., description="TP in points")  # explicit
```

### 1.5 Error types

Defined in `src/exceptions.py`:

| Class | Use for |
|---|---|
| `ConfigurationError(Exception)` | Base. Any code-level missing value. |
| `MissingParameterError(ConfigurationError)` | A required strategy / dict field was absent. |
| `MissingDataFileError(ConfigurationError)` | A CSV / data file that should exist isn't on disk. |
| `pydantic.ValidationError` | Automatically raised by Pydantic when an API request body is missing required fields. |

### 1.6 Surfacing errors

| Layer | Mechanism |
|---|---|
| API boundary (request body) | Pydantic raises `RequestValidationError`. FastAPI handler in `app.py` wraps it as a 422 JSON with `{code: 'request-validation-error', message, system_status: {path, method, errors, received_body}}`. |
| API boundary (internal error during request) | `ConfigurationError` caught by FastAPI handler → 422 JSON with `exc.to_payload()`. |
| SSE worker | Worker thread `try: ... except ConfigurationError as exc: q.put(('error', exc.to_payload()))`. Generic exceptions get a fallback payload that still includes `code` + `system_status`. |
| Inside the engine | `raise ConfigurationError(...)` or one of its subclasses. Never swallow. |

### 1.7 Test fixtures

Tests that construct strategy params or BoxLookup MUST use the helpers
in `tests/_fixtures.py`:

```python
from tests._fixtures import scaling_params, box_strategy_params, box_params_dict

# Direct dataclass — playbook defaults, override what you want
p = scaling_params(tp_target_points=50.0)
strat = ScalingStrategy(params=p)

# API request body — full dict
body = {'params': box_params_dict(reentry_enabled=False), 'data_path': '...', ...}
```

This keeps the "playbook defaults" in **one** place that's clearly
labelled as test-only, so future engineers don't mistake them for
runtime defaults.

### 1.8 Frontend equivalent

`frontend/src/types.ts` declares `BoxParams` with every field required
(no `?` markers on numeric / boolean fields). `DEFAULT_BOX_PARAMS`
pre-populates the form. The form always sends every field; backend
rejects partial payloads with 422. Frontend has no `?? 0` for required
strategy fields — those would mask backend issues.

---

## 2. Other rules (existing)

- **CLAUDE.md** — overall project guidance, run commands, conventions.
- **MASTER_STRATEGY_GUIDE.md** — single source of truth for strategy behaviour.
- **`docs/bug-checklist-revision-history.md`** — bug bounty knowledge base.
- **`docs/reviewer-playbook-segmented.md`** — 6-lens review process.

When in doubt: **be loud, not silent**. A noisy stack trace is always
better than a wrong number that silently slipped through.
