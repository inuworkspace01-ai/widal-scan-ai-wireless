import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REQUIRED_ENV = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "BOOTSTRAP_SETUP_TOKEN",
] as const;

export async function GET() {
  const presence: Record<string, boolean> = {
    NEXT_PUBLIC_SUPABASE_URL: Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL),
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: Boolean(
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    ),
    BOOTSTRAP_SETUP_TOKEN: Boolean(
      process.env.BOOTSTRAP_SETUP_TOKEN &&
      process.env.BOOTSTRAP_SETUP_TOKEN.length >= 32
    ),
  };

  const missing = REQUIRED_ENV.filter((key) => !presence[key]);
  return NextResponse.json(
    { configured: missing.length === 0, missing, presence },
    {
      headers: {
        "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
        "Pragma": "no-cache",
      },
    }
  );
}
