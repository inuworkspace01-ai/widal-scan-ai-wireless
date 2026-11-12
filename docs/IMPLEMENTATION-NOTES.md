# Implementation notes

This is a research starter, not a clinically validated medical device. The web dashboard now includes Supabase Auth ID login, role-aware navigation, a first-time server-side account bootstrap endpoint, and database migrations for profile roles and lab-user data isolation. These features are not active until the correct Supabase project URL and API keys are configured in Vercel and migrations 001–004 have been executed.

The requested initial role map is:
- `inuu` / `Inuu`: sole Super Admin
- `avi_lab` / `Avi_Lab`: Lab User
- `riska_lab` / `Riska_lab`: Lab User

The account setup wizard generates passwords in the browser or accepts user-chosen passwords. The server stores them only in Supabase Auth; they are never committed to source control. The setup token and Supabase secret key must be removed from Vercel after successful initialization.

The image pipeline remains untrained. It needs de-identified real Widal slide images and ATLM-adjudicated per-well visual grades. Kaggle clinical tabular data is a separate exploratory research task; WHO/Kemenkes documents are procedural/clinical references, not image labels.

A guarded Windows weekly retraining task is included. It runs only when a new manifest has a matching ATLM approval hash, writes a candidate checkpoint and metrics locally, and never automatically replaces the active model. It requires Python, PyTorch/torchvision, a prepared dataset, and manual task registration on the laboratory PC.

Remaining integration work includes: persist capture metadata/images to Supabase, insert audit events server-side, build an authenticated local Bridge/device pairing flow, validate ESP32-CAM capture on the exact hardware, and complete prospective external validation before any clinical pilot.
