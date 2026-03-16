# Product Builders — Python Code Quality Review Report

**Reviewer:** Kieran (Python Reviewer)  
**Date:** 2025-03-16  
**Scope:** analyzers (database, auth, error_handling), generators (scopes, cursor_rules, cursor_hooks, cursor_permissions, onboarding), cli.py

---

## Executive Summary

The codebase is generally well-structured with clear separation of concerns. Pydantic models are used appropriately, and the CLI correctly uses Click exceptions. The main issues are: **duplicated logic** across analyzers, **one logic bug** in error_handling, **missing edge-case handling** in scopes loading, and **overly broad exception handling** in the list command.

---

## 1. Type Safety

### CRITICAL

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`load_scopes_yaml` assumes `zone_data` and `scope_data` are dicts** | `scopes.py:154-165` | Malformed YAML (e.g. `zones: frontend: "src"`) causes `AttributeError`. Add `isinstance(zone_data, dict)` and `isinstance(scope_data, dict)` guards; raise `ValueError` with a clear message on invalid structure. |
| **`ContributorRole(role_str)` can raise** | `scopes.py:161` | Invalid role string raises `ValueError`. Wrap in try/except and raise a domain-specific error: `raise ValueError(f"Invalid role in scopes.yaml: '{role_str}'")` after catching. |

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`assert isinstance` in production code** | `database.py:201, 205, 211, 216` | Assertions are disabled with `python -O`. Replace with explicit checks: `if not isinstance(dep_list, list): continue` or raise `TypeError`. |
| **`ProductProfile.load()` does not validate path** | `profile.py:117-119` | Callers (CLI) check existence, but the model is reusable. Consider adding an optional `path: Path` validation or document that callers must ensure path exists. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`Zone.paths` type coercion** | `scopes.py:156` | If YAML has `paths: "src/**"` (string), Pydantic will fail. Coerce: `paths=zone_data["paths"] if isinstance(zone_data.get("paths"), list) else []`. |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Return type of `validate_product_name`** | `config.py:40` | Returns `str` but is used for validation. Consider returning `None` on success and raising on failure (current design is fine; document that it raises). |

---

## 2. Error Handling

### CRITICAL

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`list_products` swallows all exceptions** | `cli.py:435-436` | `except Exception` hides `FileNotFoundError`, `json.JSONDecodeError`, `ValidationError`. Catch specific exceptions: `except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:` and log; show "?" for that row only. |

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`load_scopes_yaml` — no file existence check** | `scopes.py:150` | `path.read_text()` raises `FileNotFoundError` if path doesn't exist. Document or add: `if not path.exists(): raise FileNotFoundError(f"scopes.yaml not found: {path}")`. |
| **`save_scopes_yaml` — directory creation can fail** | `scopes.py:140` | `path.parent.mkdir(parents=True, exist_ok=True)` can raise `PermissionError`. Consider try/except with a clear message. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Generator registry `except Exception`** | `registry.py:43` | Catches `SyntaxError`, `ImportError` (beyond ModuleNotFoundError). Consider catching `(ImportError, SyntaxError, AttributeError)` explicitly. |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Click usage** | `cli.py` | Correct use of `click.BadParameter`, `click.ClickException`, `click.UsageError`. No `sys.exit` abuse. ✓ |

---

## 3. DRY & Consistency

### CRITICAL

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`_collect_dep_names` duplicated 3×** | `database.py:154-194`, `auth.py:88-107`, `error_handling.py:73-98` | Extract to `BaseAnalyzer._collect_dep_names(repo_path: Path) -> set[str]`. Database has pom.xml, Gemfile, csproj; Auth and ErrorHandling have subsets. Use a unified implementation that checks all known manifest types. |

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Scan pattern repeated** | `auth.py:154-156`, `auth.py:183-185`, `error_handling.py:141-143`, etc. | Extract `_get_scan_root(repo_path: Path) -> Path` and `_iter_source_files(scan_root, extensions, max_files)` to `BaseAnalyzer` to reduce duplication. |
| **`_build_zone_map` import from cursor_rules** | `onboarding.py:14` | `from product_builders.generators.cursor_rules import _build_zone_map` — coupling. Move to `product_builders.generators.scopes` or a shared `product_builders.generators.utils` module. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Magic numbers for scan limits** | `auth.py:158`, `auth.py:186`, `error_handling.py:148`, etc. | Define `MAX_FILES_PERMISSION_SCAN = 30`, `MAX_FILES_PROTECTED_ROUTES = 20`, etc. in base or a constants module. |
| **Naming: `role_alias` vs `role`** | `cli.py` | `role_alias` is the CLI string; `role` is `ContributorRole`. Clear. Consider `role_str` for the alias. |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`_ZONE_FRIENDLY_NAMES` in cursor_hooks** | `cursor_hooks.py:26-37` | Could be shared with scopes if zone descriptions are needed elsewhere. |

