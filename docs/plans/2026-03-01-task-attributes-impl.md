# Task Attributes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose Amazing Marvin's six task attribute fields (energy, focus, mental weight, urgency, importance, physical) in read formatting and write tools.

**Architecture:** Add reverse-lookup display maps to `formatting.py` for rendering; add `_ATTRIBUTE_MAPS` and `_build_attribute_setters()` to `server.py` for input validation and API translation; add `extra_fields` passthrough to `marvin.py`'s `create_task`. No new tools — changes fold into `format_task`, `create_task`, and `update_item`.

**Tech Stack:** Python 3.11+, FastMCP, httpx, pytest, uv/just

---

## API field reference (verified from live API)

| Parameter | API field | Values (label → API value) |
|---|---|---|
| `energy_amount` | `energyAmount` | `"low"→1`, `"high"→2`, `"unset"→False` |
| `focus_level` | `focusLevel` | `"low"→1`, `"high"→2`, `"unset"→False` |
| `mental_weight` | `mentalWeight` | `"weighing"→2`, `"crushing"→4`, `"unset"→False` |
| `urgency` | `isUrgent` | `"urgent"→2`, `"fire"→4`, `"unset"→False` |
| `importance` | `isStarred` | `"important"→1`, `"low"→-1`, `"unset"→False` |
| `is_physical` | `isPhysical` | `True→True`, `False→False` |

- `None` always means "omit this field" (do not send to API)
- `"unset"` / `False` means "explicitly clear" (sends `False` to API)
- `False` sentinel in API means the field is not set

---

### Task 1: Add attribute rendering to `format_task()`

**Files:**
- Modify: `src/amazing_marvin_mcp/formatting.py`
- Test: `tests/test_formatting.py`

**Step 1: Write the failing tests**

Add to `TestFormatTask` in `tests/test_formatting.py`:

```python
def test_task_with_energy_amount_low(self) -> None:
    task = {"_id": "abc", "title": "T", "energyAmount": 1}
    result = format_task(task)
    assert "energy:low" in result

def test_task_with_energy_amount_high(self) -> None:
    task = {"_id": "abc", "title": "T", "energyAmount": 2}
    result = format_task(task)
    assert "energy:high" in result

def test_task_with_focus_level_low(self) -> None:
    task = {"_id": "abc", "title": "T", "focusLevel": 1}
    result = format_task(task)
    assert "focus:low" in result

def test_task_with_focus_level_high(self) -> None:
    task = {"_id": "abc", "title": "T", "focusLevel": 2}
    result = format_task(task)
    assert "focus:high" in result

def test_task_with_mental_weight_weighing(self) -> None:
    task = {"_id": "abc", "title": "T", "mentalWeight": 2}
    result = format_task(task)
    assert "weight:weighing" in result

def test_task_with_mental_weight_crushing(self) -> None:
    task = {"_id": "abc", "title": "T", "mentalWeight": 4}
    result = format_task(task)
    assert "weight:crushing" in result

def test_task_with_urgency_urgent(self) -> None:
    task = {"_id": "abc", "title": "T", "isUrgent": 2}
    result = format_task(task)
    assert "urgency:urgent" in result

def test_task_with_urgency_fire(self) -> None:
    task = {"_id": "abc", "title": "T", "isUrgent": 4}
    result = format_task(task)
    assert "urgency:fire" in result

def test_task_with_importance_important(self) -> None:
    task = {"_id": "abc", "title": "T", "isStarred": 1}
    result = format_task(task)
    assert "importance:important" in result

def test_task_with_importance_low(self) -> None:
    task = {"_id": "abc", "title": "T", "isStarred": -1}
    result = format_task(task)
    assert "importance:low" in result

def test_task_with_is_physical(self) -> None:
    task = {"_id": "abc", "title": "T", "isPhysical": True}
    result = format_task(task)
    assert "physical" in result

def test_task_no_attributes_no_attributes_line(self) -> None:
    task = {"_id": "abc", "title": "T"}
    result = format_task(task)
    assert "Attributes:" not in result

def test_task_false_attributes_not_rendered(self) -> None:
    """API sentinel value False means unset — should not render."""
    task = {"_id": "abc", "title": "T", "energyAmount": False, "isPhysical": False}
    result = format_task(task)
    assert "Attributes:" not in result

def test_task_multiple_attributes_on_one_line(self) -> None:
    task = {"_id": "abc", "title": "T", "energyAmount": 2, "focusLevel": 1, "isPhysical": True}
    result = format_task(task)
    assert "energy:high" in result
    assert "focus:low" in result
    assert "physical" in result
    # All attributes on a single "Attributes:" line
    lines = result.split("\n")
    attr_lines = [l for l in lines if "Attributes:" in l]
    assert len(attr_lines) == 1
```

