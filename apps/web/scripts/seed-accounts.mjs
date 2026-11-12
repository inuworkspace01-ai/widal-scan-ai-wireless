import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !serviceRoleKey) {
  throw new Error("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in apps/web/.env.accounts first.");
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { autoRefreshToken: false, persistSession: false },
});

const accounts = [
  {
    username: "inuu",
    display_name: "Inuu",
    role: "admin",
    password: process.env.SUPERADMIN_INUU_PASSWORD,
  },
  {
    username: "inu",
    display_name: "Inu",
    role: "admin",
    password: process.env.SUPERADMIN_INU_PASSWORD,
  },
  {
    username: "lab",
    display_name: "Laboratorium",
    role: "atlm",
    password: process.env.LAB_USER_PASSWORD,
  },
];

for (const account of accounts) {
  if (!account.password || account.password.length < 12) {
    throw new Error("Password environment variable for " + account.username + " is missing or shorter than 12 characters.");
  }

  const email = account.username + "@login.widal-scan.invalid";
  const { data: userList, error: listError } = await supabase.auth.admin.listUsers({
    page: 1,
    perPage: 1000,
  });

  if (listError) throw listError;

  let user = userList.users.find((item) => item.email?.toLowerCase() === email.toLowerCase());

  if (!user) {
    const { data, error } = await supabase.auth.admin.createUser({
      email,
      password: account.password,
      email_confirm: true,
      user_metadata: { username: account.username },
    });

    if (error) throw error;
    user = data.user;
    console.log("Created auth account:", account.username);
  } else {
    console.log("Auth account already exists; password left unchanged:", account.username);
  }

  const { error: profileError } = await supabase.from("profiles").upsert(
    {
      user_id: user.id,
      username: account.username,
      display_name: account.display_name,
      role: account.role,
      is_active: true,
    },
    { onConflict: "user_id" },
  );

  if (profileError) throw profileError;
  console.log("Profile ready:", account.username, "=>", account.role);
}

console.log("Account bootstrap complete. Remove service-role credentials from the shell after use.");
