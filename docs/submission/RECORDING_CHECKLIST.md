# BARSA — Video Recording & Pre-Flight Checklist

## Pre-Recording Environment Checklist

1. **Resolution & Scaling**:
   - [ ] Set monitor resolution to 1920x1080 (1080p).
   - [ ] In Google Chrome / Edge, zoom to **110%** for maximum readability.
   - [ ] In Windows Terminal, set font size to **16pt** or **18pt** (Consolas / Cascadia Code).

2. **Services Running**:
   - [ ] Backend active: `http://localhost:8000/health` returns `healthy`.
   - [ ] Frontend active: `http://localhost:5173` loads without console errors.
   - [ ] FalkorDB Cloud connected: AWS Mumbai cluster active.

3. **Privacy & Security Audit**:
   - [ ] Ensure `.env` is never displayed in any open editor tab.
   - [ ] Clear browser bookmarks bar and unnecessary tabs.
   - [ ] Turn on Windows Focus Assist / Do Not Disturb (no notification popups).

4. **Recording Tools**:
   - [ ] Recommended: OBS Studio, Windows Game Bar (`Win + Alt + R`), or Loom.
   - [ ] Audio: Test microphone levels (no background fan noise, clear audio).

5. **Post-Recording**:
   - [ ] Check video length (target: 4:00 - 4:45).
   - [ ] Confirm no secrets or private tokens were flashed on screen.
   - [ ] Upload to YouTube (Unlisted or Public) or Loom.
   - [ ] Paste URL into `GRAPH_HACKS_SUBMISSION.md`.
