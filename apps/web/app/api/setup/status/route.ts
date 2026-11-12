import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const configured = Boolean(
    (process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL) &&
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY &&
    (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY) &&
    process.env.BOOTSTRAP_SETUP_TOKEN
  );

  return NextResponse.json(
    { configured },
    {
      headers: {
        "Cache-Control": "no-store, max-age=0",
      },
    }
  );
}
