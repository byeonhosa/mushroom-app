"use client";

import { useEffect, useState } from "react";
import { ApiError, apiGet, apiPatch, apiPost } from "../../lib/api";
import { useCurrentUser } from "../../lib/session";
import type { User } from "../../lib/types";

type Role = "admin" | "operator";

const ROLE_LABEL: Record<Role, string> = { admin: "Administrator", operator: "Operator" };

function describe(failure: unknown, fallback: string) {
  return failure instanceof ApiError ? failure.message : fallback;
}

export default function UsersPage() {
  const me = useCurrentUser();
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("operator");
  const [password, setPassword] = useState("");

  // Which row has its password-reset field open, and what is typed in it.
  const [resetFor, setResetFor] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState("");

  async function load() {
    setUsers(await apiGet<User[]>("/users"));
  }

  useEffect(() => {
    if (me.role !== "admin") return;
    load().catch((failure) => setError(describe(failure, "The list of users could not be loaded.")));
  }, [me.role]);

  if (me.role !== "admin") {
    return (
      <div className="card">
        <h1>Users</h1>
        <p className="error" role="alert">Only an administrator can manage users.</p>
      </div>
    );
  }

  async function run(action: () => Promise<void>, fallback: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      await load();
    } catch (failure) {
      setError(describe(failure, fallback));
    } finally {
      setBusy(false);
    }
  }

  function addUser(event: React.FormEvent) {
    event.preventDefault();
    run(async () => {
      const created = await apiPost<User>("/users", {
        email,
        display_name: displayName,
        role,
        password,
      });
      setMessage(`${created.display_name} can now sign in. They will be asked to choose their own password.`);
      setEmail("");
      setDisplayName("");
      setRole("operator");
      setPassword("");
    }, "The user was not added.");
  }

  function change(user: User, changes: Record<string, unknown>, done: string) {
    run(async () => {
      await apiPatch<User>(`/users/${user.user_id}`, changes);
      setMessage(done);
    }, "The change was not saved.");
  }

  function submitReset(event: React.FormEvent, user: User) {
    event.preventDefault();
    run(async () => {
      await apiPatch<User>(`/users/${user.user_id}`, { password: resetPassword });
      setMessage(
        `Password reset for ${user.display_name}. They are signed out everywhere and will choose a new password at next sign-in.`,
      );
      setResetFor(null);
      setResetPassword("");
    }, "The password was not reset.");
  }

  return (
    <div>
      <div className="card">
        <h1>Users</h1>
        <p>
          Everyone who uses the app signs in with their own account. An operator records the farm&apos;s
          work and reads the reports. An administrator can also maintain species and other setup data and
          manage users.
        </p>
        {message && <p className="success" role="status">{message}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>

      <div className="card">
        <h2>Add a user</h2>
        <form onSubmit={addUser} className="form">
          <label>
            Name
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={120} required />
          </label>
          <label>
            Email
            <input
              type="email"
              autoCapitalize="none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label>
            Role
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="operator">Operator</option>
              <option value="admin">Administrator</option>
            </select>
          </label>
          <label>
            First password
            <input
              type="text"
              autoComplete="off"
              minLength={10}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-describedby="first-password-hint"
              required
            />
          </label>
          <span className="fieldHint" id="first-password-hint">
            At least 10 characters. Give it to the person; the app asks them to replace it at first sign-in.
          </span>
          <button className="btn btnSolid" type="submit" disabled={busy}>Add user</button>
        </form>
      </div>

      <div className="card">
        <h2>All users</h2>
        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last sign-in</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isMe = user.user_id === me.user_id;
                return (
                  <tr key={user.user_id}>
                    <td>
                      {user.display_name}
                      {isMe && <span className="tableMeta"> (you)</span>}
                    </td>
                    <td>{user.email}</td>
                    <td>
                      <select
                        aria-label={`Role of ${user.display_name}`}
                        value={user.role}
                        disabled={busy || isMe}
                        onChange={(e) =>
                          change(
                            user,
                            { role: e.target.value },
                            `${user.display_name} is now ${ROLE_LABEL[e.target.value as Role].toLowerCase()}.`,
                          )
                        }
                      >
                        <option value="operator">Operator</option>
                        <option value="admin">Administrator</option>
                      </select>
                    </td>
                    <td>{user.is_active ? "Active" : "Deactivated"}</td>
                    <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</td>
                    <td>
                      <div className="rowActions">
                        {!isMe && (
                          <button
                            type="button"
                            className="btn btnSmall"
                            disabled={busy}
                            onClick={() =>
                              change(
                                user,
                                { is_active: !user.is_active },
                                user.is_active
                                  ? `${user.display_name} can no longer sign in.`
                                  : `${user.display_name} can sign in again.`,
                              )
                            }
                          >
                            {user.is_active ? "Deactivate" : "Reactivate"}
                          </button>
                        )}
                        {!isMe && resetFor !== user.user_id && (
                          <button
                            type="button"
                            className="btn btnSmall"
                            disabled={busy}
                            onClick={() => {
                              setResetFor(user.user_id);
                              setResetPassword("");
                            }}
                          >
                            Reset password
                          </button>
                        )}
                        {isMe && <a className="btn btnSmall" href="/account">Change my password</a>}
                      </div>
                      {resetFor === user.user_id && (
                        <form className="inlineForm" onSubmit={(event) => submitReset(event, user)}>
                          <label>
                            New password for {user.display_name}
                            <input
                              type="text"
                              autoComplete="off"
                              minLength={10}
                              value={resetPassword}
                              onChange={(e) => setResetPassword(e.target.value)}
                              required
                              autoFocus
                            />
                          </label>
                          <button className="btn btnSmall btnSolid" type="submit" disabled={busy}>Set password</button>
                          <button type="button" className="btn btnSmall" onClick={() => setResetFor(null)}>Cancel</button>
                        </form>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
