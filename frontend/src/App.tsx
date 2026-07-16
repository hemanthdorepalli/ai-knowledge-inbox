import { Loader2 } from "lucide-react";
import { useAuth } from "./hooks/useAuth";
import Login from "./components/Login";
import Inbox from "./components/Inbox";

// Auth gate: show a spinner while we check for a session, the login screen if
// signed out, or the app if signed in.
export default function App() {
  const { user, loading, signInWithGoogle, signOut } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app">
        <Loader2 className="animate-spin text-accent" size={28} />
      </div>
    );
  }

  if (!user) {
    return <Login onSignIn={signInWithGoogle} />;
  }

  // Prefer the name Google gave us; fall back to the email's local part.
  const meta = (user.user_metadata ?? {}) as Record<string, string | undefined>;
  const displayName =
    meta.full_name || meta.name || meta.given_name || user.email?.split("@")[0] || "there";
  const firstName = displayName.split(" ")[0];

  return (
    <Inbox
      userEmail={user.email ?? "Signed in"}
      userName={firstName}
      onSignOut={signOut}
    />
  );
}
