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
All 12 migrations in `supabase/migrations/` are applied to the connected Supabase project. For a fresh project, apply `001` through `012` in numeric order. Migrations 005–006 add AI registry/private storage; 007–008 move role lookup into a private schema and rebuild RLS; 009–012 register one-time bootstrap and dataset governance. Migration 003 limits each lab user to examinations they created; admins/reviewers retain review access. Review security policies before enabling real users. Do not store patient identifiers in this prototype.

**ALL SYSTEM PROVIDE BY INUU**

## Role-based login

The first dashboard accounts are provisioned as:
- `inuu` — sole super admin (database role `admin`, display name `Inuu`)
- `avi_lab` — laboratory user (database role `atlm`, display name `Avi_Lab`)
- `riska_lab` — laboratory user (database role `atlm`, display name `Riska_lab`)

No default passwords are committed. All 12 migrations `001`–`012` are applied in the connected project. For another project, run the files in numeric order. Migration 004 retires the old starter IDs and ensures only Inuu retains the admin role; later migrations add security hardening, model registry, private storage, bootstrap guard, and external dataset registry.

Configure these three Vercel Project → Settings → Environment Variables for Production and Preview:
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL.
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` — Supabase publishable key.
- `BOOTSTRAP_SETUP_TOKEN` — the one-time setup token (at least 32 random characters).

The privileged account-creation logic runs in the deployed Supabase Edge Function `bootstrap-accounts`, which reads the Supabase-managed `SUPABASE_SECRET_KEYS` / legacy service role key inside the function runtime. Do not copy a secret key to Vercel or the browser.

Redeploy, open `/setup`, enter the one-time token, and create three different passwords (minimum 12 characters) for `Inuu`, `Avi_Lab`, and `Riska_lab`. The wizard creates Supabase Auth users and matching profiles. It does not need Node.js or npm on the client PC. The Edge Function validates a SHA-256 token verifier, and the database marks the token consumed after successful setup.

After successful setup, remove `BOOTSTRAP_SETUP_TOKEN` from Vercel and redeploy to close the Vercel bootstrap proxy. The Supabase Edge Function will also reject requests once the three profiles exist and the database token has been consumed. Keep the two `NEXT_PUBLIC_*` variables for sign-in.

ID login uses internal aliases in the reserved `.invalid` domain and Supabase Auth password verification. It does not send email.

## AI / ML research

- `services/ai/train.py`: image model foundation for visual agglutination grading. Requires real images and ATLM labels; it is not trained yet.
- `services/ai/train_clinical_baseline.py`: exploratory tabular baseline after manually verifying a Kaggle CSV, its target column, source licence, provenance and label quality.
- `services/ai/DATA-SOURCES.md`: source register for Kaggle, WHO, Kemenkes, Blood Agglutination Curated V1, and BloodyWell.
- `services/ai/prepare_binary_manifest.py` + `train_external_binary.py`: separate 8,043-image binary agglutination benchmark pipeline (not Widal).
- `services/ai/prepare_bloodywell_benchmark.py`: metadata manifest for the separate BloodyWell test subset.

WHO/Kemenkes publications are reference material, not labelled patient datasets. The Kaggle candidate is tabular and cannot train the Widal image classifier. The two public image datasets are binary blood-group agglutination benchmarks, not Widal reaction-grade data. Two public binary agglutination datasets (Blood Agglutination Curated V1 and BloodyWell) are catalogued only as external blood-group morphology benchmarks, not Widal grade datasets. A guarded weekly local training job is available at `services/ai/auto_train.py`; it requires a dataset hash approved by an ATLM and produces a candidate only. It never replaces the active model automatically. All AI outputs remain research-only and require professional review.
