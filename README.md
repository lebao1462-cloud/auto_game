# Phong Than Proxy Manager

Windows desktop tool for managing multiple Phong Thần game clients with per-profile proxy routing.

## Features

- Multi-profile client management
- Per-profile SOCKS5 / HTTP proxy assignment
- Real routing verification: game PID → Proxifier → proxy endpoint
- Fail-closed protection to stop a client if routing falls back to DIRECT
- Background proxy health monitoring
- Automatic stale PID cleanup
- Proxy username/password storage with Windows DPAPI
- Authenticated proxy bridge so credentials are not written to Proxifier PPX files
- Dashboard, profile search/filter, diagnostics export, daily logs
- PyInstaller portable Windows build

## Tested

See `PLAN.md` and `TEST_REPORT.md` for implementation details and the final test matrix.

## Requirements

- Windows 10/11
- Python 3.14+ for development
- Proxifier Standard for routing
- See `requirements.txt` and `requirements-dev.txt`

## Run from source

```bat
run_app.bat
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

Runtime data, logs, backups, virtual environments, build outputs, local configuration, and third-party binaries are intentionally excluded from Git.
