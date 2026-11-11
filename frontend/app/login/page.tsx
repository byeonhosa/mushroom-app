"use client";

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPost } from "../../lib/api";
import { safeNextPath } from "../../lib/session";
import type { CurrentUser } from "../../lib/types";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [setupRequired, setSetupRequired] = useState(false);

  useEffect(() => {
    apiGet<{ setup_required: boolean }>("/auth/status")
      .then((status) => setSetupRequired(status.setup_required))
      .catch(() => setError("The app could not reach its server. Check the connection and reload the page."));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const user = await apiPost<CurrentUser>("/auth/login", { email, password });
      const next = safeNextPath(new URLSearchParams(window.location.search).get("next"));
      window.location.assign(user.must_change_password ? "/account" : next);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Sign-in failed. Try again.");
      setBusy(false);
    }
  }

  return (
    <div className="card signInCard">
      <h1>Mushroom Farm App</h1>
      <p>Sign in to continue.</p>
      {setupRequired && (
        <p className="notice" role="status">
          No administrator account has been set up on this server yet, so nobody can sign in. The owner
          sets the first administrator&apos;s email and password in the deployment settings.
        </p>
      )}
      <form onSubmit={submit} className="form">
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="username"
            inputMode="email"
            autoCapitalize="none"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <button className="btn btnSolid" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
