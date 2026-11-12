import { createClient } from "npm:@supabase/supabase-js@2";

const ACCOUNT_DEFINITIONS = [
  { username: "inuu", displayName: "Inuu", role: "admin" },
  { username: "avi_lab", displayName: "Avi_Lab", role: "atlm" },
  { username: "riska_lab", displayName: "Riska_lab", role: "atlm" },
] as const;

// SHA-256 digest of the one-time BOOTSTRAP_SETUP_TOKEN stored in Vercel.
// The raw token is never stored in this function or in the repository.
const SETUP_TOKEN_SHA256 = "eefd7e5a4b64e4e5068fb63be0642ec77fe16c60fd39548800e24c64f5d4cb0f";

const corsHeaders = {
  "Access-Control-Allow-Origin": "https://widal-scan-ai-wireless.vercel.app",
  "Access-Control-Allow-Headers": "content-type, apikey, x-setup-token",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Cache-Control": "no-store, max-age=0",
};

function reply(message: string, status: number, extra: Record<string, unknown> = {}) {
  return new Response(JSON.stringify({ ok: status >= 200 && status < 300, message, ...extra }), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

async function sha256Hex(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (request.method !== "POST") return reply("Method not allowed.", 405);

  const setupToken = request.headers.get("x-setup-token") ?? "";
  if (setupToken.length < 32) return reply("Setup token tidak valid.", 401);

  const providedHash = await sha256Hex(setupToken);
  if (!safeEqual(providedHash, SETUP_TOKEN_SHA256)) {
    return reply("Setup token tidak cocok.", 401);
  }

  let body: { passwords?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return reply("Format JSON tidak valid.", 400);
  }

  const passwords = ACCOUNT_DEFINITIONS.map((account) => {
    const value = body.passwords?.[account.username];
    return typeof value === "string" ? value : "";
  });

  for (const password of passwords) {
    if (password.length < 12 || password.length > 128) {
      return reply("Password setiap akun harus terdiri dari 12–128 karakter.", 400);
    }
  }
  if (new Set(passwords).size !== ACCOUNT_DEFINITIONS.length) {
    return reply("Gunakan password berbeda untuk setiap akun.", 400);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const secretKeysEnv = Deno.env.get("SUPABASE_SECRET_KEYS");
  let adminKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

  if (secretKeysEnv) {
    try {
      const secretKeys = JSON.parse(secretKeysEnv) as Record<string, string>;
      adminKey = secretKeys.default || adminKey;
    } catch {
      return reply("Konfigurasi Supabase Secret Keys tidak dapat dibaca.", 503);
    }
  }

  if (!supabaseUrl || !adminKey) {
    return reply("Supabase Admin API belum tersedia di Edge Function.", 503);
  }

  const supabase = createClient(supabaseUrl, adminKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  try {
    const ids = ACCOUNT_DEFINITIONS.map((account) => account.username);
    const { data: existingProfiles, error: profileLookupError } = await supabase
      .from("profiles")
      .select("username")
      .in("username", ids);

    if (profileLookupError) throw profileLookupError;

    const alreadyCreated = new Set((existingProfiles ?? []).map((row) => row.username));
    if (ACCOUNT_DEFINITIONS.every((account) => alreadyCreated.has(account.username))) {
      return reply(
        "Setup akun awal sudah selesai. Endpoint bootstrap sudah dikunci; gunakan alur reset password admin untuk perubahan berikutnya.",
        409,
        { accounts: ids, setupComplete: true },
      );
    }

    const completed: string[] = [];
    for (let index = 0; index < ACCOUNT_DEFINITIONS.length; index += 1) {
      const account = ACCOUNT_DEFINITIONS[index];
      const email = account.username + "@login.widal-scan.invalid";
      let user = null;

      for (let page = 1; page <= 10; page += 1) {
        const { data, error } = await supabase.auth.admin.listUsers({ page, perPage: 1000 });
        if (error) throw error;
        user = data.users.find((item) => item.email?.toLowerCase() === email.toLowerCase()) ?? null;
        if (user || data.users.length < 1000) break;
      }

      if (user) {
        const { error } = await supabase.auth.admin.updateUserById(user.id, {
          password: passwords[index],
          user_metadata: { username: account.username },
        });
        if (error) throw error;
      } else {
        const { data, error } = await supabase.auth.admin.createUser({
          email,
          password: passwords[index],
          email_confirm: true,
          user_metadata: { username: account.username },
        });
        if (error) throw error;
        user = data.user;
      }

      const { error: upsertError } = await supabase.from("profiles").upsert({
        user_id: user.id,
        username: account.username,
        display_name: account.displayName,
        role: account.role,
        is_active: true,
      }, { onConflict: "user_id" });
      if (upsertError) throw upsertError;
      completed.push(account.username);
    }

    await supabase.from("profiles")
      .update({ is_active: false })
      .in("username", ["inu", "lab"]);

    await supabase.from("audit_logs").insert({
      actor_id: null,
      examination_id: null,
      action: "initial_account_bootstrap",
      details: { accounts: completed, role_map: { inuu: "admin", avi_lab: "atlm", riska_lab: "atlm" } },
    });

    return reply(
      "Tiga akun berhasil dibuat di Supabase Auth dan dipasangkan dengan profil role masing-masing. Simpan password sekarang; server tidak akan menampilkannya kembali.",
      200,
      { accounts: completed, setupComplete: true },
    );
  } catch (error) {
    console.error("Account bootstrap failed:", error instanceof Error ? error.message : "Unknown error");
    return reply(
      "Bootstrap akun gagal. Periksa migration database dan Auth logs, lalu ulangi dengan token yang sama. Jangan kirim password melalui chat.",
      500,
    );
  }
});
