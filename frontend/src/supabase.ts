import { createClient } from "@supabase/supabase-js";

// Single Supabase client for the whole app. Reads the project URL + anon key
// from env (safe to expose — the anon key is public; Row-Level Security is what
// actually protects the data).
const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Fail loud in dev rather than silently breaking auth.
  console.error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY in .env");
}

export const supabase = createClient(url ?? "", anonKey ?? "");