**Step 2: Run tests to verify they fail**

```bash
just check
```
Expected: multiple failures in `TestFormatTask`

**Step 3: Implement attribute rendering in `formatting.py`**

Add after the existing imports, before `CHARACTER_LIMIT`:

```python
# Maps API field → {api_value: display_label}
# Used by format_task() to render task attributes.
_ATTRIBUTE_DISPLAY: list[tuple[str, str, dict[int, str]]] = [
    ("energyAmount", "energy", {1: "low", 2: "high"}),
    ("focusLevel",   "focus",  {1: "low", 2: "high"}),
    ("mentalWeight", "weight", {2: "weighing", 4: "crushing"}),
    ("isUrgent",     "urgency",     {2: "urgent", 4: "fire"}),
    ("isStarred",    "importance",  {1: "important", -1: "low"}),
]
```

Then at the end of `format_task()`, after the notes block, add:

```python
attrs: list[str] = []
for field, display_name, label_map in _ATTRIBUTE_DISPLAY:
    val = task.get(field)
    if val and val in label_map:
        attrs.append(f"{display_name}:{label_map[val]}")
if task.get("isPhysical"):
    attrs.append("physical")
if attrs:
    line += f"\n  Attributes: {'  '.join(attrs)}"
```

**Step 4: Run tests to verify they pass**

```bash
just check
```
Expected: all tests pass

**Step 5: Commit**

```bash
git add src/amazing_marvin_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: render task attributes in format_task output"
```

---

### Task 2: Add `_ATTRIBUTE_MAPS` and `_build_attribute_setters()` to `server.py`

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py`
- Test: `tests/test_server.py`

**Step 1: Write the failing tests**

Add a new `TestBuildAttributeSetters` class to `tests/test_server.py`.
Also add an import at the top: `from amazing_marvin_mcp.server import _build_attribute_setters`

```python
class TestBuildAttributeSetters:
    def test_all_none_returns_empty(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, None)
        assert result == {}

    def test_energy_low(self) -> None:
        result = _build_attribute_setters("low", None, None, None, None, None)
        assert result == {"energyAmount": 1}

    def test_energy_high(self) -> None:
        result = _build_attribute_setters("high", None, None, None, None, None)
        assert result == {"energyAmount": 2}

    def test_energy_unset(self) -> None:
        result = _build_attribute_setters("unset", None, None, None, None, None)
        assert result == {"energyAmount": False}

    def test_focus_low(self) -> None:
        result = _build_attribute_setters(None, "low", None, None, None, None)
        assert result == {"focusLevel": 1}

    def test_focus_high(self) -> None:
        result = _build_attribute_setters(None, "high", None, None, None, None)
        assert result == {"focusLevel": 2}

    def test_focus_unset(self) -> None:
        result = _build_attribute_setters(None, "unset", None, None, None, None)
        assert result == {"focusLevel": False}

    def test_mental_weight_weighing(self) -> None:
        result = _build_attribute_setters(None, None, "weighing", None, None, None)
        assert result == {"mentalWeight": 2}

    def test_mental_weight_crushing(self) -> None:
        result = _build_attribute_setters(None, None, "crushing", None, None, None)
        assert result == {"mentalWeight": 4}

    def test_mental_weight_unset(self) -> None:
        result = _build_attribute_setters(None, None, "unset", None, None, None)
        assert result == {"mentalWeight": False}

    def test_is_physical_true(self) -> None:
        result = _build_attribute_setters(None, None, None, True, None, None)
        assert result == {"isPhysical": True}

    def test_is_physical_false_clears(self) -> None:
        result = _build_attribute_setters(None, None, None, False, None, None)
        assert result == {"isPhysical": False}

    def test_urgency_urgent(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "urgent", None)
        assert result == {"isUrgent": 2}

    def test_urgency_fire(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "fire", None)
        assert result == {"isUrgent": 4}

    def test_urgency_unset(self) -> None:
        result = _build_attribute_setters(None, None, None, None, "unset", None)
        assert result == {"isUrgent": False}

    def test_importance_important(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "important")
        assert result == {"isStarred": 1}

    def test_importance_low(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "low")
        assert result == {"isStarred": -1}

    def test_importance_unset(self) -> None:
        result = _build_attribute_setters(None, None, None, None, None, "unset")
        assert result == {"isStarred": False}

    def test_multiple_fields_combined(self) -> None:
        result = _build_attribute_setters("high", "low", None, True, "urgent", None)
        assert result == {
            "energyAmount": 2,
            "focusLevel": 1,
            "isPhysical": True,
            "isUrgent": 2,
        }
