# Offline status — 6 October 2026

## Delivered

- Signal age greater than 1,800 seconds gives OFFLINE for both module families. At exactly 1,800 seconds it remains NO_SIGNAL. Compressor keeps the existing 20-minute Online window; Vacuum keeps its 15-second Online and 90-second Stale windows, then uses NO_SIGNAL until 30 minutes.
- Device/module response status and Overview status counts derive from the same connectivity policy. Stored condition, scores and source rows are not rewritten by this display projection. New telemetry restores the stored condition on the next normal refresh.
- Offline Compressor cells use a grey background and solid borders; legend, tooltip and accessibility labels say Offline. Offline machines retain all registered module cells. Preview denominator counts all machines with Compressor modules (5 / 24 on this local fleet).
- Overview connectivity KPI now says Offline and agrees with the status distribution. Existing bounded caches/polling remain; summary uses one shared device/status/time query instead of two queries.

## Verification

- 65 Python tests pass, including deterministic boundary, UTC/Bangkok, reconnection and device/module/summary consistency checks.
- Final production frontend build passes; existing ECharts size warning remains.
- Actual localhost:5173 Overview: Offline 23, Good 1, fleet 24; both Offline counters agree. Compressor cells have grey background rgba(157,166,171,0.12), grey text, four solid border styles and an Offline accessible label. Caption 5 / 24 verified.
- Images: ../artifacts/offline-status-qa/dashboard.png and ../artifacts/offline-status-qa/compressor-matrix.png.
- Local Dashboard API restarted on its existing port 5001. This was not a Server deployment or source/Profile/Active mutation. Existing sessions signed with the process-local development key may require login again.
- Offline is connectivity evidence, not a fault diagnosis; retained Alerts/Work/Logs remain available.
