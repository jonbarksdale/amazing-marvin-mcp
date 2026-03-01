# Task Attributes: Energy, Focus, Weight, Urgency, Importance, Physical

## Purpose

Expose Amazing Marvin's task attribute fields — energy, focus, mental weight, urgency, importance, and physical — in the MCP server's read and write tools.

## Problem

The MCP server does not surface six task attribute fields that Marvin stores and returns. Users cannot read these attributes in formatted output, nor set them via `create_task` or `update_item`.

## Requirements

- Read: display non-default attribute values in `format_task()` output
- Write: accept attribute parameters in `create_task` and `update_item`
- Clear: allow explicitly unsetting a field that was previously set
- No new tools; all changes fold into the existing layer stack
- Parameter types must be self-documenting per MCP best practices (parameters as LLM prompts)

## API Field Mapping

Verified against live API responses from sample tasks.

| Parameter | API field | Type | API values |
|---|---|---|---|
| `energy_amount` | `energyAmount` | scale | `1` (low), `2` (high), `False` (unset) |
| `focus_level` | `focusLevel` | scale | `1` (low), `2` (high), `False` (unset) |
| `mental_weight` | `mentalWeight` | scale | `2` (weighing), `4` (crushing), `False` (unset) |
| `is_physical` | `isPhysical` | bool | `True`, `False` |
| `urgency` | `isUrgent` | scale | `2` (urgent), `4` (fire), `False` (unset) |
| `importance` | `isStarred` | scale | `1` (important), `-1` (low), `False` (unset) |

Notes:
- `isUrgent` uses integers despite its boolean-sounding name; "fire" is a second urgency tier
- `isStarred` represents importance, not a simple star toggle; `-1` marks low priority
- `mentalWeight` values are 2/4, not 1/2 — requires explicit mapping, not arithmetic
- All fields use `False` as the "unset" sentinel

## Approach

### Layer changes

**`formatting.py`** — `format_task()` appends an attributes line when any field is set:
```
- [ ] Pick grapefruits (id: abc123) — scheduled: 2026-03-01
  Attributes: energy:high  focus:low  physical  urgency:fire
```
Unset fields are omitted. Scale fields render as `field:value`; `is_physical` renders as `physical` when true.

**`server.py`** — six new optional parameters on `create_task` and `update_item`:
```python
energy_amount: Literal["low", "high", "unset"] | None = None
focus_level:   Literal["low", "high", "unset"] | None = None
mental_weight: Literal["weighing", "crushing", "unset"] | None = None
is_physical:   bool | None = None
urgency:       Literal["urgent", "fire", "unset"] | None = None
importance:    Literal["important", "low", "unset"] | None = None
```

- `None` = omit (do not touch the field)
- `"unset"` / `False` = explicitly clear (sends `False` to API)
- Any other value = set

A `_build_attribute_setters()` helper encapsulates the value mappings. A shared `_ATTRIBUTE_MAPS` dict drives conversion so the mapping is defined once.

**`marvin.py`** — `create_task()` and `update_item()` pass through the new fields unchanged (already accepts `**kwargs` / `setters: dict`). No logic changes needed in this layer.

### Clearing semantics

`update_item` currently treats `None` as "omit". Scale fields add `"unset"` to their Literal to distinguish "omit" from "clear". Booleans use `False` to clear (natural Python semantics; `None` still means omit).

### Parameter descriptions (MCP best practices)

Each parameter description should explain:
1. What the attribute controls in Marvin
2. When to use it (the decision heuristic)
3. The available values inline

Example for `energy_amount`:
> Energy required by the task. Use 'low' for tasks safe to tackle when depleted; 'high' for tasks that need peak energy. Use 'unset' to clear a previously set value.

## Testing

- **Unit**: `test_formatting.py` — verify attribute line renders correctly for each field; verify omission when all fields are default
- **Unit**: `test_server.py` — verify `_build_attribute_setters()` maps all values correctly including `"unset"` → `False`
- **Integration**: create a task with attributes set, read it back, verify round-trip
- **Mutation**: run `just mutate` after adding tests; attribute mapping dict is a prime mutation target
