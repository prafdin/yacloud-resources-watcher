# VM Status In Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show each compute instance's power state (running / stopped / …) next to its name in the Telegram inventory report.

**Architecture:** `Resource` gains an optional `status` string. `FetcherSpec` gains an optional `status_of` extractor; only the compute-instances spec sets it, mapping the YC `Instance.Status` enum to a lowercase label. `format_snapshot` appends `— <status>` to a resource line when `status` is present, leaving every other resource type untouched.

**Tech Stack:** Python 3.11, `yandexcloud` SDK (`yandex.cloud.compute.v1.instance_pb2.Instance.Status`), pytest.

**Spec:** none — direct change request. The requirement is: "в репорт должен попасть статус машины (запущена или остановлена)". This plan captures it in full.

## Global Constraints

- Runner: `.venv/bin/python -m pytest` from the repo root. Full suite must stay green (currently 88 tests).
- `Resource` and `FetcherSpec` stay frozen dataclasses; new fields are optional with a default so existing positional constructions keep working.
- No inline comments. A module-level function gets no docstring unless it already had one; keep bodies packed, no blank lines inside.
- Telegram output stays plain text — no Markdown, no HTML.
- Tests: one behaviour per test, the single assertion is the last statement, failure-style names phrased negatively where natural, spell "cannot"/"dont" without apostrophes.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011QV7jCqTJWiUNFjgDiS3i7
  ```
- Branch: `claude-try`.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/yc_watcher/models.py` | Pure data structures | Add `Resource.status: str \| None = None` |
| `src/yc_watcher/yc/fetchers.py` | Catalogue + shared fetch routine | Add `_instance_status` helper, `FetcherSpec.status_of` field, wire it into `fetch()`, set it on the compute spec |
| `src/yc_watcher/telegram/formatting.py` | Render snapshot as text | Add `_resource_line`, use it in `format_snapshot` |
| `tests/test_fetchers.py` | Fetcher behaviour | Fix 3 compute-touching tests, add status coverage |
| `tests/test_formatting.py` | Rendering behaviour | Add status-line coverage |

`test_inventory.py`, `test_handlers.py`, `test_scheduler.py` build `Resource("id", "name")` (two positional args) and are unaffected by the new optional field — do not touch them.

Reference for the enum (verified against `yandexcloud==0.405.0`):
`Instance.Status` values are `STATUS_UNSPECIFIED=0, PROVISIONING=1, RUNNING=2, STOPPING=3, STOPPED=4, STARTING=5, RESTARTING=6, UPDATING=7, ERROR=8, CRASHED=9, DELETING=10`. `Instance.Status.Name(2)` returns `"RUNNING"`.

---

### Task 1: Resource status + compute fetcher populates it

**Files:**
- Modify: `src/yc_watcher/models.py:12-15`
- Modify: `src/yc_watcher/yc/fetchers.py:11-14` (imports), `:56` (import `Resource` already there — add `Instance`), `:62-79` (`FetcherSpec`), `:83` (compute spec row)
- Test: `tests/test_fetchers.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `Resource(id: str, name: str, status: str | None = None)` — frozen dataclass, `status` is a lowercase label like `"running"`, `"stopped"`, `"provisioning"`, or `"unknown"` for an unspecified enum value, or `None` for resource types that do not report a state.
  - `yc_watcher.yc.fetchers._instance_status(item: Any) -> str` — reads `item.status` (int enum), returns the lowercase enum name, `"unknown"` when the value is `STATUS_UNSPECIFIED`.
  - `FetcherSpec(key, title, stub_ctor, request_cls, items_attr, status_of: Callable[[Any], str] | None = None)` — when `status_of` is set, `fetch()` calls it per item and stores the result in `Resource.status`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_fetchers.py` (after the existing `SPECS = {...}` line):

```python
def test_compute_fetcher_reports_running_instance():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="capusta", status=2)])})
    assert spec.fetch(client)[0].status == "running"


def test_compute_fetcher_reports_stopped_instance():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="capusta", status=4)])})
    assert spec.fetch(client)[0].status == "stopped"


def test_compute_fetcher_reports_unknown_for_unspecified_status():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="capusta", status=0)])})
    assert spec.fetch(client)[0].status == "unknown"


def test_compute_fetcher_keeps_id_and_name():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="capusta", status=2)])})
    assert (spec.fetch(client)[0].id, spec.fetch(client)[0].name) == ("r1", "capusta")


def test_non_compute_fetcher_leaves_status_unset():
    spec = SPECS["storage_buckets"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="b1", name="bucket")])})
    assert spec.fetch(client)[0].status is None
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_fetchers.py -k "status or keeps_id_and_name" -v`
Expected: the `compute_*` tests FAIL with `AttributeError: 'Resource' object has no attribute 'status'`; `test_non_compute_fetcher_leaves_status_unset` also FAILs for the same reason.

