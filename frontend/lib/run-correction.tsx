"use client";

import { useId, useState } from "react";
import { apiPatch } from "./api";
import { useCurrentUser } from "./session";

/**
 * "Correct this run": an administrator fixes a run's details after creating it
 * (SRS RUN-5). Only the fields that were changed are sent. The server refuses
 * a correction that would falsify the run's bags (a run code already printed
 * on a label, a planned count below the records that exist) and says why.
 */

export type CorrectionField = {
  key: string;
  label: string;
  kind: "text" | "datetime" | "integer" | "number";
  required?: boolean;
  hint?: string;
};

type Values = Record<string, unknown>;

function toLocalInput(iso: unknown): string {
  if (typeof iso !== "string" || !iso) return "";
  const moment = new Date(iso);
  if (Number.isNaN(moment.getTime())) return "";
  const pad = (value: number) => String(value).padStart(2, "0");
  return (
    `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}` +
    `T${pad(moment.getHours())}:${pad(moment.getMinutes())}`
  );
}

function asInput(field: CorrectionField, value: unknown): string {
  if (field.kind === "datetime") return toLocalInput(value);
  return value == null ? "" : String(value);
}

function asPayload(field: CorrectionField, text: string): string | number | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  if (field.kind === "datetime") return new Date(trimmed).toISOString();
  if (field.kind === "integer" || field.kind === "number") return Number(trimmed);
  return trimmed;
}

export function RunCorrection(props: {
  /** API path of the run, for example "/sterilization-runs/12". */
  path: string;
  values: Values;
  fields: CorrectionField[];
  onSaved: () => Promise<void> | void;
  /** Wording for a record that is not a run. */
  title?: string;
  intro?: string;
  savedMessage?: string;
  /** Show the form at once, for a record picked from a list. */
  startOpen?: boolean;
  onClose?: () => void;
}) {
  const user = useCurrentUser();
  const formId = useId();
  const title = props.title ?? "Correct this run";
  const initialDraft = () =>
    Object.fromEntries(props.fields.map((field) => [field.key, asInput(field, props.values[field.key])]));
  const [open, setOpen] = useState(Boolean(props.startOpen));
  const [draft, setDraft] = useState<Record<string, string>>(() => (props.startOpen ? initialDraft() : {}));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (user.role !== "admin") return null;

  function start() {
    setDraft(initialDraft());
    setError(null);
    setMessage(null);
    setOpen(true);
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const changes: Record<string, string | number | null> = {};
    for (const field of props.fields) {
      const before = asInput(field, props.values[field.key]);
      const after = draft[field.key] ?? "";
      if (after.trim() !== before.trim()) changes[field.key] = asPayload(field, after);
    }
    if (Object.keys(changes).length === 0) {
      setOpen(false);
      setMessage("Nothing was changed.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiPatch(props.path, changes);
      await props.onSaved();
      setOpen(false);
      setMessage(props.savedMessage ?? "Run corrected.");
    } catch (failure: any) {
      setError(failure?.message || String(failure));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label={title}>
      <h2>{title}</h2>
      {message && <p className="success" role="status">{message}</p>}
      {!open ? (
        <>
          <p>{props.intro ?? "If the run was entered with a wrong date, count or setting, an administrator can put it right here."}</p>
          <button className="btn" type="button" onClick={start}>{title}</button>
        </>
      ) : (
        <form className="form stackedForm" onSubmit={save}>
          {error && <p className="error" role="alert">{error}</p>}
          {props.fields.map((field) => {
            const hintId = `${formId}-${field.key}-hint`;
            return (
              <div key={field.key}>
                <label>
                  {field.label}
                  <input
                    type={field.kind === "datetime" ? "datetime-local" : field.kind === "text" ? "text" : "number"}
                    step={field.kind === "integer" ? "1" : field.kind === "number" ? "0.1" : undefined}
                    min={field.kind === "integer" || field.kind === "number" ? "0" : undefined}
                    required={field.required}
                    aria-describedby={field.hint ? hintId : undefined}
                    value={draft[field.key] ?? ""}
                    onChange={(e) => setDraft((current) => ({ ...current, [field.key]: e.target.value }))}
                  />
                </label>
                {field.hint && <span className="fieldHint" id={hintId}>{field.hint}</span>}
              </div>
            );
          })}
          <button className="btn btnSolid" type="submit" disabled={busy}>Save correction</button>
          <button
            className="btn"
            type="button"
            disabled={busy}
            onClick={() => {
              setOpen(false);
              props.onClose?.();
            }}
          >
            Cancel
          </button>
        </form>
      )}
    </section>
  );
}
