# Security notes

- Never commit Wi-Fi passwords, Supabase service-role keys, patient identifiers, or secrets.
- Use anonymized sample codes during prototyping.
- Keep image storage private and review RLS policies before real use.
- Bridge currently binds to localhost by default. If LAN access is enabled, add authentication, strict CORS, TLS where feasible, and firewall restrictions.
- Firmware uses placeholder credentials and must be adapted to the exact board.
- The current OpenCV logic measures image quality only. It is not a validated Widal classifier and must not be used for diagnosis.

## Account login and roles

- User IDs `inuu` and `inu` are mapped to the internal `admin` role (displayed as Super Admin).
- User ID `lab` is mapped to the `atlm` role (displayed as Lab User).
- Passwords are provisioned through Supabase Auth by the local bootstrap script. There are no source-code default passwords.
- The Supabase service-role key is used only by the one-time local bootstrap script. It must never use a `NEXT_PUBLIC_*` prefix or be shipped to the browser.
- The app's role-aware navigation is a convenience layer; PostgreSQL Row Level Security is the enforcement boundary. Review all RLS policies before enabling production records.
- Internal login aliases use the reserved `.invalid` domain and are not email delivery addresses.