---

## 4. Edge Cases

### CRITICAL

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`load_scopes_yaml` — empty or invalid YAML** | `scopes.py:150-153` | `yaml.safe_load` returns `None` for empty file. `if not isinstance(data, dict)` catches it. But `data.get("zones", {})` on `None` would fail—we already check. Good. Add explicit `if data is None` for clarity. |
| **`generate_scope_config` mutates zones in place** | `scopes.py:110-118` | `config_zone.paths.extend(...)` mutates the Zone. If the same ScopeConfig is reused, paths accumulate. Prefer creating new Zone instances: `Zone(name=z.name, paths=z.paths + [".env*", "config/**"])`. |

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Django migration dir: `*/migrations`** | `database.py:135-138` | `candidates = list(repo_path.glob(migration_dir))` — for `*/migrations` returns multiple. `candidates[0]` picks one arbitrarily. Prefer the app closest to root or document behavior. |
| **Empty `zone.paths`** | `cursor_hooks.py:78` | `pathGlobs: zone.paths` — empty list means no paths match. Acceptable. |
| **`find_files(repo_path, "src/**/*.py")` with no src** | `error_handling.py:108` | Returns `[]`; loop doesn't run. Fine. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`feedback` — malformed existing YAML** | `cli.py:426-430` | If `feedback.yaml` exists but has invalid YAML, `safe_load` raises. Not caught. Add try/except and reset to `[]` on parse error. If `data` is a dict instead of list, prior feedback is lost. Use `existing = data if isinstance(data, list) else [data] if isinstance(data, dict) else []`. |
| **`bulk_analyze` — product missing `name` or `path`** | `cli.py:361-363` | `if product_name and product_path` — silently skips. Log a warning when skipping invalid entries. |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`get_profile(role)` when prof_def is None** | `cursor_rules.py:130` | `prof_def.display_name if prof_def else role.value` — handled. ✓ |

---

## 5. Performance

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Multiple full-tree scans in error_handling** | `error_handling.py` | `_detect_error_strategy`, `_detect_error_response_format`, `_detect_custom_error_classes` each do `rglob("*")` and read files. Consider a single pass that collects content and runs all three detectors. |
| **Auth: two similar scans** | `auth.py` | `_detect_permission_model` and `_detect_protected_routes` both walk the tree. Could share one traversal. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`find_files` with `**` glob** | `base.py:76-81` | `repo_path.glob("src/**/*.py")` is efficient. No change needed. |
| **Repeated `profile.scopes.get_zone`** | `cursor_hooks.py:73-74`, etc. | Called in loops. Consider building a `zone_by_name: dict[str, Zone]` once. |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`dict.fromkeys` for deduplication** | `cursor_permissions.py:64` | `list(dict.fromkeys(...))` preserves order. Good. ✓ |

---

## 6. Maintainability

### CRITICAL

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Bug: `break` in python-logging check** | `error_handling.py:108-112` | The `break` runs after the first file regardless of match. Result: only the first `src/**/*.py` file is checked. Fix: remove `break`; loop until a file with `import logging` is found, then `return "python-logging"`. |

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Guard pattern in `_detect_protected_routes`** | `auth.py:213-215` | `p = m if isinstance(m, str) and m else pat.strip("\\()")` — the regex `@UseGuards\((\w+)\)` returns a string match, so `m` is always str. Simplify. |
| **`error_response_format` regex** | `error_handling.py:191-193` | Very broad patterns; may match comments or strings. Consider tightening or documenting as heuristic. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Docstrings** | All modules | Module docstrings are good. Add docstrings for public functions in scopes.py (`auto_detect_zones`, `generate_scope_config`, `load_scopes_yaml`, `save_scopes_yaml`). |
| **Type hints** | Generators | All `generate` methods have correct signatures. ✓ |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **Testability** | Analyzers | `safe_analyze` wraps `analyze`; analyzers are stateless. Easy to unit test. ✓ |

