# One-click project startup design

## Goal

Provide a Windows batch file in the repository root that starts the Career Guidance app with a double-click.

## Behavior

- Resolve the project root from the batch file location so it works regardless of the current directory.
- Check that `.venv\Scripts\python.exe` exists; if it does not, print a clear setup hint and stop.
- Open the FastAPI service (`app.api:app`, port 8002) and Streamlit UI (`app/ui.py`, port 8501) in separate persistent command windows, using the project's virtual environment.
- Open the UI URL (`http://127.0.0.1:8501`) in the default browser.
- Do not install packages or overwrite local configuration as a side effect.

## Alternatives considered

1. A single `.bat` starts both services in separate windows. This is the recommended option because it needs no extra launcher and matches the documented manual workflow.
2. A `.bat` delegates to a PowerShell script. This provides more control but adds a second file without a need in this project.

## Error handling and scope

The launcher reports a missing virtual-environment interpreter and exits without changing files. Dependency installation, port conflict recovery, and service health monitoring remain outside this small launcher; the two service windows remain open so startup errors are visible.

## Review

Self-review: the launch commands and ports match the current README. The launcher is Windows-specific, consistent with the requested `.bat` file. It preserves `.env` and existing project data.
