import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { createClient, type User } from "@supabase/supabase-js";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ACCOUNT_DEFINITIONS = [
  { username: "inuu", displayName: "Inuu", role: "admin" as const },
  { username: "inu", displayName: "Inu", role: "admin" as const },
  { username: "lab", displayName: "Laboratorium", role: "atlm" as const },
];

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
        "Cache-Control": "no-store, max-age=0",
        "Pragma": "no-cache",
      },
    }
  );
}

async function findAuthUser(
  supabase: ReturnType<typeof createClient>,
  email: string
): Promise<User | null> {
  for (let page = 1; page <= 10; page += 1) {
    const { data, error } = await supabase.auth.admin.listUsers({ page, perPage: 1000 });
    if (error) throw error;

    const found = data.users.find(
      (user) => user.email?.toLowerCase() === email.toLowerCase()
    );
    if (found) return found;
    if (data.users.length < 1000) return null;
  }

  throw new Error("Account lookup exceeded the supported page range.");
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
  const supabaseUrl =
    process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!expectedToken || expectedToken.length < 32 || !supabaseUrl || !serviceRoleKey) {
    return json(
      "Setup belum siap. Admin perlu mengisi SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, dan BOOTSTRAP_SETUP_TOKEN di Vercel Environment Variables.",
      503
    );
  }

  let body: SetupBody;
  try {
    body = (await request.json()) as SetupBody;
  } catch {
    return json("Format permintaan tidak valid.", 400);
  }

  if (
    typeof body.token !== "string" ||
    !safeTokenMatch(body.token, expectedToken)
  ) {
    return json("Setup token salah. Periksa token yang dimasukkan.", 401);
  }

  const passwordEntries = body.passwords;
  if (!passwordEntries || typeof passwordEntries !== "object") {
    return json("Password untuk ketiga akun wajib diisi.", 400);
  }

  const passwords = ACCOUNT_DEFINITIONS.map((account) => {
    const value = passwordEntries[account.username];
    return typeof value === "string" ? value : "";
  });

  for (let index = 0; index < passwords.length; index += 1) {
    const password = passwords[index];
    if (password.length < 12 || password.length > 128) {
      return json(
        "Setiap password harus memiliki panjang 12–128 karakter.",
        400
      );
    }
    if (/^(.)\1+$/.test(password) || password.toLowerCase() === ACCOUNT_DEFINITIONS[index].username) {
      return json("Gunakan password yang kuat dan tidak sama dengan ID akun.", 400);
    }
  }

  if (new Set(passwords).size !== passwords.length) {
    return json("Gunakan password yang berbeda untuk setiap akun.", 400);
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  const completed: string[] = [];

  try {
    const { data: existingProfiles, error: profileLookupError } = await supabase
      .from("profiles")
      .select("username")
      .in("username", ACCOUNT_DEFINITIONS.map((account) => account.username));

    if (profileLookupError) throw profileLookupError;

    const existingIds = new Set(
      (existingProfiles || []).map((profile) => profile.username)
    );
    if (ACCOUNT_DEFINITIONS.every((account) => existingIds.has(account.username))) {
      return json(
        "Setup awal sudah pernah diselesaikan. Hapus BOOTSTRAP_SETUP_TOKEN dari Vercel; gunakan menu reset password resmi bila diperlukan.",
        409,
        { setupComplete: true }
      );
    }

    for (let index = 0; index < ACCOUNT_DEFINITIONS.length; index += 1) {
      const account = ACCOUNT_DEFINITIONS[index];
      const email = account.username + "@login.widal-scan.invalid";
      let user = await findAuthUser(supabase, email);

      if (!user) {
        const { data, error } = await supabase.auth.admin.createUser({
          email,
          password: passwords[index],
          email_confirm: true,
          user_metadata: { username: account.username },
        });

        if (error) {
          // Handle a simultaneous first-time setup attempt without changing
          // an existing account password.
          user = await findAuthUser(supabase, email);
          if (!user) throw error;
        } else {
          user = data.user;
        }
      }

      const { error: profileError } = await supabase
        .from("profiles")
        .upsert(
          {
            user_id: user.id,
            username: account.username,
            display_name: account.displayName,
            role: account.role,
            is_active: true,
          },
          { onConflict: "user_id" }
        );

      if (profileError) throw profileError;
      completed.push(account.username);
    }

    return json(
      "Ketiga akun berhasil disiapkan. Hapus BOOTSTRAP_SETUP_TOKEN dari Vercel setelah proses ini selesai.",
      200,
      { accounts: completed, nextStep: "remove_setup_token" }
    );
  } catch (error) {
    console.error(
      "Account bootstrap failed:",
      error instanceof Error ? error.message : "Unknown setup error"
    );
    return json(
      "Setup belum selesai. Periksa migration Supabase 001 dan 002, lalu ulangi proses. Password akun yang sudah berhasil dibuat tidak diubah saat diulang.",
      500,
      { accounts: completed }
    );
  }
}
