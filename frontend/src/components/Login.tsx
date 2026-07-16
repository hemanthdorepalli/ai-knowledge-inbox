import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

interface Props {
  onSignIn: () => Promise<unknown>;
}

// Full-screen sign-in. One action: continue with Google (handled by Supabase).
export default function Login({ onSignIn }: Props) {
  const [busy, setBusy] = useState(false);

  async function handleClick() {
    setBusy(true);
    try {
      await onSignIn();
    } finally {
      // On success the browser redirects to Google, so this rarely runs.
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="w-full max-w-sm rounded-2xl border border-line bg-card p-8 text-center shadow-lift"
      >
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-white shadow-lift">
          <Sparkles size={26} />
        </div>
        <h1 className="font-serif text-3xl font-medium tracking-tight text-ink">
          Knowledge Inbox
        </h1>
        <p className="mt-2 text-sm text-muted">
          Save notes and links, then ask questions answered from your own content.
        </p>

        <button
          onClick={handleClick}
          disabled={busy}
          className="mt-7 flex w-full items-center justify-center gap-3 rounded-xl border border-line bg-card px-4 py-3 text-sm font-semibold text-ink transition-all hover:border-accent/40 hover:shadow-soft disabled:opacity-60"
        >
          <GoogleIcon />
          {busy ? "Redirecting…" : "Continue with Google"}
        </button>

        <p className="mt-4 text-xs text-faint">
          Your saved content is private to your account.
        </p>
      </motion.div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.71-1.57 2.68-3.89 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.47.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}