---

## 7. Pydantic

### HIGH

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`Zone.paths` has no default** | `scopes.py` / `models/scopes.py:28` | `paths: list[str] = Field(description=...)` — required. In `load_scopes_yaml` we pass `zone_data.get("paths", [])`. If `paths` is missing, we pass `[]`. Consider `Field(default_factory=list)` for consistency with other list fields. |
| **`ScopeConfig` — duplicate zone names** | `models/scopes.py:57` | `get_zone(name)` returns first match. Duplicate zone names in YAML would be ambiguous. Add a validator: `@model_validator(mode='after')` to check zone names are unique. |

### MEDIUM

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`DatabaseResult.relationship_patterns`** | `analysis.py:67` | Has `default_factory=list` but database analyzer never populates it. Either implement or remove. |
| **`ProductMetadata.analysis_timestamp`** | `profile.py:53` | Uses `default_factory=lambda: datetime.now(tz=timezone.utc)`. Good. ✓ |

### LOW

| Issue | Location | Recommendation |
|-------|----------|----------------|
| **`Field(default_factory=dict)`** | `analysis.py:27` | `raw_data` — correct. ✓ |

---

## 8. New Code — Specific Findings

### Analyzers

| File | Severity | Finding |
|------|----------|---------|
| `database.py` | HIGH | Replace `assert isinstance` with explicit checks. |
| `database.py` | MEDIUM | `_collect_dep_names` — extract to base. |
| `auth.py` | HIGH | `_collect_dep_names` — extract to base. |
| `auth.py` | MEDIUM | Combine permission and protected-route scans. |
| `error_handling.py` | **CRITICAL** | Fix python-logging detection `break` bug. |
| `error_handling.py` | HIGH | `_collect_dep_names` — extract to base. |
| `error_handling.py` | MEDIUM | Single-pass scan for error strategy, format, custom classes. |

### Generators

| File | Severity | Finding |
|------|----------|---------|
| `scopes.py` | CRITICAL | Validate `zone_data`/`scope_data` in `load_scopes_yaml`; avoid mutating zones in place. |
| `scopes.py` | HIGH | Handle `ContributorRole(role_str)` ValueError. |
| `cursor_rules.py` | LOW | Consider moving `_build_zone_map` to shared module. |
| `cursor_hooks.py` | LOW | No critical issues. |
| `cursor_permissions.py` | LOW | No critical issues. |
| `onboarding.py` | MEDIUM | Depends on `_build_zone_map` from cursor_rules. |

### CLI

| File | Severity | Finding |
|------|----------|---------|
| `cli.py` | CRITICAL | Narrow `except Exception` in `list_products`. |
| `cli.py` | MEDIUM | Add warning when bulk-analyze skips invalid manifest entries. |
| `cli.py` | MEDIUM | Handle malformed `feedback.yaml` in feedback command. |

---

## Recommended Priority Order

1. **Fix the python-logging bug** (`error_handling.py`) — incorrect behavior.
2. **Extract `_collect_dep_names`** to `BaseAnalyzer` — reduces duplication and drift.
3. **Harden `load_scopes_yaml`** — validate structure, handle invalid roles.
4. **Stop mutating zones in `generate_scope_config`** — create new Zone instances.
5. **Narrow `except Exception` in `list_products`** — improve debuggability.
6. **Replace `assert isinstance` in database.py** — production robustness.
7. **Add `_get_scan_root` / `_iter_source_files`** to base — reduce scan duplication.
8. **Single-pass error detection** in error_handling — performance.

---

## Summary by Severity

| Severity | Count |
|----------|-------|
| CRITICAL | 5 |
| HIGH | 14 |
| MEDIUM | 18 |
| LOW | 10 |
