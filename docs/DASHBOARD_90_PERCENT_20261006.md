# Dashboard 90% display — 6 October 2026

Owner replaced the proposed scrollable desktop sidebar with a 90% overall display while retaining the current component arrangement.

- Removed the newly added internal navigation scrolling, overflow clipping and fixed footer overrides.
- Desktop Dashboard root uses CSS zoom 0.9 at browser zoom 100%. Grid order and existing responsive breakpoints remain; mobile layout retains its existing scale.
- Sidebar and full-screen/login heights compensate for the display scale. Logo, menus, account and Logout retain their existing order.
- Portal diagnostics use the same scale with compensated screen coordinates.

Verified actual localhost:5173 at 1280 x 720: visual viewport scale 1, root zoom 0.9; Logout bottom 707.4 px is fully visible; sidebar navigation has no vertical overflow and no scrollbar; document has no horizontal overflow. After scrolling the main page, Logout remains fully visible. Focused Compressor tooltip stays within the viewport. Screenshot: ../artifacts/dashboard-90-percent-qa/overview.png.

65 Python tests passed during this layout task; final production frontend build passed after the 90% replacement (existing ECharts size warning). No backend restart or data/profile change was needed for this presentation revision.
