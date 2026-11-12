# WIDAL-SCAN AI — Wireless Edition
**ALL SYSTEM PROVIDE BY INUU**

Prototype starter: Next.js PWA + Supabase + Windows FastAPI/OpenCV Bridge + ESP32-CAM.

## Status
- Web dashboard: starter UI with camera connection settings, capture preview and watermark.
- Database: PostgreSQL schema, RLS policies and private Storage policies.
- Local Bridge: FastAPI starter; simulation mode works without hardware.
- Firmware: ESP32-CAM starter; adapt Wi-Fi provisioning and camera pin map to the exact board.
- Hardware capture and clinical classification are NOT validated. Do not use for patient diagnosis or clinical reporting.

## Web
Set Vercel Root Directory to `apps/web`. Build command: `npm run build`; install: `npm install`.
Optional env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.

## Windows Bridge
Install Python 3.11+, then in `services/bridge` run:
```bash
python -m venv .venv
# activate the environment
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8765
```
Simulation mode is enabled by default and creates a synthetic placeholder, not a specimen.

## Supabase
Run `supabase/migrations/001_initial_schema.sql` in Supabase SQL Editor. Review security policies before enabling real users. Do not store patient identifiers in this prototype.

**ALL SYSTEM PROVIDE BY INUU**
