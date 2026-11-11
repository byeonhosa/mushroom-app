"use client";

import { useState } from "react";
import { ApiError, apiPatch, apiPost } from "../../lib/api";
import { useCurrentUser } from "../../lib/session";
import type { CurrentUser } from "../../lib/types";

export default function AccountPage() {
  const user = useCurrentUser();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState(user.display_name);
  const [nameError, setNameError] = useState<string | null>(null);

  async function saveName(event: React.FormEvent) {
    event.preventDefault();
    setNameError(null);
    try {
      await apiPatch<CurrentUser>("/auth/me", { display_name: name });
      window.location.reload();
    } catch (failure) {
      setNameError(failure instanceof ApiError ? failure.message : "The name was not saved. Try again.");
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    setDone(false);
    if (next !== again) {
      setError("The two new passwords are not the same.");
      return;
    }
    setBusy(true);
    try {
      await apiPost<CurrentUser>("/auth/change-password", { current_password: current, new_password: next });
      if (user.must_change_password) {
        window.location.assign("/");
        return;
      }
      setDone(true);
      setCurrent("");
      setNext("");
      setAgain("");
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The password was not changed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card accountCard">
      <h1>Your account</h1>
      <p>
        {user.display_name} · {user.email} · {user.role === "admin" ? "Administrator" : "Operator"}
      </p>

      {!user.must_change_password && (
        <>
          <h2>Your name</h2>
          <form onSubmit={saveName} className="form">
            <label>
              Name shown in the app
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120} required />
            </label>
            <button className="btn" type="submit" disabled={name.trim() === user.display_name || !name.trim()}>
              Save name
            </button>
          </form>
          {nameError && <p className="error" role="alert">{nameError}</p>}
        </>
      )}

      <h2>Change password</h2>
      {user.must_change_password && (
        <p className="notice" role="status">
          Your password was set by someone else. Choose your own before you continue.
        </p>
      )}
      <form onSubmit={submit} className="form">
        <label>
          Current password
          <input
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
          />
        </label>
        <label>
          New password
          <input
            type="password"
            autoComplete="new-password"
            minLength={10}
            value={next}
            onChange={(e) => setNext(e.target.value)}
            aria-describedby="new-password-hint"
            required
          />
        </label>
        <span className="fieldHint" id="new-password-hint">At least 10 characters.</span>
        <label>
          New password again
          <input
            type="password"
            autoComplete="new-password"
            minLength={10}
            value={again}
            onChange={(e) => setAgain(e.target.value)}
            required
          />
        </label>
        <button className="btn btnSolid" type="submit" disabled={busy}>
          {busy ? "Saving…" : "Change password"}
        </button>
      </form>
      {done && <p className="success" role="status">Password changed. Other devices signed in to this account have been signed out.</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}