- [ ] **Step 3: Add the `status` field to `Resource`**

In `src/yc_watcher/models.py`, replace the `Resource` class body:

```python
@dataclass(frozen=True, slots=True)
class Resource:
    id: str
    name: str
    status: str | None = None
```

- [ ] **Step 4: Run the new tests again**

Run: `.venv/bin/python -m pytest tests/test_fetchers.py -k "status or keeps_id_and_name" -v`
Expected: `test_non_compute_fetcher_leaves_status_unset` and `test_compute_fetcher_keeps_id_and_name` now PASS; the three `test_compute_fetcher_reports_*` still FAIL (`status` is `None`, not the expected label).

- [ ] **Step 5: Add the status extractor and wire it into `FetcherSpec`**

In `src/yc_watcher/yc/fetchers.py`:

Add this import next to the other compute imports (around line 13):

```python
from yandex.cloud.compute.v1.instance_pb2 import Instance
```

Add this module-level function just above `PAGE_SIZE = 1000`:

```python
def _instance_status(item: Any) -> str:
    name = Instance.Status.Name(item.status)
    return "unknown" if name == "STATUS_UNSPECIFIED" else name.lower()
```

Replace the `FetcherSpec` dataclass with:

```python
@dataclass(frozen=True)
class FetcherSpec:
    key: str
    title: str
    stub_ctor: Callable[[Any], Any]
    request_cls: Callable[..., Any]
    items_attr: str
    status_of: Callable[[Any], str] | None = None

    def fetch(self, client) -> list[Resource]:
        stub = client.stub(self.stub_ctor)
        items = list_all(
            stub.List,
            lambda token: self.request_cls(
                folder_id=client.folder_id, page_size=PAGE_SIZE, page_token=token or ""
            ),
            lambda response: getattr(response, self.items_attr),
        )
        return [
            Resource(
                id=item.id or item.name,
                name=item.name or item.id,
                status=self.status_of(item) if self.status_of else None,
            )
            for item in items
        ]
```

- [ ] **Step 6: Set `status_of` on the compute-instances spec**

In `src/yc_watcher/yc/fetchers.py`, replace the first row of `FETCHERS`:

```python
    FetcherSpec("compute_instances", "🖥 Compute instances", InstanceServiceStub, ListInstancesRequest, "instances", status_of=_instance_status),
```

- [ ] **Step 7: Run the new tests again**

Run: `.venv/bin/python -m pytest tests/test_fetchers.py -k "status or keeps_id_and_name" -v`
Expected: all five new tests PASS.

- [ ] **Step 8: Fix the three existing compute-touching tests**

In `tests/test_fetchers.py`:

Restrict the parametrized mapping test to specs without a status extractor, so compute is covered by the dedicated tests from Step 1:

```python
@pytest.mark.parametrize("spec", [s for s in FETCHERS if s.status_of is None], ids=lambda s: s.key)
def test_fetcher_maps_items_to_resources(spec):
    attr = spec.items_attr
    client = FakeClient({"": _page(attr, [SimpleNamespace(id="r1", name="alpha")])})
    assert spec.fetch(client) == [Resource(id="r1", name="alpha")]
```

Give the fallback test's fake item a `status` and update its expected `Resource`:

```python
def test_fetcher_falls_back_to_id_when_name_is_blank():
    spec = SPECS["compute_instances"]
    client = FakeClient({"": _page(spec.items_attr, [SimpleNamespace(id="r1", name="", status=2)])})
    assert spec.fetch(client) == [Resource(id="r1", name="r1", status="running")]
```

Give the pagination test's fake items a `status` (its assertion is on `.id` only, so nothing else changes):

```python
def test_fetcher_follows_pagination():
    spec = SPECS["compute_instances"]
    attr = spec.items_attr
    client = FakeClient(
        {
            "": _page(attr, [SimpleNamespace(id="r1", name="a", status=2)], next_token="p2"),
            "p2": _page(attr, [SimpleNamespace(id="r2", name="b", status=2)]),
        }
    )
    assert [r.id for r in spec.fetch(client)] == ["r1", "r2"]
```

- [ ] **Step 9: Run the whole fetchers suite**

Run: `.venv/bin/python -m pytest tests/test_fetchers.py -v`
Expected: every test PASSES (the parametrized `test_fetcher_maps_items_to_resources` now shows 10 cases instead of 11).

- [ ] **Step 10: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all green.

