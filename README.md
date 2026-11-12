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
Run `supabase/migrations/001_initial_schema.sql` and `002_username_accounts.sql` in Supabase SQL Editor before initializing user accounts. Review security policies before enabling real users. Do not store patient identifiers in this prototype.

**ALL SYSTEM PROVIDE BY INUU**

## Role-based login

The first dashboard accounts are provisioned as:
- `inuu` — super admin (database role `admin`)
- `inu` — super admin (database role `admin`)
- `lab` — laboratory user (database role `atlm`)

No default passwords are committed. Create a Supabase project and run migrations `001_initial_schema.sql` and `002_username_accounts.sql` in Supabase SQL Editor.

Configure Vercel Project → Settings → Environment Variables:
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL.
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — Supabase publishable/anon key.
- `SUPABASE_SERVICE_ROLE_KEY` — server-only service role secret; never prefix with `NEXT_PUBLIC_`.
- `BOOTSTRAP_SETUP_TOKEN` — a random secret of at least 32 characters.

Redeploy, open `/setup`, enter the setup token, and create three different passwords (minimum 12 characters) for `inuu`, `inu`, and `lab`. The wizard creates the Supabase Auth accounts and matching profiles. It does not need Node.js or npm on the client PC. The initial setup endpoint refuses to run again after all three profile records exist.

After successful setup, remove `SUPABASE_SERVICE_ROLE_KEY` and `BOOTSTRAP_SETUP_TOKEN` from Vercel and redeploy to close the setup endpoint. Keep only the two `NEXT_PUBLIC_*` browser variables for sign-in.

ID login uses internal aliases in the reserved `.invalid` domain and Supabase Auth password verification. It does not send email.

## AI / ML research

- `services/ai/train.py`: image model foundation for visual agglutination grading. Requires real images and ATLM labels; it is not trained yet.
- `services/ai/train_clinical_baseline.py`: exploratory tabular baseline after manually verifying a Kaggle CSV, its target column, source licence, provenance and label quality.
- `services/ai/DATA-SOURCES.md`: source register for Kaggle, WHO and Kemenkes and their correct roles.

WHO/Kemenkes publications are reference material, not labelled patient datasets. The Kaggle candidate is tabular and cannot train the image classifier. All AI outputs remain research-only and require professional review.
