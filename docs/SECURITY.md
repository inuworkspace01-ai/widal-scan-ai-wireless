# Security notes

- Never commit Wi-Fi passwords, Supabase service-role keys, patient identifiers, or secrets.
- Use anonymized sample codes during prototyping.
- Keep image storage private and review RLS policies before real use.
- Bridge currently binds to localhost by default. If LAN access is enabled, add authentication, strict CORS, TLS where feasible, and firewall restrictions.
- Firmware uses placeholder credentials and must be adapted to the exact board.
- The current OpenCV logic measures image quality only. It is not a validated Widal classifier and must not be used for diagnosis.