```

Also add a test that verifies the new parameters appear in JSON schema:

```python
def test_attribute_params_use_literal_type(self) -> None:
    """Attribute scale params should expose allowed values in JSON schema."""
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    for tool_name in ("create_task", "update_item"):
        schema = tools[tool_name].parameters
        props = schema["properties"]
        for param in ("energy_amount", "focus_level", "mental_weight", "urgency", "importance"):
            prop = props[param]
            any_of = prop.get("anyOf", [])
            has_enum = "enum" in prop or any(
                "enum" in item for item in any_of if isinstance(item, dict)
            )
            assert has_enum, f"{tool_name}.{param} should use Literal type"
```

**Step 2: Run tests to verify they fail**

```bash
just check
```
Expected: `ImportError` or `AttributeError` for `_build_attribute_setters`

**Step 3: Implement `_ATTRIBUTE_MAPS` and `_build_attribute_setters()` in `server.py`**

Add after the existing `_WRITE_IDEMPOTENT` / `_DESTRUCTIVE` annotation constants (around line 136):

```python
# Maps parameter label → API value for each scale attribute field.
# False is the API sentinel meaning "unset/clear".
_ATTRIBUTE_MAPS: dict[str, dict[str, int | bool]] = {
    "energyAmount": {"low": 1, "high": 2, "unset": False},
    "focusLevel":   {"low": 1, "high": 2, "unset": False},
    "mentalWeight": {"weighing": 2, "crushing": 4, "unset": False},
    "isUrgent":     {"urgent": 2, "fire": 4, "unset": False},
    "isStarred":    {"important": 1, "low": -1, "unset": False},
}


def _build_attribute_setters(
    energy_amount: Literal["low", "high", "unset"] | None,
    focus_level: Literal["low", "high", "unset"] | None,
    mental_weight: Literal["weighing", "crushing", "unset"] | None,
    is_physical: bool | None,
    urgency: Literal["urgent", "fire", "unset"] | None,
    importance: Literal["important", "low", "unset"] | None,
) -> dict[str, Any]:
    """Convert MCP attribute parameters to API field setters.

    Returns only the fields that were explicitly provided (not None).
    'unset' maps to False (the API sentinel for clearing a field).
    """
    setters: dict[str, Any] = {}
    scale_fields = [
        ("energyAmount", energy_amount),
        ("focusLevel", focus_level),
        ("mentalWeight", mental_weight),
        ("isUrgent", urgency),
        ("isStarred", importance),
    ]
    for api_key, value in scale_fields:
        if value is not None:
            setters[api_key] = _ATTRIBUTE_MAPS[api_key][value]
    if is_physical is not None:
        setters["isPhysical"] = is_physical
    return setters
```

**Step 4: Run tests to verify they pass**

```bash
just check
```
Expected: all tests pass

**Step 5: Commit**

```bash
git add src/amazing_marvin_mcp/server.py tests/test_server.py
git commit -m "feat: add _build_attribute_setters and _ATTRIBUTE_MAPS to server"
```

---

### Task 3: Add attribute parameters to `create_task` tool and `marvin.py`

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py` (the `create_task` tool function)
- Modify: `src/amazing_marvin_mcp/marvin.py` (the `create_task` method)
- Test: `tests/test_marvin_integration.py`

**Step 1: Write the failing integration test**

Add to `TestWriteLifecycle` in `tests/test_marvin_integration.py`:

```python
@pytest.mark.asyncio
async def test_create_task_with_attributes(
    self, service: MarvinService, sandbox_parent_id: str
) -> None:
    task = await service.create_task(
        title="MCP Attributes Test",
        parent_id=sandbox_parent_id,
        extra_fields={"energyAmount": 2, "focusLevel": 1, "isPhysical": True},
    )
    task_id = task["_id"]
    try:
        assert task.get("energyAmount") == 2
        assert task.get("focusLevel") == 1
        assert task.get("isPhysical") is True
    finally:
        await service.delete_item(task_id)
```

**Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_marvin_integration.py::TestWriteLifecycle::test_create_task_with_attributes -v
```
Expected: `TypeError` — `create_task()` got unexpected keyword argument `extra_fields`

**Step 3: Add `extra_fields` to `marvin.py`'s `create_task`**

In `src/amazing_marvin_mcp/marvin.py`, update the `create_task` signature and body:

```python
async def create_task(
    self,
    title: str,
    day: str | None = None,
    due_date: str | None = None,
    parent_id: str | None = None,
    parent_name: str | None = None,
    label_ids: list[str] | None = None,
    note: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a task. Resolves parent_name to ID if provided."""
    body: dict[str, Any] = {"title": title}
    if day is not None:
        body["day"] = day
    if due_date is not None:
        body["dueDate"] = due_date
    if parent_name is not None:
        parent_id = await self._resolve_parent_id(parent_name)
    if parent_id is not None:
        body["parentId"] = parent_id
    if label_ids is not None:
        body["labelIds"] = label_ids
    if note is not None:
        body["note"] = note
    if extra_fields:
        body.update(extra_fields)

    result: dict[str, Any] = await self._client.post("/addTask", data=body)
    self.invalidate_caches()
    return result
```

**Step 4: Run integration test to verify it passes**

```bash
uv run pytest tests/test_marvin_integration.py::TestWriteLifecycle::test_create_task_with_attributes -v
```
Expected: PASS

**Step 5: Add attribute parameters to the `create_task` tool in `server.py`**

Update the `create_task` tool function signature to add the six new parameters and wire them through `_build_attribute_setters`:

```python
@mcp.tool(annotations=_WRITE)
@_handle_errors
async def create_task(
    title: str,
    day: str | None = None,
    due_date: str | None = None,
    parent: str | None = None,
    note: str | None = None,
    labels: list[str] | None = None,
    energy_amount: Literal["low", "high", "unset"] | None = None,
    focus_level: Literal["low", "high", "unset"] | None = None,
    mental_weight: Literal["weighing", "crushing", "unset"] | None = None,
    is_physical: bool | None = None,
    urgency: Literal["urgent", "fire", "unset"] | None = None,
    importance: Literal["important", "low", "unset"] | None = None,
) -> str:
    """Create a task. 'parent' can be a project name or ID. Dates use YYYY-MM-DD.

    energy_amount: Energy required. 'low' for depleted days, 'high' for peak energy tasks. 'unset' clears.
    focus_level: Concentration depth needed. 'low' for autopilot tasks, 'high' for deep work. 'unset' clears.
    mental_weight: Psychological burden. 'weighing' for tasks on your mind, 'crushing' for dreaded tasks. 'unset' clears.
    is_physical: True if the task requires physical presence or activity.
    urgency: Time sensitivity beyond due dates. 'urgent' for pressing tasks, 'fire' for drop-everything priority. 'unset' clears.
    importance: 'important' to highlight high-value tasks, 'low' to mark low-priority tasks. 'unset' clears.
    """
    _validate_date(day)
    _validate_date(due_date)
    svc = _get_service()
    kwargs: dict[str, Any] = {"title": title}
    if day is not None:
        kwargs["day"] = day
    if due_date is not None:
        kwargs["due_date"] = due_date
    if note is not None:
        kwargs["note"] = note
    if labels is not None:
        kwargs["label_ids"] = await _resolve_labels(svc, labels)
    if parent is not None:
        if _looks_like_id(parent):
            kwargs["parent_id"] = parent
        else:
            kwargs["parent_name"] = parent
    attr_setters = _build_attribute_setters(
        energy_amount, focus_level, mental_weight, is_physical, urgency, importance
    )
    if attr_setters:
        kwargs["extra_fields"] = attr_setters
    result = await svc.create_task(**kwargs)
    return f"Created: {format_task(result)}"
```

**Step 6: Run all tests**

```bash
just check
```
Expected: all pass

**Step 7: Commit**

```bash
git add src/amazing_marvin_mcp/server.py src/amazing_marvin_mcp/marvin.py tests/test_marvin_integration.py
git commit -m "feat: add attribute parameters to create_task"
```

---

### Task 4: Add attribute parameters to `update_item` tool

**Files:**
- Modify: `src/amazing_marvin_mcp/server.py` (the `update_item` tool function)
- Test: `tests/test_marvin_integration.py`

**Step 1: Write the failing integration test**

Add to `TestWriteLifecycle` in `tests/test_marvin_integration.py`:

```python
@pytest.mark.asyncio
async def test_update_item_sets_and_clears_attributes(
    self, service: MarvinService, sandbox_parent_id: str
) -> None:
    task = await create_test_task(service, sandbox_parent_id, "MCP Update Attributes Test")
    task_id = task["_id"]
    try:
        # Set attributes
        updated = await service.update_item(
            task_id,
            setters={"energyAmount": 2, "isUrgent": 2},
        )
        assert updated.get("energyAmount") == 2
        assert updated.get("isUrgent") == 2

        # Clear one attribute
        cleared = await service.update_item(
            task_id,
            setters={"energyAmount": False},
        )
        assert cleared.get("energyAmount") in (False, None, 0)
    finally:
        await service.delete_item(task_id)
```

**Step 2: Run the test to verify it passes (no marvin.py change needed)**

```bash
uv run pytest tests/test_marvin_integration.py::TestWriteLifecycle::test_update_item_sets_and_clears_attributes -v
```
Expected: PASS — `update_item` in marvin.py already accepts arbitrary setters

**Step 3: Add attribute parameters to the `update_item` tool in `server.py`**

```python
@mcp.tool(annotations=_WRITE_IDEMPOTENT)
@_handle_errors
async def update_item(
    item_id: str,
    title: str | None = None,
    day: str | None = None,
    due_date: str | None = None,
    note: str | None = None,
    backburner: bool | None = None,
    energy_amount: Literal["low", "high", "unset"] | None = None,
    focus_level: Literal["low", "high", "unset"] | None = None,
    mental_weight: Literal["weighing", "crushing", "unset"] | None = None,
    is_physical: bool | None = None,
    urgency: Literal["urgent", "fire", "unset"] | None = None,
    importance: Literal["important", "low", "unset"] | None = None,
) -> str:
    """Update task, project, or category fields. Pass only the fields you want to change.

    Set backburner=true to move an item to the backburner,
    or backburner=false to restore it.

    energy_amount: Energy required. 'low'/'high' to set, 'unset' to clear.
    focus_level: Concentration depth needed. 'low'/'high' to set, 'unset' to clear.
    mental_weight: Psychological burden. 'weighing'/'crushing' to set, 'unset' to clear.
    is_physical: True to mark as physical task, False to clear.
    urgency: 'urgent'/'fire' to set urgency tier, 'unset' to clear.
    importance: 'important'/'low' to set, 'unset' to clear.
    """
    setters: dict[str, Any] = {}
    if title is not None:
        setters["title"] = title
    if day is not None:
        _validate_date(day)
        setters["day"] = day
    if due_date is not None:
        _validate_date(due_date)
        setters["dueDate"] = due_date
    if note is not None:
        setters["note"] = note
    if backburner is not None:
        setters["backburner"] = backburner
    setters.update(
        _build_attribute_setters(energy_amount, focus_level, mental_weight, is_physical, urgency, importance)
    )
    if not setters:
        return "Error: No fields provided to update."
    result = await _get_service().update_item(item_id, setters)
    return f"Updated: {format_task(result)}"
```

**Step 4: Run all tests**

```bash
just check
```
Expected: all pass

**Step 5: Commit**

```bash
git add src/amazing_marvin_mcp/server.py tests/test_marvin_integration.py
git commit -m "feat: add attribute parameters to update_item"
```

---

### Task 5: Update README

**Files:**
- Modify: `README.md`

**Step 1: Update the `create_task` and `update_item` rows in the Tools table**

Change:

```
| `create_task` | Create a task (with optional project, dates, notes) |
| `update_item` | Update task, project, or category fields (title, dates, notes, backburner) |
```

To:

```
| `create_task` | Create a task (with optional project, dates, notes, and task attributes: energy, focus, mental weight, urgency, importance, physical) |
| `update_item` | Update task, project, or category fields (title, dates, notes, backburner, and task attributes) |
```

**Step 2: Run check to confirm nothing broke**

```bash
just check
```
Expected: all pass

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README for task attribute parameters"
```

---

### Task 6: Run mutation testing

**Step 1: Run mutation testing**

```bash
just mutate
```

**Step 2: Check results**

```bash
just mutate-report
```

Expected: kill rates for `marvin.py` and `formatting.py` have not regressed below thresholds (marvin.py ≤60% survival, formatting.py ≤43% survival). The new attribute map lookups in `formatting.py` and `server.py` should be well-covered by the tests written in Tasks 1 and 2.

**Step 3: If survival rates regressed, add targeted tests**

If `formatting.py` mutation survival is too high, the `_ATTRIBUTE_DISPLAY` list entries are prime targets. Add tests for the edge case where a field has a value not in the label_map (should not render):

```python
def test_unknown_attribute_value_not_rendered(self) -> None:
    """An API value with no label mapping should not appear in output."""
    task = {"_id": "abc", "title": "T", "energyAmount": 99}
    result = format_task(task)
    assert "energy:" not in result
```