- [ ] **Step 11: Commit**

```bash
git add src/yc_watcher/models.py src/yc_watcher/yc/fetchers.py tests/test_fetchers.py
git commit -m "$(cat <<'EOF'
Carry compute instance power state on Resource

Resource gains an optional status; FetcherSpec gains an optional status_of
extractor, set only on the compute-instances spec, mapping the YC
Instance.Status enum to a lowercase label.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011QV7jCqTJWiUNFjgDiS3i7
EOF
)"
```

---

### Task 2: Render the status in the report

**Files:**
- Modify: `src/yc_watcher/telegram/formatting.py:16-37`
- Test: `tests/test_formatting.py`

**Interfaces:**
- Consumes: `Resource.status: str | None` from Task 1.
- Produces: `format_snapshot` renders a resource with `status` set as `  • <name> — <status>`; a resource with `status` `None` renders unchanged as `  • <name>`. `_resource_line(resource) -> str` is a module-level helper returning that single line (no leading/trailing newline).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_formatting.py`:

```python
def test_instance_line_shows_running_status():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "capusta", "running"),))]
    )
    assert "  • capusta — running" in format_snapshot(snapshot)


def test_instance_line_shows_stopped_status():
    snapshot = _snapshot(
        [ResourceGroup("compute", "🖥 Compute instances", (Resource("i1", "capusta", "stopped"),))]
    )
    assert "  • capusta — stopped" in format_snapshot(snapshot)


def test_resource_without_status_has_no_status_suffix():
    snapshot = _snapshot(
        [ResourceGroup("buckets", "🪣 Object Storage buckets", (Resource("b1", "my-bucket"),))]
    )
    assert "my-bucket —" not in format_snapshot(snapshot)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_formatting.py -k "status" -v`
Expected: `test_instance_line_shows_running_status` and `test_instance_line_shows_stopped_status` FAIL (line rendered as `  • capusta`); `test_resource_without_status_has_no_status_suffix` PASSES already.

- [ ] **Step 3: Add `_resource_line` and use it**

In `src/yc_watcher/telegram/formatting.py`, add this module-level function above `format_snapshot`:

```python
def _resource_line(resource) -> str:
    if resource.status:
        return f"  • {resource.name} — {resource.status}"
    return f"  • {resource.name}"
```

In `format_snapshot`, replace the body-building line:

```python
        body = "\n".join(_resource_line(resource) for resource in group.resources) or "  (none)"
```

- [ ] **Step 4: Run the formatting suite**

Run: `.venv/bin/python -m pytest tests/test_formatting.py -v`
Expected: all tests PASS, including the pre-existing ones (they build `Resource` without a status, so their `  • <name>` expectations are unchanged).

- [ ] **Step 5: Run the full suite**

Run: `.venv/bin/python -m pytest`
Expected: all green (88 existing + 8 new).

- [ ] **Step 6: Commit**

```bash
git add src/yc_watcher/telegram/formatting.py tests/test_formatting.py
git commit -m "$(cat <<'EOF'
Show compute instance status in the inventory report

A resource line becomes "  • <name> — <status>" when a status is present;
every other resource type renders as before.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011QV7jCqTJWiUNFjgDiS3i7
EOF
)"
```

---

## Manual verification (optional, needs real credentials)

With `.env` + `sa-key.json` present (see the local-run notes), run a one-off inventory print and confirm the compute section now reads e.g. `  • capusta — running`:

```bash
.venv/bin/python - <<'EOF'
import asyncio
from yc_watcher.config import load_settings
from yc_watcher.telegram.formatting import format_snapshot
from yc_watcher.yc.client import YcClient
from yc_watcher.yc.inventory import collect_inventory

async def main():
    s = load_settings()
    c = YcClient.from_key_file(s.yc_sa_key_file, s.yc_folder_id)
    print(format_snapshot(await collect_inventory(c)))

asyncio.run(main())
EOF
```

## Self-Review

- **Spec coverage:** the single requirement — machine status in the report — is delivered by Task 1 (capture the state) + Task 2 (render it). No gaps.
- **Placeholder scan:** every step has concrete code or an exact command; no TBD / "handle edge cases" / vague error handling.
- **Type consistency:** `Resource.status: str | None` (Task 1) is the exact attribute read by `_resource_line` (Task 2). `FetcherSpec.status_of` is defined in Task 1 Step 5 and referenced by the filter in Task 1 Step 8 (`s.status_of is None`) and nowhere else. `_instance_status` is defined once and referenced only on the compute spec row. Enum value ints in tests (`2`, `4`, `0`) match the verified `Instance.Status` mapping.
