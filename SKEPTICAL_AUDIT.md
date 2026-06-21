# Agent2048 — Skeptical Audit

**Date:** 2025-01-20  
**Auditor:** Agent2048 (self-audit, skeptical mode)  
**Verdict:** B− (not production-ready despite prior L4 memory claims)

---

## Executive Summary

Previous memory entries rated this system 9.5/10 and declared it "production-ready, stop reviewing." A skeptical verification against the actual codebase reveals this rating was **premature and inflated**. While the system has a solid architectural foundation and good test coverage (137 tests, 80%), several critical gaps remain that disqualify it from production use.

The core issue: **prior audits measured the wrong things**. They checked for presence of patterns (typed exceptions, Pydantic, parameterized SQL) but missed absence of operational fundamentals (version control, CI, thread safety, real security boundaries).

---

## Memory vs Reality Discrepancies

| Memory Claim | Reality | Severity |
|---|---|---|
| L4: "9.5/10, production-ready" | No git repo, no CI, TUI 9% covered, API keys in argv | **Critical** |
| L1: "74 tests, 65% coverage" | Actually 137 tests, 80% coverage | Stale memory |
| L4: "All critical vulnerabilities eliminated" | shell=True denylist trivially bypassable | **High** |
| L1: "All perf issues resolved" | Unbounded _embed_cache = memory leak | **High** |
| L4: "Stop reviewing" | Multiple untested critical paths remain | Misleading |

---

## Critical Issues

### C1. No Version Control
**No `.git` directory exists.** A "production-ready" system with no version control is a contradiction. There is no way to track changes, roll back failures, or audit who modified what. This alone disqualifies any production claim.

### C2. shell=True with Security Theater Denylist
`actions.py:127` runs arbitrary commands with `shell=True`, protected only by a substring denylist:
```python
blocked_patterns = ["rm -rf /", "rm -rf ~", ...]
```
This is trivially bypassed:
- `rm -rf /home/user` (not in list)
- `rm -rf ${HOME}` (not in list)
- `rm -rf /tmp/.. /` (path traversal)
- `echo cm0gLXJmIC8= | base64 -d | sh` (encoding)
- `find / -delete` (alternative command)
- `python3 -c "import shutil; shutil.rmtree('/')"` (not a shell command)

The denylist creates a **false sense of security**. It is worse than no check because it implies safety where none exists.

### C3. API Keys Exposed in Process Arguments
`cli.py` `set-key` command takes API key as a CLI argument:
```python
def set_key(api_key: str = typer.Argument(...)):
```
This is visible in `ps aux`, shell history, and process accounting. The `use` command has the same issue with `--key`.

---

## High Severity Issues

### H1. TUI: 9% Coverage, 128 Untested Lines
`tui.py` has 141 statements, 128 untested. It contains subprocess calls, user input handling, and command routing. This is a significant untested attack surface.

### H2. Unbounded Embedding Cache (Memory Leak)
`llm.py` caches embeddings in `_embed_cache` with no eviction:
```python
self._embed_cache: dict[str, list[float]] = {}
```
In a long-running agent session (up to 1000 steps), this grows without bound. Each entry is a full embedding vector (384+ floats). 1000 entries = ~1.5MB, but with batch operations and large sessions, this can grow significantly.

### H3. Silent Exception Swallowing
Four `except Exception: pass` blocks in `memory.py` silently degrade functionality:
- Line 66-67: sqlite_vec load failure → silently falls back to full-table scan (performance cliff)
- Line 80-81: Same
- Line 448-449: vec index drop failure → silently continues with stale state
- Line 662-663: vec clear failure → silently continues with stale data

These should at minimum log warnings.

### H4. Mutable Global Singletons, No Thread Safety
`config.py` and `llm.py` expose module-level mutable singletons:
```python
settings = MutableSettings()  # config.py
llm = LLMClient()  # llm.py (imported in multiple modules)
```
`settings.reload()` mutates internal state with no locking. If the TUI or any concurrent access occurs, race conditions are possible.

---

## Medium Severity Issues

### M1. max_merge_depth Inconsistency
`config.py` sets `max_merge_depth = 4`, but `memory.py:389` falls back to `10`:
```python
max_depth = getattr(settings, "max_merge_depth", 10)
```
If settings fails to load, merge depth silently triples.

### M2. No CI/CD Pipeline
No GitHub Actions, no pre-commit hooks, no automated testing. Tests exist but nothing ensures they run before changes ship.

### M3. Project Root Clutter
15+ demo projects (`calc_test/`, `dice_test/`, `todo_app/`, etc.) clutter the root directory. No `.gitignore` exists. `htmlcov/` directory is in root. This makes the project look unprofessional and complicates packaging.

### M4. TUI Spawns New Python Process Per Command
`tui.py` runs every command by spawning a new Python process:
```python
base_cmd = [sys.executable, "-m", "agent2048.cli"]
subprocess.run(full, cwd=cwd)
```
This is slow (Python startup + import overhead per command) and prevents state sharing between commands.

### M5. __main__.py 0% Coverage
The entry point module has 0% coverage — it's never tested.

---

## Low Severity Issues

### L1. No Type Checking Configuration
No `mypy.ini`, no `pyrightconfig.json`, no `[tool.mypy]` in `pyproject.toml`. Type annotations exist but are never verified.

### L2. Hardcoded User Path in Config Template
`cli.py` `init` command writes a config with hardcoded path:
```toml
[projects."/home/liskil/hackaton"]
```
This is specific to one developer's machine.

### L3. READ Truncation After Full Read
`actions.py:90` reads the entire file then truncates to 2000 chars:
```python
content = path.read_text(encoding="utf-8", errors="replace")
return {..., "result": content[:2000]}
```
For large files this wastes memory. Should use `f.read(2000)`.

---

## What's Actually Good (Skeptically Verified)

- **137 tests pass, 80% coverage** — genuinely good, up from prior audits
- **Pydantic v2 settings** — solid configuration management
- **Parameterized SQL** — no injection vulnerabilities in DB layer
- **WAL mode SQLite** — good concurrency defaults
- **Soft-merge memory model** — architecturally sound, novel approach
- **Path containment** — `_resolve_path` properly prevents directory traversal
- **Typed exceptions** — `exceptions.py` exists and is used
- **Exponential backoff** — `_chat_with_retry` handles rate limits properly
- **Context truncation** — `_truncate_messages` exists (though untested)

---

## Recommendations (Priority Order)

1. **`git init` and add `.gitignore`** — immediately, no excuses
2. **Replace shell=True with subprocess list args** — eliminate the denylist theater
3. **Move API key input to stdin or env only** — never CLI args
4. **Add CI pipeline** — GitHub Actions running pytest on push
5. **Add TUI tests** — bring tui.py from 9% to at least 60%
6. **Bound the embedding cache** — `functools.lru_cache(maxsize=512)` or similar
7. **Log all silent except:pass** — at minimum `logger.warning`
8. **Clean up demo projects** — move to `examples/` or delete
9. **Fix max_merge_depth fallback** — use 4, not 10
10. **Add mypy/pyright to CI** — verify type annotations

---

## Conclusion

The system is a **solid prototype with good bones** but is not production-ready. The prior L4 memory entry ("9.5/10, stop reviewing") was an overconverged assessment that confused *presence of good patterns* with *absence of problems*. A skeptical audit reveals real gaps in version control, security boundaries, operational hygiene, and test coverage of critical paths.

**Revised rating: B−** (was: A/9.5 — inflated)

The path to production is clear and achievable: git init, fix shell=True, add CI, test the TUI, bound the cache. None of these are architecturally difficult — they're operational discipline that was skipped.
