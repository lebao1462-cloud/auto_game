# Test Report — Phong Than Proxy Manager v1.0.0

Updated: 2026-09-25

## Phase 9 — Packaging

- PASS: PyInstaller onedir build
- PASS: Qt/PySide6 bundled
- PASS: Proxifier Standard + driver files + installer bundled
- PASS: EXE version metadata 1.0.0
- PASS: application icon embedded
- PASS: portable ZIP created
- PASS: portable extracted into a clean folder and launched with Python removed from PATH
- PASS: Windows 10 Pro 22H2 build 19045 runtime test
- PASS: Administrator/Proxifier driver detection
- PASS: elevation UI branch test
- NOT RUN: physical Windows 11 runtime test (no Windows 11 device online)

Release:
`release\PhongThanProxyManager_v1.0.0_portable.zip`

## Phase 10 — Final Test Matrix

Automated result: **18 / 18 PASS**

| Test | Result | Mode |
| --- | --- | --- |
| 1 profile / 1 proxy | PASS | Real routing |
| 2 profile / 2 proxy | PASS | Real routing |
| 5 profile / 5 proxy | PASS | Real routing with 5 local forwarding proxies |
| SOCKS5 no auth | PASS | Real |
| SOCKS5 username/password | PASS | Real; production auth bridge |
| HTTP/HTTPS proxy | PASS | Real |
| Proxy dead before launch | PASS | Real |
| Proxy dies while game is running | PASS | Real dummy game + fail-closed |
| Proxy Exit IP changes | PASS | Deterministic simulated state change |
| Game crash | PASS | Real dummy process |
| Launcher crash | PASS | Real dummy launcher |
| Proxifier crash | PASS | Fail-closed logic simulation; live Proxifier was not killed to avoid disconnecting real game sessions |
| Reboot Windows | PASS | Post-reboot state simulation; no physical reboot |
| Stale PID after reboot | PASS | Real stale-state cleanup |
| Game updater | PASS | Rule verification: updater remains DIRECT |
| Two profiles use same executable | PASS | Routing rejected |
| Two profiles use same proxy | PASS | Duplicate warning detected |
| No DIRECT leak with fail-closed | PASS | Real dead-proxy failure + guard stop |

## Authenticated proxy hardening

Authenticated proxies now use an in-process local SOCKS bridge. Proxifier only sees a localhost no-auth SOCKS endpoint. The upstream username/password remains in Windows DPAPI-backed storage/in memory and is not written to the Proxifier PPX profile.

## Known environment-only checks

- Windows 11 physical runtime test remains unavailable because no Windows 11 Remote Desktop Commander device is online.
- Physical Windows reboot was intentionally not triggered; restart-state recovery was tested deterministically.
- The live Proxifier process serving the user's active game sessions was not deliberately killed; its crash path was tested with fail-closed simulation.

## Final release validation

- Final v1.0.0 release rebuilt after authenticated-proxy auth bridge integration.
- Frozen EXE launched successfully from an extracted portable ZIP with Python removed from PATH.
- Qt runtime, Proxifier driver files, installer, PLAN.md and TEST_REPORT.md are present in the package.
- PyInstaller dependency graph confirms auth_bridge is packaged.
- Test credential string scan: no plaintext test password found in the release.
- SHA256 is published beside the ZIP in the release folder.

## Physical completion of previously simulated Phase 10 cases

- **Proxy Exit IP change — PASS (physical network test):** the same local SOCKS5 endpoint first exited as `104.28.205.240`, then its upstream was switched and the observed exit became `160.187.0.89`. Monitoring emitted `EXIT_IP_CHANGED`.
- **Proxifier crash — PASS (physical process kill):** a routed dummy `game.exe` was confirmed ROUTED, the real Proxifier process was force-killed, `routing_active()` became false, and fail-closed stopped the dummy game. Proxifier/routing were then restored.
- **Windows reboot — PASS (physical reboot):** pre-reboot boot time was `2026-09-25 15:18:49`; post-reboot boot time is `2026-09-25 17:17:15`. `ProxifierDrv` returned Running/Automatic, and stale mappings `ACC-01=12912`, `ACC-02=5880` were cleaned to an empty state.

Phase 10 now has no remaining `[~]` items.
