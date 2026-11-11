"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { apiGet, apiPatch, apiPost } from "./api";

/**
 * One list of reference records with add, edit and deactivate (SRS REF-3 to
 * REF-7, REF-14). Nothing here deletes: a record that has been used must stay
 * visible on the runs and lots that used it, so it is deactivated instead,
 * which takes it out of the pick lists for new work.
 */

export type ReferenceField = {
  key: string;
  label: string;
  kind?: "text" | "number";
  required?: boolean;
  placeholder?: string;
  hint?: string;
  /** Shown after a number in the table, for example "kg". */
  unit?: string;
};

type Row = Record<string, unknown> & { is_active: boolean };
type Draft = Record<string, string>;

type Props = {
  title: string;
  intro?: string;
  /** API path of the collection, for example "/spawn-recipes". */
  path: string;
  idKey: string;
  /** The word for one record, for example "spawn recipe". */
  noun: string;
  fields: ReferenceField[];
  canEdit: boolean;
};

function emptyDraft(fields: ReferenceField[]): Draft {
  return Object.fromEntries(fields.map((field) => [field.key, ""]));
}

function draftOf(fields: ReferenceField[], row: Row): Draft {
  return Object.fromEntries(fields.map((field) => [field.key, row[field.key] == null ? "" : String(row[field.key])]));
}

function payloadOf(fields: ReferenceField[], draft: Draft): Record<string, string | number | null> {
  const payload: Record<string, string | number | null> = {};
  for (const field of fields) {
    const text = (draft[field.key] ?? "").trim();
    if (field.kind === "number") payload[field.key] = text === "" ? null : Number(text);
    else payload[field.key] = text === "" ? null : text;
  }
  return payload;
}

function shown(field: ReferenceField, value: unknown): string {
  if (value == null || value === "") return "-";
  return field.unit ? `${value} ${field.unit}` : String(value);
}

export function ReferenceList({ title, intro, path, idKey, noun, fields, canEdit }: Props) {
  const formId = useId();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [draft, setDraft] = useState<Draft>(() => emptyDraft(fields));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Draft>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRows(await apiGet<Row[]>(path));
  }, [path]);

  useEffect(() => {
    refresh().catch((e) => setError(e?.message || String(e)));
  }, [refresh]);

  const nameOf = (row: Row) => String(row[fields[0].key] ?? "");

  async function act(work: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const done = await work();
      await refresh();
      setMessage(done);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function add(event: React.FormEvent) {
    event.preventDefault();
    void act(async () => {
      const created = await apiPost<Row>(path, payloadOf(fields, draft));
      setDraft(emptyDraft(fields));
      return `Added ${nameOf(created)}.`;
    });
  }

  function save(event: React.FormEvent, row: Row) {
    event.preventDefault();
    void act(async () => {
      const saved = await apiPatch<Row>(`${path}/${row[idKey]}`, payloadOf(fields, editDraft));
      setEditingId(null);
      return `Saved ${nameOf(saved)}.`;
    });
  }

  function setActive(row: Row, active: boolean) {
    void act(async () => {
      await apiPatch<Row>(`${path}/${row[idKey]}`, { is_active: active });
      return active ? `${nameOf(row)} is active again.` : `${nameOf(row)} is deactivated. Records that used it still show it.`;
    });
  }

  return (
    <section className="card" aria-label={title}>
      <h2>{title}</h2>
      {intro && <p>{intro}</p>}
      {message && <p className="success" role="status">{message}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {rows === null ? (
        <p>Loading…</p>
      ) : rows.length === 0 ? (
        <p>None yet.</p>
      ) : (
        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                {fields.map((field) => <th key={field.key}>{field.label}</th>)}
                <th>State</th>
                {canEdit && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const id = Number(row[idKey]);
                const editing = editingId === id;
                const editFormId = `${formId}-edit-${id}`;
                return (
                  <tr key={id} className={row.is_active ? undefined : "rowInactive"}>
                    {fields.map((field) => (
                      <td key={field.key}>
                        {editing ? (
                          <input
                            className="cellInput"
                            form={editFormId}
                            aria-label={`${field.label} of ${nameOf(row)}`}
                            type={field.kind === "number" ? "number" : "text"}
                            step={field.kind === "number" ? "0.001" : undefined}
                            min={field.kind === "number" ? "0" : undefined}
                            required={field.required}
                            value={editDraft[field.key] ?? ""}
                            onChange={(e) => setEditDraft((d) => ({ ...d, [field.key]: e.target.value }))}
                          />
                        ) : (
                          shown(field, row[field.key])
                        )}
                      </td>
                    ))}
                    <td>{row.is_active ? "Active" : "Deactivated"}</td>
                    {canEdit && (
                      <td>
                        {editing ? (
                          <form id={editFormId} className="rowActions" onSubmit={(e) => save(e, row)}>
                            <button className="btn btnSmall btnSolid" type="submit" disabled={busy}>Save</button>
                            <button className="btn btnSmall" type="button" onClick={() => setEditingId(null)}>Cancel</button>
                          </form>
                        ) : (
                          <div className="rowActions">
                            <button
                              className="btn btnSmall"
                              type="button"
                              aria-label={`Edit ${nameOf(row)}`}
                              onClick={() => {
                                setEditDraft(draftOf(fields, row));
                                setEditingId(id);
                              }}
                            >
                              Edit
                            </button>
                            <button
                              className="btn btnSmall"
                              type="button"
                              disabled={busy}
                              aria-label={`${row.is_active ? "Deactivate" : "Reactivate"} ${nameOf(row)}`}
                              onClick={() => setActive(row, !row.is_active)}
                            >
                              {row.is_active ? "Deactivate" : "Reactivate"}
                            </button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {canEdit && (
        <form className="form stackedForm" onSubmit={add} aria-label={`Add a ${noun}`}>
          <h3>Add a {noun}</h3>
          {fields.map((field) => {
            const hintId = `${formId}-${field.key}-hint`;
            return (
              <div key={field.key}>
                <label>
                  {field.label}
                  <input
                    type={field.kind === "number" ? "number" : "text"}
                    step={field.kind === "number" ? "0.001" : undefined}
                    min={field.kind === "number" ? "0" : undefined}
                    required={field.required}
                    placeholder={field.placeholder}
                    aria-describedby={field.hint ? hintId : undefined}
                    value={draft[field.key] ?? ""}
                    onChange={(e) => setDraft((d) => ({ ...d, [field.key]: e.target.value }))}
                  />
                </label>
                {field.hint && <span className="fieldHint" id={hintId}>{field.hint}</span>}
              </div>
            );
          })}
          <button className="btn btnSolid" type="submit" disabled={busy}>Add {noun}</button>
        </form>
      )}
    </section>
  );
}
