import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REQUIRED_ENV = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "SUPABASE_SECRET_KEY",
  "BOOTSTRAP_SETUP_TOKEN",
] as const;

export async function GET() {
  const presence: Record<string, boolean> = {
    NEXT_PUBLIC_SUPABASE_URL: Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL),
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: Boolean(
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    ),
    SUPABASE_SECRET_KEY: Boolean(
      process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY
    ),
    BOOTSTRAP_SETUP_TOKEN: Boolean(
      process.env.BOOTSTRAP_SETUP_TOKEN &&
      process.env.BOOTSTRAP_SETUP_TOKEN.length >= 32
    ),
  };

  const missing = REQUIRED_ENV.filter((key) => !presence[key]);
  const configured = missing.length === 0;

  return NextResponse.json(
    { configured, missing, presence },
    {
      headers: {
        "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
        "Pragma": "no-cache",
      },
    }
  );
}
