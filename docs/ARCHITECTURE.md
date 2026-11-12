# Architecture

ESP32-CAM (same trusted 2.4 GHz LAN) → Windows FastAPI/OpenCV Bridge → Next.js PWA dashboard → Supabase PostgreSQL/Storage. Vercel hosts only the web frontend; the Windows bridge must run on the local PC and hardware firmware must be flashed separately.