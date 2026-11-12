# Local Bridge API

- GET /v1/health
- GET /v1/device/status
- POST /v1/device/configure (simulation acknowledgement only; no Wi-Fi provisioning implemented)
- POST /v1/capture
- GET /v1/captures/{capture_id}/image
- POST /v1/captures/{capture_id}/analyze (quality metrics only)
- DELETE /v1/captures/{capture_id}


## Web setup endpoints

- GET `/api/setup/status` — reports whether the one-time account setup server configuration is present (booleans only).
- POST `/api/setup/bootstrap` — validates the same-origin request and one-time setup token, then creates the initial `inuu`, `inu`, and `lab` Supabase Auth users and profiles. Requires server-only `SUPABASE_SERVICE_ROLE_KEY` and `BOOTSTRAP_SETUP_TOKEN`. It refuses replay after all three profile records exist. Remove the server secrets from Vercel after successful initialization.


## Initial account bootstrap

- `POST /api/setup/bootstrap` validates the Vercel one-time setup token, checks three different strong passwords, and forwards the request server-to-server to the Supabase Edge Function `bootstrap-accounts`.
- The Edge Function uses Supabase's built-in server-side Secret Keys environment and creates `inuu` (admin), `avi_lab` (ATLM), and `riska_lab` (ATLM).
- The three required Vercel variables are `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and `BOOTSTRAP_SETUP_TOKEN`. A Supabase Secret Key is not required in Vercel.
- After successful account setup, remove `BOOTSTRAP_SETUP_TOKEN` from Vercel. The function rejects replay after the database token is consumed.
