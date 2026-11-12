import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCOUNT_IDS = ["inuu", "avi_lab", "riska_lab"] as const;
type SetupBody = {
  token?: unknown;
  passwords?: Record<string, unknown>;
};

function safeTokenMatch(provided: string, expected: string): boolean {
  const left = Buffer.from(provided);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

function json(message: string, status: number, extra: Record<string, unknown> = {}) {
  return NextResponse.json(
    { ok: status >= 200 && status < 300, message, ...extra },
    {
      status,
      headers: {
        "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
        "Pragma": "no-cache",
      },
    }
  );
}

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (origin && host) {
    try {
      if (new URL(origin).host !== host) {
        return json("Permintaan setup ditolak karena origin tidak cocok.", 403);
      }
    } catch {
      return json("Origin request tidak valid.", 403);
    }
  }

  const expectedToken = process.env.BOOTSTRAP_SETUP_TOKEN;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!expectedToken || expectedToken.length < 32 || !supabaseUrl || !publishableKey) {
    return json(
      "Setup belum siap. Diperlukan NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, dan BOOTSTRAP_SETUP_TOKEN di environment Vercel.",
      503
    );
  }

  let body: SetupBody;
  try {
    body = (await request.json()) as SetupBody;
  } catch {
    return json("Format permintaan tidak valid.", 400);
  }

  if (typeof body.token !== "string" || !safeTokenMatch(body.token, expectedToken)) {
    return json("Setup token salah. Periksa token setup.", 401);
  }

  if (!body.passwords || typeof body.passwords !== "object") {
    return json("Password untuk ketiga akun wajib diisi.", 400);
  }

  const passwords = ACCOUNT_IDS.map((id) => body.passwords?.[id]);
  if (passwords.some((value) => typeof value !== "string" || value.length < 12 || value.length > 128)) {
    return json("Setiap password harus memiliki panjang 12–128 karakter.", 400);
  }

  const normalizedPasswords = passwords as string[];
  if (new Set(normalizedPasswords).size !== ACCOUNT_IDS.length) {
    return json("Gunakan password berbeda untuk setiap akun.", 400);
  }

  if (normalizedPasswords.some((value, index) =>
    /^(.)\\1+$/.test(value) || value.toLowerCase() === ACCOUNT_IDS[index]
  )) {
    return json("Gunakan password yang kuat dan tidak sama dengan ID akun.", 400);
  }

  try {
    const edgeResponse = await fetch(supabaseUrl.replace(/\\/$/, "") + "/functions/v1/bootstrap-accounts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": publishableKey,
        "x-setup-token": expectedToken,
      },
      body: JSON.stringify({
        passwords: {
          inuu: normalizedPasswords[0],
          avi_lab: normalizedPasswords[1],
          riska_lab: normalizedPasswords[2],
        },
      }),
      cache: "no-store",
    });

    const payload = await edgeResponse.json().catch(() => ({}));
    return NextResponse.json(payload, {
      status: edgeResponse.status,
      headers: {
        "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
        "Pragma": "no-cache",
      },
    });
  } catch {
    return json(
      "Tidak dapat menghubungi Supabase Edge Function. Periksa status bootstrap-accounts di Supabase.",
      502
    );
  }
}
