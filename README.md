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

## Role-based login

The first dashboard accounts are provisioned as:
- `inuu` — super admin (database role `admin`)
- `inu` — super admin (database role `admin`)
- `lab` — laboratory user (database role `atlm`)

No default passwords are committed. Create a Supabase project, run migrations `001_initial_schema.sql` and `002_username_accounts.sql`, then copy `apps/web/.env.accounts.example` to `apps/web/.env.accounts`. Put a different, strong password (12+ characters) in each environment variable and run from `apps/web`:

```powershell
npm run seed:accounts
```

Set these Vercel environment variables for the web app:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or legacy `NEXT_PUBLIC_SUPABASE_ANON_KEY`)

**Never put `SUPABASE_SERVICE_ROLE_KEY` in a `NEXT_PUBLIC_*` variable or the Vercel client environment.** The service-role key is only for the one-time local account bootstrap script.

ID login uses internal aliases in the reserved `.invalid` domain and Supabase Auth password verification. It does not send email.

## AI / ML research

- `services/ai/train.py`: image model foundation for visual agglutination grading. Requires real images and ATLM labels; it is not trained yet.
- `services/ai/train_clinical_baseline.py`: exploratory tabular baseline after manually verifying a Kaggle CSV, its target column, source licence, provenance and label quality.
- `services/ai/DATA-SOURCES.md`: source register for Kaggle, WHO and Kemenkes and their correct roles.

WHO/Kemenkes publications are reference material, not labelled patient datasets. The Kaggle candidate is tabular and cannot train the image classifier. All AI outputs remain research-only and require professional review.
