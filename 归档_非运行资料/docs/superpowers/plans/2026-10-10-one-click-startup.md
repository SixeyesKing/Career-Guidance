# One-click project startup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Windows batch file that starts the project's API and UI with a double-click.

**Architecture:** A root-level batch file resolves its own directory, checks the project virtual-environment interpreter, launches the documented API and UI commands in separate persistent command windows, then opens the local UI URL.

**Tech Stack:** Windows batch, `cmd.exe`, project `.venv` Python, Uvicorn, Streamlit.

**Spec:** `docs/superpowers/specs/2026-10-10-one-click-startup-design.md`

## Global Constraints

- Use `.venv\Scripts\python.exe` and the documented ports 8002 and 8501.
- Do not install dependencies or overwrite `.env` or project data.
- Resolve paths relative to the batch file.

## Review Focus

- Launching from a working directory other than the project root must still use the project root.
- Missing `.venv\Scripts\python.exe` must show a setup hint and exit before opening services.
- Paths containing spaces must remain quoted in the child command lines.

---

### Task 1: Add the Windows startup launcher

**Files:**
- Create: `start.bat`

**Interfaces:**
- Consumes: `app.api:app`, `app/ui.py`, and `.venv\Scripts\python.exe` as documented in the project README.
- Produces: a root-level double-click launcher for `http://127.0.0.1:8501`.

- [ ] Resolve and switch to `%~dp0`, then check for the virtual-environment interpreter and print the README setup hint if it is missing.
- [ ] Launch Uvicorn on `127.0.0.1:8002` and Streamlit on `127.0.0.1:8501` in separate persistent command windows; open the Streamlit URL in the default browser.
- [ ] Review the final batch commands for quoting and confirm their module, script, and port arguments match the README; do not start long-running services as a verification step.
